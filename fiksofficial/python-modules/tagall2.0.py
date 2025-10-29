#         ______     ___  ___          _       _      
#    ____ | ___ \    |  \/  |         | |     | |     
#   / __ \| |_/ /   _| .  . | ___   __| |_   _| | ___ 
#  / / _` |  __/ | | | |\/| |/ _ \ / _` | | | | |/ _ \
# | | (_| | |  | |_| | |  | | (_) | (_| | |_| | |  __/
#  \ \__,_\_|   \__, \_|  |_/\___/ \__,_|\__,_|_|\___|
#   \____/       __/ |                                
#               |___/                                  

# На модуль распространяется лицензия "GNU General Public License v3.0"
# https://github.com/all-licenses/GNU-General-Public-License-v3.0

# meta developer: @pymodule

from .. import loader, utils
from telethon.tl.types import ChannelParticipantsAdmins, UserStatusRecently, UserStatusOnline, Message
import typing
import asyncio

@loader.tds
class TagAllMod(loader.Module):
    """TagAll 2.0 — smart mention of chat participants: .tagall {all/admins/online/active} {text}"""

    strings = {
        "name": "TagAll 2.0",
        "done": "✅ <b>{}</b> users mentioned",
        "no_users": "⚠️ No users found matching this filter",
        "invalid_args": "❌ Invalid command format. Use: .tagall {all/admins/online/active} {text}",
    }

    strings_ru = {
        "_cls_doc": "TagAll 2.0 — умное упоминание участников чата: .tagall {all/admins/online/active} {текст}",
        "done": "✅ Упомянуто <b>{}</b> пользователей",
        "no_users": "⚠️ Не найдено пользователей по данному фильтру",
        "invalid_args": "❌ Неверный формат команды. Используйте: .tagall {all/admins/online/active} {текст}",
    }

    async def client_ready(self, client, db):
        self.client = client

    @loader.command(ru_doc="Упомянуть участников: .tagall {all/admins/online/active} {текст}")
    async def tagallcmd(self, message: Message):
        """Mention members: .tagall {all/admins/online/active} {text}"""
        args = utils.get_args_raw(message).split(maxsplit=1)
        mode = args[0].lower() if args else None
        text = args[1] if len(args) > 1 else "Срочное собрание!"

        valid_modes = {"all", "admins", "online", "active"}

        if mode not in valid_modes:
            await utils.answer(message, self.strings["invalid_args"])
            return

        chat = await self.client.get_entity(message.chat_id)
        tagged = await self._do_tagall(chat, mode, text)
        if not tagged:
            await utils.answer(message, self.strings["no_users"])
            return
        await utils.answer(message, self.strings["done"].format(tagged))

    async def _do_tagall(self, chat, filter_: str, text: str = "") -> typing.Optional[int]:
        users = []

        try:
            if filter_ == "all":
                async for user in self.client.iter_participants(chat):
                    if not user.bot:
                        users.append(user)

            elif filter_ == "admins":
                async for user in self.client.iter_participants(chat, filter=ChannelParticipantsAdmins):
                    if not user.bot:
                        users.append(user)

            elif filter_ == "online":
                async for user in self.client.iter_participants(chat):
                    if not user.bot and isinstance(user.status, (UserStatusRecently, UserStatusOnline)):
                        users.append(user)

            elif filter_ == "active":
                user_ids = set()
                async for msg in self.client.iter_messages(chat, limit=50):
                    if msg.sender_id and msg.sender_id not in user_ids:
                        try:
                            user = await self.client.get_entity(msg.sender_id)
                            if not user.bot:
                                users.append(user)
                                user_ids.add(msg.sender_id)
                        except Exception:
                            continue

            if not users:
                return None

            batch_size = 5
            tagged = 0
            for i in range(0, len(users), batch_size):
                batch = users[i:i + batch_size]
                mentions = " ".join([f"<span class='tg-spoiler'><a href='tg://user?id={u.id}'>{u.first_name or 'User'}</a></span>" for u in batch])
                msg_text = f"<b>{text}</b>\n{mentions}" if text else mentions
                await self.client.send_message(chat, msg_text, link_preview=False, parse_mode="html")
                tagged += len(batch)
                if i + batch_size < len(users):
                    await asyncio.sleep(2)

            return tagged

        except Exception as e:
            self._log.error(f"Error in tagall: {e}")
            return None