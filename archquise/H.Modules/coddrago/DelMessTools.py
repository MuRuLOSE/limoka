# ---------------------------------------------------------------------------------
# ░█▀▄░▄▀▀▄░█▀▄░█▀▀▄░█▀▀▄░█▀▀▀░▄▀▀▄░░░█▀▄▀█
# ░█░░░█░░█░█░█░█▄▄▀░█▄▄█░█░▀▄░█░░█░░░█░▀░█
# ░▀▀▀░░▀▀░░▀▀░░▀░▀▀░▀░░▀░▀▀▀▀░░▀▀░░░░▀░░▒▀
# Name: DelMessTools
# Description: Module to manage and delete your messages in the current chat
# Author: @codrago_m
# ---------------------------------------------------------------------------------
# 🔒    Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html
# ---------------------------------------------------------------------------------
# Author: @codrago
# Commands: nopurge, purgetime, purgelength, purgekeyword, purge
# scope: hikka_only
# meta developer: @codrago_m
# meta banner: https://raw.githubusercontent.com/coddrago/modules/refs/heads/main/banner.png
# meta pic: https://envs.sh/HJx.webp
# ---------------------------------------------------------------------------------

__version__ = (1, 1, 0)

from telethon.tl.types import Message, DocumentAttributeFilename

from .. import loader, utils


class DelMessTools(loader.Module):
    """Module to manage and delete your messages in the current chat"""

    strings = {
        "name": "DelMessTools",
        "purge_complete": "All your messages have been deleted.",
        "purge_reply_complete": "Messages up to the replied message have been deleted.",
        "purge_keyword_complete": "Messages containing the keyword have been deleted.",
        "purge_time_complete": "Messages within the specified time range have been deleted.",
        "purge_media_complete": "All your media messages have been deleted.",
        "purge_length_complete": "Messages with the specified length have been deleted.",
        "purge_type_complete": "Messages of the specified type have been deleted.",
        "enabled": "It's not operational now anyway.",
        "disabled": "Operation status changed to disabled.",
        "interrupted": "The deletion was interrupted because you changed your mind.",
        "none": "You didn't even intend to delete anything here, but anyway it's disabled now.",
        "no_args": "Please specify arguments for the command.",
        "no_keyword": "Please specify a keyword to delete messages.",
        "no_length": "Please specify a valid length.",
        "invalid_time": "Invalid time format. Please use the format: YYYY-MM-DD HH:MM:SS",
        "invalid_length": "Please specify a valid number for length.",
    }

    strings_ru = {
        "purge_complete": "Все ваши сообщения были удалены.",
        "purge_reply_complete": "Сообщения до указанного ответа были удалены.",
        "purge_keyword_complete": "Сообщения, содержащие ключевое слово, были удалены.",
        "purge_time_complete": "Сообщения в указанном временном диапазоне были удалены.",
        "purge_media_complete": "Все ваши медиа-сообщения были удалены.",
        "purge_length_complete": "Сообщения указанной длины были удалены.",
        "purge_type_complete": "Сообщения указанного типа были удалены.",
        "enabled": "Оно итак сейчас не работает.",
        "disabled": "Режим работы изменен на выключено.",
        "interrupted": "Удаление было прервано т.к вы передумали.",
        "none": "Вы даже не пытались ничего здесь удалить, в любом случае сейчас оно выключено.",
        "no_args": "Пожалуйста, укажите аргументы для команды.",
        "no_keyword": "Пожалуйста, укажите ключевое слово для удаления сообщений.",
        "no_length": "Пожалуйста, укажите корректную длину.",
        "invalid_time": "Неверный формат времени. Используйте формат: YYYY-MM-DD HH:MM:SS",
        "invalid_length": "Пожалуйста, укажите корректное число для длины.",
    }

    def __init__(self):
        self.client = None
        self.db = None
        self.tg_id = None

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.tg_id = (await client.get_me()).id

    @loader.command(
        ru_doc="[reply] [-img] [-voice] [-file] [-all] - удалить все ваши сообщения в текущем чате или только до сообщения, на которое ответили\n        -all - удалять сообщения в каждой теме, если это форум, иначе флаг игнорируется",
        en_doc="[reply] [-img] [-voice] [-file] [-all] - delete all your messages in current chat or only ones up to the message you replied to\n        -all - to delete messages in each topic if this is a forum otherwise the flag'll just be ignored",
    )
    async def purge(self, message: Message):
        if not self.client or not self.db or not self.tg_id:
            return

        reply = await message.get_reply_message()
        is_last = False
        args, types_filter, is_each = self.get_types_filter(message)

        try:
            entity = await self.client.get_entity(message.chat.id)
            is_forum = getattr(entity, "forum", False)
        except Exception:
            is_forum = False

        status = self.db.get(__name__, "status", {})
        status[message.chat.id] = True
        self.db.set(__name__, "status", status)

        deleted_count = 0
        async for i in self.client.iter_messages(message.peer_id):
            status = self.db.get(__name__, "status", {})
            if status.get(message.chat.id, None) is not True:
                return await utils.answer(message, self.strings["interrupted"])

            if is_forum and not is_each:
                try:
                    if utils.get_topic(message) != utils.get_topic(i):
                        continue
                except Exception:
                    pass

            if i.from_id == self.tg_id and self.is_valid_type(i, types_filter):
                if reply:
                    if is_last:
                        break
                    if i.id == reply.id:
                        is_last = True
                try:
                    await self.client.delete_messages(message.peer_id, [i.id])
                    deleted_count += 1
                except Exception:
                    pass

        if reply:
            await utils.answer(message, self.strings["purge_reply_complete"])
        else:
            await utils.answer(message, self.strings["purge_complete"])

    @loader.command(
        ru_doc="<ключевое слово> [-img] [-voice] [-file] [-all] - удалить все ваши сообщения с указанным ключевым словом в текущем чате\n        -all - удалять сообщения в каждой теме, если это форум, иначе флаг игнорируется",
        en_doc="<keyword> [-img] [-voice] [-file] [-all] - delete all your messages containing the specified keyword in the current chat\n        -all - to delete messages in each topic if this is a forum otherwise the flag'll just be ignored",
    )
    async def purgekeyword(self, message: Message):
        if not self.client or not self.db or not self.tg_id:
            return

        args = utils.get_args_raw(message)
        if not args:
            return await utils.answer(message, self.strings["no_args"])

        args, types_filter, is_each = self.get_types_filter(message)
        if not args:
            return await utils.answer(message, self.strings["no_keyword"])

        try:
            entity = await self.client.get_entity(message.chat.id)
            is_forum = getattr(entity, "forum", False)
        except Exception:
            is_forum = False

        status = self.db.get(__name__, "status", {})
        status[message.chat.id] = True
        self.db.set(__name__, "status", status)

        deleted_count = 0
        async for i in self.client.iter_messages(message.peer_id):
            status = self.db.get(__name__, "status", {})
            if status.get(message.chat.id, None) is not True:
                return await utils.answer(message, self.strings["interrupted"])

            if is_forum and not is_each:
                try:
                    if utils.get_topic(message) != utils.get_topic(i):
                        continue
                except Exception:
                    pass

            if (
                i.from_id == self.tg_id
                and args.lower() in (i.text or "").lower()
                and self.is_valid_type(i, types_filter)
            ):
                try:
                    await self.client.delete_messages(message.chat.id, [i.id])
                    deleted_count += 1
                except Exception:
                    pass

        await utils.answer(message, self.strings["purge_keyword_complete"])

    @loader.command(
        ru_doc="<начальное время> <конечное время> [-img] [-voice] [-file] [-all] - удалить все ваши сообщения в указанном временном диапазоне в текущем чате\n        -all - удалять сообщения в каждой теме, если это форум, иначе флаг игнорируется\n        Формат времени: YYYY-MM-DD HH:MM:SS",
        en_doc="<start_time> <end_time> [-img] [-voice] [-file] [-all] - delete all your messages within the specified time range in the current chat\n        -all - to delete messages in each topic if this is a forum otherwise the flag'll just be ignored\n        Time format: YYYY-MM-DD HH:MM:SS",
    )
    async def purgetime(self, message: Message):
        if not self.client or not self.db or not self.tg_id:
            return

        args = utils.get_args_raw(message)
        if not args:
            return await utils.answer(message, self.strings["no_args"])

        args, types_filter, is_each = self.get_types_filter(message)
        args = args.split()

        if not args or len(args) < 2:
            return await utils.answer(message, self.strings["no_args"])

        from datetime import datetime

        try:
            start_time = datetime.strptime(args[0], "%Y-%m-%d %H:%M:%S")
            end_time = datetime.strptime(args[1], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return await utils.answer(message, self.strings["invalid_time"])

        try:
            entity = await self.client.get_entity(message.chat.id)
            is_forum = getattr(entity, "forum", False)
        except Exception:
            is_forum = False

        status = self.db.get(__name__, "status", {})
        status[message.chat.id] = True
        self.db.set(__name__, "status", status)

        deleted_count = 0
        async for i in self.client.iter_messages(message.peer_id):
            status = self.db.get(__name__, "status", {})
            if status.get(message.chat.id, None) is not True:
                return await utils.answer(message, self.strings["interrupted"])

            if is_forum and not is_each:
                try:
                    if utils.get_topic(message) != utils.get_topic(i):
                        continue
                except Exception:
                    pass

            if (
                i.from_id == self.tg_id
                and start_time <= i.date <= end_time
                and self.is_valid_type(i, types_filter)
            ):
                try:
                    await self.client.delete_messages(message.peer_id, [i.id])
                    deleted_count += 1
                except Exception:
                    pass

        await utils.answer(message, self.strings["purge_time_complete"])

    @loader.command(
        ru_doc="<длина> [-img] [-voice] [-file] [-all] - удалить все ваши сообщения указанной длины в текущем чате\n        -all - удалять сообщения в каждой теме, если это форум, иначе флаг игнорируется",
        en_doc="<length> [-img] [-voice] [-file] [-all] - delete all your messages with the specified length in the current chat\n        -all - to delete messages in each topic if this is a forum otherwise the flag'll just be ignored",
    )
    async def purgelength(self, message: Message):
        if not self.client or not self.db or not self.tg_id:
            return

        args = utils.get_args_raw(message)
        if not args:
            return await utils.answer(message, self.strings["no_args"])

        args, types_filter, is_each = self.get_types_filter(message)
        if not args:
            return await utils.answer(message, self.strings["no_length"])

        try:
            length = int(args)
        except ValueError:
            return await utils.answer(message, self.strings["invalid_length"])

        try:
            entity = await self.client.get_entity(message.chat.id)
            is_forum = getattr(entity, "forum", False)
        except Exception:
            is_forum = False

        status = self.db.get(__name__, "status", {})
        status[message.chat.id] = True
        self.db.set(__name__, "status", status)

        deleted_count = 0
        async for i in self.client.iter_messages(message.peer_id):
            status = self.db.get(__name__, "status", {})
            if status.get(message.chat.id, None) is not True:
                return await utils.answer(message, self.strings["interrupted"])

            if is_forum and not is_each:
                try:
                    if utils.get_topic(message) != utils.get_topic(i):
                        continue
                except Exception:
                    pass

            if (
                i.from_id == self.tg_id
                and len(i.text or "") == length
                and self.is_valid_type(i, types_filter)
            ):
                try:
                    await self.client.delete_messages(message.peer_id, [i.id])
                    deleted_count += 1
                except Exception:
                    pass

        await utils.answer(message, self.strings["purge_length_complete"])

    @loader.command(
        ru_doc="Прервать процесс удаления\nИспользуйте в чате, где вы ранее начали удаление",
        en_doc="Interrupt the deletion process\nUse in the chat where you've previously started deletion",
    )
    async def nopurge(self, message: Message):
        if not self.db:
            return

        chat_id = utils.get_chat_id(message)

        status = self.db.get(__name__, "status", {})
        _status = status.get(chat_id, None)
        status[chat_id] = False
        self.db.set(__name__, "status", status)

        if _status is True:
            await utils.answer(message, self.strings["disabled"])
        elif _status is False:
            await utils.answer(message, self.strings["enabled"])
        else:
            await utils.answer(message, self.strings["none"])

    def get_types_filter(self, message: Message):
        """Get the types filter from the command arguments."""
        args_raw = utils.get_args_raw(message)
        if not args_raw:
            return "", [], False

        args = args_raw.split()
        types_filter = []
        valid_types = ["-img", "-voice", "-file", "-all"]
        is_each = "-all" in args

        _args = args_raw
        args_ = ""

        for i, arg in enumerate(args):
            if arg in valid_types:
                _args = " ".join(args[:i])
                args_ = " ".join(args[i:])
                break

        if "-img" in args_:
            types_filter.append("img")
        if "-voice" in args_:
            types_filter.append("voice")
        if "-file" in args_:
            types_filter.append("file")
        if "-all" in args_:
            is_each = True

        return _args, types_filter, is_each

    def is_valid_type(self, message: Message, types_filter):
        """Check if the message matches the specified types filter."""
        if not types_filter:
            return True  # No filtering means all types are valid

        if "img" in types_filter and hasattr(message, "photo") and message.photo:
            return True
        if "voice" in types_filter and hasattr(message, "voice") and message.voice:
            return True
        if "file" in types_filter and hasattr(message, "document") and message.document:
            for attr in getattr(message.document, "attributes", []):
                if isinstance(attr, DocumentAttributeFilename):
                    return True

        return False
