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
# Name: MessageMonitor
# Description: Monitor messages for trigger words in all chats.
# Author: @hikka_mods
# ---------------------------------------------------------------------------------
# meta developer: @hikka_mods
# scope: MessageMonitor
# scope: MessageMonitor 0.0.1
# ---------------------------------------------------------------------------------

import logging
import re
from typing import List, Optional

from telethon.types import Message

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class MessageMonitor(loader.Module):
    """
    Monitor messages for trigger words in all chats.
    """

    strings = {
        "name": "MessageMonitor",
        "triggers_set": "<emoji document_id=5854762571659218443>✅</emoji> Trigger words have been set: <code>{}</code>",
        "triggers_not_set": "<emoji document_id=5854929766146118183>❌</emoji> Trigger words have not been set",
        "target_set": "<emoji document_id=5854762571659218443>✅</emoji> Target chat for notifications has been set",
        "target_not_set": "<emoji document_id=5854929766146118183>❌</emoji> Target chat for notifications has not been set",
        "monitoring_started": "<emoji document_id=5188311512791393083>🌎</emoji> Monitoring has started",
        "monitoring_stopped": "<emoji document_id=5854929766146118183>❌</emoji> Monitoring has stopped",
        "monitoring_status": "<emoji document_id=5188311512791393083>🌎</emoji> Monitoring <b>{}</b>",
        "triggers_example": "<emoji document_id=5854929766146118183>❌</emoji> Example: <code>.triggers word1 word2</code>",
        "monitoring_status_on": "<emoji document_id=5854762571659218443>✅</emoji> enabled",
        "monitoring_status_off": "<emoji document_id=5854929766146118183>❌</emoji> disabled",
        "ignore_set": "<emoji document_id=5854762571659218443>✅</emoji> Ignored chats have been set: <code>{}</code>",
        "ignore_none": "<emoji document_id=5854929766146118183>❌</emoji> Ignored chats have not been set",
        "ignore_example": "<emoji document_id=5854929766146118183>❌</emoji> Example: <code>.ignore 123456789 -987654321</code> (chat IDs)",
        "no_reply": "<emoji document_id=5854929766146118183>❌</emoji> Reply to a message in the desired chat or specify its ID",
        "monitoring_msg": (
            "<emoji document_id=5854929766146118183>🚨</emoji> <b>Trigger word detected!</b> <emoji document_id=5854929766146118183>🚨</emoji>\n\n"
            "<b>Chat:</b> <code>{}</code>\n"
            "<b>User:</b> {}\n"
            "<b>Link:</b> <a href='{}'>{}</a>\n\n"
            "<b>Message:</b>\n{}"
        ),
    }

    strings_ru = {
        "triggers_set": "<emoji document_id=5854762571659218443>✅</emoji> Триггерные слова установлены: <code>{}</code>",
        "triggers_not_set": "<emoji document_id=5854929766146118183>❌</emoji> Триггерные слова не установлены",
        "target_set": "<emoji document_id=5854762571659218443>✅</emoji> Целевой чат для уведомлений установлен",
        "target_not_set": "<emoji document_id=5854929766146118183>❌</emoji> Целевой чат для уведомлений не установлен",
        "monitoring_started": "<emoji document_id=5188311512791393083>🌎</emoji> Мониторинг запущен",
        "monitoring_stopped": "<emoji document_id=5854929766146118183>❌</emoji> Мониторинг остановлен",
        "monitoring_status": "<emoji document_id=5188311512791393083>🌎</emoji> Мониторинг <b>{}</b>",
        "triggers_example": "<emoji document_id=5854929766146118183>❌</emoji> Пример: <code>.triggers слово1 слово2</code>",
        "monitoring_status_on": "<emoji document_id=5854762571659218443>✅</emoji> включен",
        "monitoring_status_off": "<emoji document_id=5854929766146118183>❌</emoji> выключен",
        "ignore_set": "<emoji document_id=5854762571659218443>✅</emoji> Игнорируемые чаты установлены: <code>{}</code>",
        "ignore_none": "<emoji document_id=5854929766146118183>❌</emoji> Игнорируемые чаты не установлены",
        "ignore_example": "<emoji document_id=5854929766146118183>❌</emoji> Пример: <code>.ignore 123456789 -987654321</code> (ID чатов)",
        "no_reply": "<emoji document_id=5854929766146118183>❌</emoji> Ответьте на сообщение в нужном чате или укажите его ID",
        "monitoring_msg": (
            "<emoji document_id=5854929766146118183>🚨</emoji> <b>Обнаружено триггерное слово!</b> <emoji document_id=5854929766146118183>🚨</emoji>\n\n"
            "<b>Чат:</b> <code>{}</code>\n"
            "<b>Пользователь:</b> {}\n"
            "<b>Ссылка:</b> <a href='{}'>{}</a>\n\n"
            "<b>Сообщение:</b>\n{}"
        ),
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "triggers",
                [],
                "List of trigger words to monitor",
                validator=loader.validators.Series(),
            ),
            loader.ConfigValue(
                "target_chat",
                None,
                "Target chat ID for notifications",
                validator=loader.validators.Integer(),
            ),
            loader.ConfigValue(
                "ignore_chats",
                [],
                "List of chat IDs to ignore",
                validator=loader.validators.Series(),
            ),
        )
        self._triggers: List[str] = []
        self._target_chat: Optional[int] = None
        self._ignore_chats: List[int] = []
        self._compiled_patterns: List[re.Pattern] = []

    async def client_ready(self, client, db):
        """Initialize module when client is ready"""
        await self._update_config()
        self.client = client

    async def _update_config(self):
        """Update internal configuration and compile regex patterns"""
        self._triggers = [trigger.lower() for trigger in self.config["triggers"]]
        self._target_chat = self.config["target_chat"]
        self._ignore_chats = [
            int(chat_id)
            for chat_id in self.config["ignore_chats"]
            if str(chat_id).lstrip("-").isdigit()
        ]

        self._compiled_patterns = [
            re.compile(r"\b" + re.escape(trigger) + r"\b", re.IGNORECASE)
            for trigger in self._triggers
        ]

    @loader.command(
        ru_doc="Показать статус мониторинга",
        en_doc="Show monitoring status",
    )
    async def status(self, message: Message):
        """Show current monitoring status"""
        status_text = (
            self.strings["monitoring_status_on"]
            if self._target_chat and self._triggers
            else self.strings["monitoring_status_off"]
        )
        await utils.answer(
            message, self.strings["monitoring_status"].format(status_text)
        )

    @loader.command(
        ru_doc="Установить триггерные слова. Пример: .triggers слово1 слово2",
        en_doc="Set trigger words. Example: .triggers word1 word2",
    )
    async def triggers(self, message: Message):
        """Set trigger words"""
        args = utils.get_args(message)
        if not args:
            await utils.answer(message, self.strings["triggers_example"])
            return

        self._triggers = [arg.lower() for arg in args]
        self.config["triggers"] = self._triggers
        await self._update_config()
        await utils.answer(
            message, self.strings["triggers_set"].format(", ".join(self._triggers))
        )

    @loader.command(
        ru_doc="Установить целевой чат для уведомлений. Ответьте на сообщение или укажите ID",
        en_doc="Set target chat for notifications. Reply to a message or provide its ID",
    )
    async def settarget(self, message: Message):
        """Set target chat"""
        args = utils.get_args_raw(message)
        chat_id = None

        if getattr(message, "is_reply", False):
            reply_message = await message.get_reply_message()
            if reply_message and hasattr(reply_message, "chat_id"):
                chat_id = reply_message.chat_id
        elif args and (args.isdigit() or (args.startswith("-") and args[1:].isdigit())):
            chat_id = int(args)

        if chat_id:
            self.config["target_chat"] = chat_id
            self._target_chat = chat_id
            await utils.answer(message, self.strings["target_set"])
        else:
            await utils.answer(message, self.strings["no_reply"])

    @loader.command(
        ru_doc="Установить игнорируемые чаты. Укажите ID чатов через пробел.",
        en_doc="Set ignored chats. Provide chat IDs separated by space.",
    )
    async def ignore(self, message: Message):
        """Set ignored chats"""
        args = utils.get_args(message)
        if not args:
            await utils.answer(message, self.strings["ignore_example"])
            return

        valid_ids = []
        for arg in args:
            if arg.isdigit() or (arg.startswith("-") and arg[1:].isdigit()):
                valid_ids.append(int(arg))

        self.config["ignore_chats"] = valid_ids
        await self._update_config()

        if valid_ids:
            await utils.answer(
                message,
                self.strings["ignore_set"].format(", ".join(map(str, valid_ids))),
            )
        else:
            await utils.answer(message, self.strings["ignore_none"])

    @loader.watcher(out=False, only_messages=True)
    async def message_watcher(self, message: Message):
        """Watch for messages containing trigger words"""
        if not self._target_chat or not self._triggers:
            return

        chat_id = getattr(message, "chat_id", None)
        if chat_id and chat_id in self._ignore_chats:
            logger.debug(f"Message in ignored chat: {chat_id}. Skipping monitoring.")
            return

        text = getattr(message, "text", "")
        if not text:
            return

        found_triggers = [
            trigger
            for pattern, trigger in zip(self._compiled_patterns, self._triggers)
            if pattern.search(text)
        ]

        if not found_triggers:
            return

        try:
            chat = await message.get_chat()
            chat_title = getattr(
                chat,
                "title",
                "Личные сообщения"
                if getattr(message, "is_private", False)
                else f"Чат с ID {chat_id}",
            )

            sender = await message.get_sender()
            if sender:
                sender_name = sender.first_name
                if getattr(sender, "last_name", None):
                    sender_name += f" {sender.last_name}"
                if not sender_name:
                    sender_name = getattr(
                        sender, "username", "Неизвестный пользователь"
                    )
            else:
                sender_name = "Неизвестный пользователь"

            link = await self._get_message_link(message, sender)

            await self.client.send_message(
                self._target_chat,
                self.strings["monitoring_msg"].format(
                    chat_title,
                    chat_id,
                    sender_name,
                    link,
                    text,
                ),
                parse_mode="HTML",
            )
            logger.debug(
                f"Sent notification about trigger word(s) {found_triggers} to chat {self._target_chat}"
            )
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def _get_message_link(self, message: Message, sender) -> str:
        """Generate message link based on message type"""
        message_id = message.id

        if getattr(message, "to_id", None):
            to_id_obj = getattr(message, "to_id")
            if getattr(to_id_obj, "channel_id", None):
                return f"https://t.me/c/{to_id_obj.channel_id}/{message_id}"

        if (
            getattr(message, "is_private", False)
            and sender
            and getattr(sender, "username", None)
        ):
            return f"https://t.me/{sender.username}/{message_id}"

        return f"https://t.me/c/{message_id}"
