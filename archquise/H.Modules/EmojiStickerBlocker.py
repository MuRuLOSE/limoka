# Proprietary License Agreement

# Copyright (c) 2024-29 CodWiz

# Permission is hereby granted to any person obtaining a copy of this software and associated documentation files (the "Software"), to use the Software for personal and non-commercial purposes, subject to the following conditions:

# 1. The Software may not be modified, altered, or otherwise changed in any way without the explicit written permission of the author.

# 2. Redistribution of the Software, in original or modified form, is strictly prohibited without the explicit written permission of the author.

# 3. The Software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement. In no event shall the author or copyright holder be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the Software or the use or other dealings in the Software.

# 4. Any use of the Software must include the above copyright notice and this permission notice in all copies or substantial portions of the Software.

# 5. By using the Software, you agree to be bound by the terms and conditions of this license.

# For any inquiries or requests for permissions, please contact codwiz@yandex.ru.

# ---------------------------------------------------------------------------------
# Name: EmojiStickerBlocker
# Description: Block emojis, stickers and sticker packs
# Author: @hikka_mods
# ---------------------------------------------------------------------------------
# meta developer: @hikka_mods
# scope: EmojiStickerBlocker
# scope: EmojiStickerBlocker0.0.1
# ---------------------------------------------------------------------------------

import logging
import re
from typing import Optional, Set

from telethon.errors import FloodWaitError, MessageDeleteForbiddenError
from telethon.tl.types import Message, MessageMediaDocument

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class EmojiStickerBlocker(loader.Module):
    """Block emojis, stickers and sticker packs with enhanced functionality"""

    strings = {
        "name": "EmojiStickerBlocker",
        "no_permission": "<emoji document_id=5854929766146118183>❌</emoji> Need delete messages permission",
        "pack_blocked": "<emoji document_id=5854762571659218443>✅</emoji> Pack blocked",
        "pack_not_found": "<emoji document_id=5854929766146118183>❌</emoji> Pack not found",
        "sticker_blocked": "<emoji document_id=5854929766146118183>❌</emoji> Sticker blocked",
        "emoji_blocked": "<emoji document_id=5854929766146118183>❌</emoji> Emoji blocked",
        "pack_unblocked": "<emoji document_id=5854762571659218443>✅</emoji> Pack unblocked",
        "item_unblocked": "<emoji document_id=5854929766146118183>❌</emoji> Item unblocked",
        "not_found": "<emoji document_id=5854929766146118183>❌</emoji> Not in blocklist",
        "no_reply": "<emoji document_id=5854929766146118183>❌</emoji> Reply to a sticker or emoji",
        "no_args": "<emoji document_id=5854929766146118183>❌</emoji> Specify pack link or name",
        "list_packs": "📦 Blocked packs: {}",
        "list_stickers": "🖼 Blocked stickers: {}",
        "list_emojis": "😀 Blocked emojis: {}",
        "all_cleared": "✅ All blocks cleared",
    }

    strings_ru = {
        "no_permission": "<emoji document_id=5854929766146118183>❌</emoji> Нужны права на удаление сообщений",
        "pack_blocked": "<emoji document_id=5188311512791393083>✅</emoji> Пак заблокирован",
        "pack_not_found": "<emoji document_id=5854929766146118183>❌</emoji> Пак не найден",
        "sticker_blocked": "<emoji document_id=5854929766146118183>❌</emoji> Стикер заблокирован",
        "emoji_blocked": "<emoji document_id=5854929766146118183>❌</emoji> Эмодзи заблокирован",
        "pack_unblocked": "<emoji document_id=5854762571659218443>✅</emoji> Пак разблокирован",
        "item_unblocked": "<emoji document_id=5854929766146118183>❌</emoji> Элемент разблокирован",
        "not_found": "<emoji document_id=5854929766146118183>❌</emoji> Не найден в блоклисте",
        "no_reply": "<emoji document_id=5854929766146118183>❌</emoji> Ответьте на стикер или эмодзи",
        "no_args": "<emoji document_id=5854929766146118183>❌</emoji> Укажите ссылку или название пака",
        "list_packs": "📦 Заблокированные паки: {}",
        "list_stickers": "🖼 Заблокированные стикеры: {}",
        "list_emojis": "😀 Заблокированные эмодзи: {}",
        "all_cleared": "✅ Все блоки очищены",
    }

    def __init__(self):
        self.blocked_packs: Set[str] = set()
        self.blocked_stickers: Set[str] = set()
        self.blocked_emojis: Set[str] = set()
        self._client = None
        self._db = None

    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        self._load_blocklists()

    def _load_blocklists(self):
        self.blocked_packs = set(self._db.get(__name__, "blocked_packs", []))
        self.blocked_stickers = set(self._db.get(__name__, "blocked_stickers", []))
        self.blocked_emojis = set(self._db.get(__name__, "blocked_emojis", []))

    def _save_blocklists(self):
        self._db.set(__name__, "blocked_packs", list(self.blocked_packs))
        self._db.set(__name__, "blocked_stickers", list(self.blocked_stickers))
        self._db.set(__name__, "blocked_emojis", list(self.blocked_emojis))

    def _extract_pack_name(self, message: Message) -> Optional[str]:
        """Extract pack name from sticker or emoji"""
        if not message.media:
            return None

        if message.sticker:
            if hasattr(message.sticker, "set_name") and message.sticker.set_name:
                return message.sticker.set_name.lower()

        if isinstance(message.media, MessageMediaDocument):
            if hasattr(message.media, "document") and hasattr(
                message.media.document, "attributes"
            ):
                for attr in message.media.document.attributes:
                    if (
                        hasattr(attr, "stickerset")
                        and hasattr(attr.stickerset, "title")
                        and attr.stickerset.title
                    ):
                        return attr.stickerset.title.lower()

        return None

    def _extract_emoji_text(self, message: Message) -> Optional[str]:
        """Extract emoji text from message"""
        if not message.message:
            return None

        emoji_pattern = re.compile(
            r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251]"
        )
        emojis = emoji_pattern.findall(message.message)

        if emojis:
            return emojis[0]
        return None

    async def _delete_message(self, message: Message) -> bool:
        """Delete message with error handling"""
        try:
            await self._client.delete_messages(message.to_id, [message.id])
            return True
        except MessageDeleteForbiddenError:
            logger.warning("No permission to delete message")
            return False
        except FloodWaitError as e:
            logger.warning(f"Flood wait when deleting message: {e.seconds}s")
            return False
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            return False

    async def _should_block_message(self, message: Message) -> tuple[bool, str]:
        """Check if message should be blocked and return reason"""
        try:
            pack_name = self._extract_pack_name(message)
            emoji_text = self._extract_emoji_text(message)

            if pack_name and pack_name in self.blocked_packs:
                return True, f"pack: {pack_name}"

            if message.sticker:
                sticker_id = str(message.sticker.id)
                if sticker_id in self.blocked_stickers:
                    return True, f"sticker: {sticker_id}"

            if emoji_text and emoji_text in self.blocked_emojis:
                return True, f"emoji: {emoji_text}"

        except Exception as e:
            logger.error(f"Error checking message: {e}")

        return False, ""

    @loader.command(
        ru_doc="[link/название пака] — блокирует эмодзипак/стикерпак в личных сообщениях",
        en_doc="[link/pack name] — block emoji pack/sticker pack in private messages",
    )
    async def packblock(self, message: Message):
        """Block emoji pack/sticker pack"""
        args = utils.get_args_raw(message)
        if not args:
            return await utils.answer(message, self.strings["no_args"])

        pack_name = args.lower().strip()

        if pack_name in self.blocked_packs:
            return await utils.answer(message, self.strings["not_found"])

        self.blocked_packs.add(pack_name)
        self._save_blocklists()

        await utils.answer(message, self.strings["pack_blocked"])

    @loader.command(
        ru_doc="[reply] — блокирует определенный стикер",
        en_doc="[reply] — block specific sticker",
    )
    async def stickblock(self, message: Message):
        """Block sticker from reply"""
        if not message.is_reply:
            return await utils.answer(message, self.strings["no_reply"])

        reply_msg = await message.get_reply_message()
        if not reply_msg or not reply_msg.sticker:
            return await utils.answer(message, self.strings["no_reply"])

        sticker_id = str(reply_msg.sticker.id)

        if sticker_id in self.blocked_stickers:
            return await utils.answer(message, self.strings["not_found"])

        self.blocked_stickers.add(sticker_id)
        self._save_blocklists()

        await utils.answer(message, self.strings["sticker_blocked"])

    @loader.command(
        ru_doc="[reply/enter] — блокирует определенное эмодзи",
        en_doc="[reply/enter] — block specific emoji",
    )
    async def emojiblock(self, message: Message):
        """Block emoji from reply or input"""
        args = utils.get_args_raw(message)
        emoji_text = None

        if args:
            emoji_text = args.strip()
            if not emoji_text:
                return await utils.answer(message, self.strings["no_args"])
        else:
            if not message.is_reply:
                return await utils.answer(message, self.strings["no_reply"])

            reply_msg = await message.get_reply_message()
            if not reply_msg:
                return await utils.answer(message, self.strings["no_reply"])

            emoji_text = self._extract_emoji_text(reply_msg)
            if not emoji_text:
                return await utils.answer(message, self.strings["no_reply"])

        if emoji_text in self.blocked_emojis:
            return await utils.answer(message, self.strings["not_found"])

        self.blocked_emojis.add(emoji_text)
        self._save_blocklists()

        await utils.answer(message, self.strings["emoji_blocked"])

    @loader.command(
        ru_doc="— снимает блокировку с эмодзипака/стикерпака",
        en_doc="— unblock emoji pack/sticker pack",
    )
    async def ublpack(self, message: Message):
        """Unblock emoji pack/sticker pack"""
        args = utils.get_args_raw(message)
        if not args:
            return await utils.answer(message, self.strings["no_args"])

        pack_name = args.lower().strip()

        if pack_name in self.blocked_packs:
            self.blocked_packs.remove(pack_name)
            self._save_blocklists()
            await utils.answer(message, self.strings["pack_unblocked"])
        else:
            await utils.answer(message, self.strings["not_found"])

    @loader.command(
        ru_doc="[reply/enter] — снимает блокировку с определенного эмодзи/стикера",
        en_doc="[reply/enter] — unblock specific emoji/sticker",
    )
    async def ublthis(self, message: Message):
        """Unblock emoji/sticker from reply or input"""
        args = utils.get_args_raw(message)

        if args:
            item = args.strip()
            if not item:
                return await utils.answer(message, self.strings["no_args"])
        else:
            if not message.is_reply:
                return await utils.answer(message, self.strings["no_reply"])

            reply_msg = await message.get_reply_message()
            if not reply_msg:
                return await utils.answer(message, self.strings["no_reply"])

            if reply_msg.sticker:
                item = str(reply_msg.sticker.id)
            else:
                item = self._extract_emoji_text(reply_msg)

            if not item:
                return await utils.answer(message, self.strings["no_reply"])

        unblocked = False
        if item in self.blocked_stickers:
            self.blocked_stickers.remove(item)
            unblocked = True
        if item in self.blocked_emojis:
            self.blocked_emojis.remove(item)
            unblocked = True

        if unblocked:
            self._save_blocklists()
            await utils.answer(message, self.strings["item_unblocked"])
        else:
            await utils.answer(message, self.strings["not_found"])

    @loader.command(
        ru_doc="— показать список заблокированных паков/стикеров/эмодзи",
        en_doc="— show list of blocked packs/stickers/emojis",
    )
    async def blocklist(self, message: Message):
        """Show blocklist"""
        packs_list = ", ".join(self.blocked_packs) if self.blocked_packs else "нет"
        stickers_list = (
            ", ".join(self.blocked_stickers) if self.blocked_stickers else "нет"
        )
        emojis_list = ", ".join(self.blocked_emojis) if self.blocked_emojis else "нет"

        result = []
        if packs_list:
            result.append(self.strings["list_packs"].format(packs_list))
        if stickers_list:
            result.append(self.strings["list_stickers"].format(stickers_list))
        if emojis_list:
            result.append(self.strings["list_emojis"].format(emojis_list))

        if result:
            await utils.answer(message, "\n".join(result))
        else:
            await utils.answer(message, self.strings["all_cleared"])

    @loader.command(ru_doc="— очистить все блокировки", en_doc="— clear all blocks")
    async def clearblocks(self, message: Message):
        """Clear all blocks"""
        self.blocked_packs.clear()
        self.blocked_stickers.clear()
        self.blocked_emojis.clear()
        self._save_blocklists()

        await utils.answer(message, self.strings["all_cleared"])

    async def watcher(self, message: Message):
        """Monitor messages and block unwanted content"""
        if not self._client or not self._db:
            return

        if message.is_group or message.is_channel:
            return

        should_block, reason = await self._should_block_message(message)

        if should_block:
            logger.info(f"Blocking message: {reason}")
            await self._delete_message(message)
