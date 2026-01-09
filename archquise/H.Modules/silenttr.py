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
# Name: Silent T&R
# Description: Silent tags and reactions
# Author: @hikka_mods
# ---------------------------------------------------------------------------------
# meta developer: @hikka_mods
# scope: Silent T&R
# scope: Silent T&R 0.0.1
# ---------------------------------------------------------------------------------

from telethon.types import Message

from .. import loader, utils


@loader.tds
class SilentTRMod(loader.Module):
    """Silent tags and reactions"""

    strings = {
        "name": "Silent T&R",
        "global_reactions_on": "✅ Global silent reactions enabled",
        "global_reactions_off": "❌ Global silent reactions disabled",
        "global_tags_on": "✅ Global silent tags enabled",
        "global_tags_off": "❌ Global silent tags disabled",
        "chat_reactions_on": "✅ Silent reactions enabled in this chat",
        "chat_reactions_off": "❌ Silent reactions disabled in this chat",
        "chat_tags_on": "✅ Silent tags enabled in this chat",
        "chat_tags_off": "❌ Silent tags disabled in this chat",
        "ignore_added": "✅ User added to global ignore list",
        "ignore_removed": "❌ User removed from global ignore list",
        "hignore_added": "✅ User added to ignore list in this chat",
        "hignore_removed": "❌ User removed from ignore list in this chat",
        "no_reply": "❌ Reply to a user or specify username",
        "user_not_found": "❌ User not found",
        "args_error": "❌ Use: .sreacts on/off or .sreacts",
        "chat_args_error": "❌ Use: .hsreacts on/off or .hsreacts",
        "status": "📊 Silent T&R status:\n\nGlobal:\n  Reactions: {}\n  Tags: {}\n\nThis chat:\n  Reactions: {}\n  Tags: {}\n\nGlobal ignore: {}\nChat ignore: {}",
    }

    strings_ru = {
        "global_reactions_on": "✅ Глобальные тихие реакции включены",
        "global_reactions_off": "❌ Глобальные тихие реакции выключены",
        "global_tags_on": "✅ Глобальные тихие упоминания включены",
        "global_tags_off": "❌ Глобальные тихие упоминания выключены",
        "chat_reactions_on": "✅ Тихие реакции включены в этом чате",
        "chat_reactions_off": "❌ Тихие реакции выключены в этом чате",
        "chat_tags_on": "✅ Тихие упоминания включены в этом чате",
        "chat_tags_off": "❌ Тихие упоминания выключены в этом чате",
        "ignore_added": "✅ Пользователь добавлен в глобальный игнор-лист",
        "ignore_removed": "❌ Пользователь удален из глобального игнор-листа",
        "hignore_added": "✅ Пользователь добавлен в игнор-лист этого чата",
        "hignore_removed": "❌ Пользователь удален из игнор-листа этого чата",
        "no_reply": "❌ Ответьте на пользователя или укажите username",
        "user_not_found": "❌ Пользователь не найден",
        "args_error": "❌ Используйте: .sreacts on/off или .sreacts",
        "chat_args_error": "❌ Используйте: .hsreacts on/off или .hsreacts",
        "status": "📊 Статус Silent T&R:\n\nГлобально:\n  Реакции: {}\n  Упоминания: {}\n\nВ этом чате:\n  Реакции: {}\n  Упоминания: {}\n\nГлобальный игнор: {}\nИгнор в чате: {}",
    }

    async def client_ready(self, client, db):
        self._client = client
        self._db = db

        self._global_settings = self._db.get(
            __name__, "global_settings", {"reactions": False, "tags": False}
        )
        self._chat_settings = self._db.get(__name__, "chat_settings", {})
        self._global_ignore = self._db.get(__name__, "global_ignore", [])
        self._chat_ignore = self._db.get(__name__, "chat_ignore", {})

        client.add_event_handler(self._on_message_reaction_updated)
        client.add_event_handler(self._on_new_message)

    async def on_unload(self):
        self._client.remove_event_handler(self._on_message_reaction_updated)
        self._client.remove_event_handler(self._on_new_message)

    def _save_global_settings(self):
        self._db.set(__name__, "global_settings", self._global_settings)

    def _save_chat_settings(self):
        self._db.set(__name__, "chat_settings", self._chat_settings)

    def _save_global_ignore(self):
        self._db.set(__name__, "global_ignore", self._global_ignore)

    def _save_chat_ignore(self):
        self._db.set(__name__, "chat_ignore", self._chat_ignore)

    async def _on_message_reaction_updated(self, event):
        """Обработчик обновления реакций"""
        try:
            message = await self._client.get_messages(
                event.chat_id, ids=event.message_id
            )
        except Exception:
            return

        if message.sender_id != (await self._client.get_me()).id:
            return

        chat_id = str(event.chat_id)
        user_id = event.user_id

        if user_id in self._global_ignore:
            return

        if chat_id in self._chat_ignore and user_id in self._chat_ignore[chat_id]:
            return

        chat_settings = self._chat_settings.get(
            chat_id, {"reactions": None, "tags": None}
        )
        if chat_settings["reactions"] is None:
            if not self._global_settings["reactions"]:
                return
        else:
            if not chat_settings["reactions"]:
                return

        await self._client.read_messages(event.chat_id, event.message_id)

    async def _on_new_message(self, event):
        """Обработчик новых сообщений для упоминаний"""

        if event.out:
            return

        me = await self._client.get_me()
        mentioned = False
        if event.mentioned:
            mentioned = True
        else:
            if event.entities:
                for entity in event.entities:
                    if entity.type == "mentionName" and entity.user_id == me.id:
                        mentioned = True
                        break
                    elif entity.type == "textMention" and entity.user_id == me.id:
                        mentioned = True
                        break

        if not mentioned:
            return

        chat_id = str(event.chat_id)
        user_id = event.sender_id

        if user_id in self._global_ignore:
            return

        if chat_id in self._chat_ignore and user_id in self._chat_ignore[chat_id]:
            return

        chat_settings = self._chat_settings.get(
            chat_id, {"reactions": None, "tags": None}
        )
        if chat_settings["tags"] is None:
            if not self._global_settings["tags"]:
                return
        else:
            if not chat_settings["tags"]:
                return

        await event.mark_read()

    @loader.command(
        ru_doc="[on/off] - тихие реакции во всех чатах",
        en_doc="[on/off] - silent reactions in all chats",
    )
    async def sreacts(self, message: Message):
        """Toggle global silent reactions"""
        args = utils.get_args_raw(message).lower()
        if args == "on":
            self._global_settings["reactions"] = True
            self._save_global_settings()
            await utils.answer(message, self.strings["global_reactions_on"])
        elif args == "off":
            self._global_settings["reactions"] = False
            self._save_global_settings()
            await utils.answer(message, self.strings["global_reactions_off"])
        elif args == "":
            status = "on" if self._global_settings["reactions"] else "off"
            await utils.answer(message, f"Global silent reactions: {status}")
        else:
            await utils.answer(message, self.strings["args_error"])

    @loader.command(
        ru_doc="[on/off] - тихие упоминания во всех чатах",
        en_doc="[on/off] - silent tags in all chats",
    )
    async def stags(self, message: Message):
        """Toggle global silent tags"""
        args = utils.get_args_raw(message).lower()
        if args == "on":
            self._global_settings["tags"] = True
            self._save_global_settings()
            await utils.answer(message, self.strings["global_tags_on"])
        elif args == "off":
            self._global_settings["tags"] = False
            self._save_global_settings()
            await utils.answer(message, self.strings["global_tags_off"])
        elif args == "":
            status = "on" if self._global_settings["tags"] else "off"
            await utils.answer(message, f"Global silent tags: {status}")
        else:
            await utils.answer(message, self.strings["args_error"])

    @loader.command(
        ru_doc="[on/off] - тихие реакции и упоминания во всех чатах",
        en_doc="[on/off] - silent reactions and tags in all chats",
    )
    async def sall(self, message: Message):
        """Toggle global silent reactions and tags"""
        args = utils.get_args_raw(message).lower()
        if args == "on":
            self._global_settings["reactions"] = True
            self._global_settings["tags"] = True
            self._save_global_settings()
            await utils.answer(message, "✅ Global silent reactions and tags enabled")
        elif args == "off":
            self._global_settings["reactions"] = False
            self._global_settings["tags"] = False
            self._save_global_settings()
            await utils.answer(message, "❌ Global silent reactions and tags disabled")
        elif args == "":
            status_r = "on" if self._global_settings["reactions"] else "off"
            status_t = "on" if self._global_settings["tags"] else "off"
            await utils.answer(
                message, f"Global silent reactions: {status_r}, tags: {status_t}"
            )
        else:
            await utils.answer(message, self.strings["args_error"])

    @loader.command(
        ru_doc="[on/off] - тихие реакции в этом чате",
        en_doc="[on/off] - silent reactions in this chat",
    )
    async def hsreacts(self, message: Message):
        """Toggle silent reactions in this chat"""
        args = utils.get_args_raw(message).lower()
        chat_id = str(message.chat_id)

        # Получаем настройки чата или создаем новые
        chat_settings = self._chat_settings.get(
            chat_id, {"reactions": None, "tags": None}
        )

        if args == "on":
            chat_settings["reactions"] = True
            self._chat_settings[chat_id] = chat_settings
            self._save_chat_settings()
            await utils.answer(message, self.strings["chat_reactions_on"])
        elif args == "off":
            chat_settings["reactions"] = False
            self._chat_settings[chat_id] = chat_settings
            self._save_chat_settings()
            await utils.answer(message, self.strings["chat_reactions_off"])
        elif args == "":
            status = chat_settings["reactions"]
            if status is None:
                status = (
                    "global ("
                    + ("on" if self._global_settings["reactions"] else "off")
                    + ")"
                )
            else:
                status = "on" if status else "off"
            await utils.answer(message, f"Silent reactions in this chat: {status}")
        else:
            await utils.answer(message, self.strings["chat_args_error"])

    @loader.command(
        ru_doc="[on/off] - тихие упоминания в этом чате",
        en_doc="[on/off] - silent tags in this chat",
    )
    async def hstags(self, message: Message):
        """Toggle silent tags in this chat"""
        args = utils.get_args_raw(message).lower()
        chat_id = str(message.chat_id)

        chat_settings = self._chat_settings.get(
            chat_id, {"reactions": None, "tags": None}
        )

        if args == "on":
            chat_settings["tags"] = True
            self._chat_settings[chat_id] = chat_settings
            self._save_chat_settings()
            await utils.answer(message, self.strings["chat_tags_on"])
        elif args == "off":
            chat_settings["tags"] = False
            self._chat_settings[chat_id] = chat_settings
            self._save_chat_settings()
            await utils.answer(message, self.strings["chat_tags_off"])
        elif args == "":
            status = chat_settings["tags"]
            if status is None:
                status = (
                    "global ("
                    + ("on" if self._global_settings["tags"] else "off")
                    + ")"
                )
            else:
                status = "on" if status else "off"
            await utils.answer(message, f"Silent tags in this chat: {status}")
        else:
            await utils.answer(message, self.strings["chat_args_error"])

    @loader.command(
        ru_doc="[on/off] - тихие реакции и упоминания в этом чате",
        en_doc="[on/off] - silent reactions and tags in this chat",
    )
    async def hsall(self, message: Message):
        """Toggle silent reactions and tags in this chat"""
        args = utils.get_args_raw(message).lower()
        chat_id = str(message.chat_id)

        chat_settings = self._chat_settings.get(
            chat_id, {"reactions": None, "tags": None}
        )

        if args == "on":
            chat_settings["reactions"] = True
            chat_settings["tags"] = True
            self._chat_settings[chat_id] = chat_settings
            self._save_chat_settings()
            await utils.answer(
                message, "✅ Silent reactions and tags enabled in this chat"
            )
        elif args == "off":
            chat_settings["reactions"] = False
            chat_settings["tags"] = False
            self._chat_settings[chat_id] = chat_settings
            self._save_chat_settings()
            await utils.answer(
                message, "❌ Silent reactions and tags disabled in this chat"
            )
        elif args == "":
            status_r = chat_settings["reactions"]
            if status_r is None:
                status_r = (
                    "global ("
                    + ("on" if self._global_settings["reactions"] else "off")
                    + ")"
                )
            else:
                status_r = "on" if status_r else "off"
            status_t = chat_settings["tags"]
            if status_t is None:
                status_t = (
                    "global ("
                    + ("on" if self._global_settings["tags"] else "off")
                    + ")"
                )
            else:
                status_t = "on" if status_t else "off"
            await utils.answer(
                message, f"Silent reactions: {status_r}, tags: {status_t} in this chat"
            )
        else:
            await utils.answer(message, self.strings["chat_args_error"])

    async def _get_user_id(self, message: Message):
        """Получить ID пользователя из аргументов или ответа"""
        reply = await message.get_reply_message()
        args = utils.get_args_raw(message)

        if reply:
            return reply.sender_id
        elif args:
            try:
                user = await self._client.get_entity(args)
                return user.id
            except Exception:
                return None
        else:
            return None

    @loader.command(
        ru_doc="[ответ/username] - игнорировать пользователя глобально",
        en_doc="[reply/username] - ignore user globally",
    )
    async def ignore(self, message: Message):
        """Toggle ignore user globally"""
        user_id = await self._get_user_id(message)
        if not user_id:
            await utils.answer(message, self.strings["no_reply"])
            return

        if user_id in self._global_ignore:
            self._global_ignore.remove(user_id)
            await utils.answer(message, self.strings["ignore_removed"])
        else:
            self._global_ignore.append(user_id)
            await utils.answer(message, self.strings["ignore_added"])

        self._save_global_ignore()

    @loader.command(
        ru_doc="[ответ/username] - игнорировать пользователя в этом чате",
        en_doc="[reply/username] - ignore user in this chat",
    )
    async def hignore(self, message: Message):
        """Toggle ignore user in this chat"""
        user_id = await self._get_user_id(message)
        if not user_id:
            await utils.answer(message, self.strings["no_reply"])
            return

        chat_id = str(message.chat_id)

        if chat_id not in self._chat_ignore:
            self._chat_ignore[chat_id] = []

        if user_id in self._chat_ignore[chat_id]:
            self._chat_ignore[chat_id].remove(user_id)
            await utils.answer(message, self.strings["hignore_removed"])
        else:
            self._chat_ignore[chat_id].append(user_id)
            await utils.answer(message, self.strings["hignore_added"])

        self._save_chat_ignore()

    @loader.command(
        ru_doc="Показать статус Silent T&R", en_doc="Show Silent T&R status"
    )
    async def strstatus(self, message: Message):
        """Show status"""
        global_reactions = "on" if self._global_settings["reactions"] else "off"
        global_tags = "on" if self._global_settings["tags"] else "off"

        chat_id = str(message.chat_id)
        chat_settings = self._chat_settings.get(
            chat_id, {"reactions": None, "tags": None}
        )
        chat_reactions = chat_settings["reactions"]
        if chat_reactions is None:
            chat_reactions = "global"
        else:
            chat_reactions = "on" if chat_reactions else "off"
        chat_tags = chat_settings["tags"]
        if chat_tags is None:
            chat_tags = "global"
        else:
            chat_tags = "on" if chat_tags else "off"

        global_ignore_count = len(self._global_ignore)
        chat_ignore_count = len(self._chat_ignore.get(chat_id, []))

        await utils.answer(
            message,
            self.strings["status"].format(
                global_reactions,
                global_tags,
                chat_reactions,
                chat_tags,
                global_ignore_count,
                chat_ignore_count,
            ),
        )
