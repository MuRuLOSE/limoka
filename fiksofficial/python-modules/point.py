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


@loader.tds
class PointSentenceCaseMod(loader.Module):
    """Automatically capitalizes the first letter of each sentence and adds a period at the end of the message (if there isn't one)."""

    strings = {
        "name": "PointSentenceCase",
        "enabled": "<b>The module is activated ✅</b>",
        "disabled": "<b>The module is deactivated ❌</b>",
        "status": "Current status: {status}\nIgnore channels: {ignore_channels}\n\nUsage:\n<code>.pointcase on|off</code>\n<code>.pointcaseignore on|off</code>",
        "status_on": "✅ Enabled",
        "status_off": "❌ Off",
        "ignore_on": "✅ Ignoring channels",
        "ignore_off": "❌ Not ignoring channels",
    }

    strings_ru = {
        "_cls_doc": "Автоматически делает первую букву каждого предложения заглавной и добавляет точку в конце сообщения (если её нет).",
        "enabled": "<b>Модуль активирован ✅</b>",
        "disabled": "<b>Модуль деактивирован ❌</b>",
        "status": "Текущий статус: {status}\nИгнорировать каналы: {ignore_channels}\n\nИспользование:\n<code>.pointcase on|off</code>\n<code>.pointcaseignore on|off</code>",
        "status_on": "✅ Включен",
        "status_off": "❌ Выключен",
        "ignore_on": "✅ Каналы игнорируются",
        "ignore_off": "❌ Каналы не игнорируются",
    }

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        if self.db.get("PointSentenceCase", "enabled") is None:
            self.db.set("PointSentenceCase", "enabled", True)
        if self.db.get("PointSentenceCase", "ignore_channels") is None:
            self.db.set("PointSentenceCase", "ignore_channels", True)

    @loader.command(ru_doc="{on/off} — включает/выключает модуль")
    async def pointcase(self, message):
        """{on/off} - enables/disables the module"""
        args = utils.get_args_raw(message).lower()

        if args == "on":
            self.db.set("PointSentenceCase", "enabled", True)
            await utils.answer(message, self.strings("enabled"))
        elif args == "off":
            self.db.set("PointSentenceCase", "enabled", False)
            await utils.answer(message, self.strings("disabled"))
        else:
            status = self.db.get("PointSentenceCase", "enabled", True)
            ignore = self.db.get("PointSentenceCase", "ignore_channels", True)
            await utils.answer(
                message,
                self.strings("status").format(
                    status=self.strings("status_on") if status else self.strings("status_off"),
                    ignore_channels=self.strings("ignore_on") if ignore else self.strings("ignore_off"),
                ),
            )

    @loader.command(ru_doc="{on/off} — включает/выключает игнорирование каналов")
    async def pointcaseignore(self, message):
        """{on/off} - enables/disables ignoring channels"""
        args = utils.get_args_raw(message).lower()

        if args == "on":
            self.db.set("PointSentenceCase", "ignore_channels", True)
            await utils.answer(message, self.strings("ignore_on"))
        elif args == "off":
            self.db.set("PointSentenceCase", "ignore_channels", False)
            await utils.answer(message, self.strings("ignore_off"))
        else:
            ignore = self.db.get("PointSentenceCase", "ignore_channels", True)
            await utils.answer(
                message,
                self.strings("ignore_on") if ignore else self.strings("ignore_off"),
            )

    async def watcher(self, message):
        if not self.db.get("PointSentenceCase", "enabled", True):
            return

        if not message.out or not message.text:
            return

        if self.db.get("PointSentenceCase", "ignore_channels", True):
            try:
                peer = await message.get_chat()
                if getattr(peer, "is_channel", False) and not getattr(peer, "is_group", False):
                    return
            except Exception:
                pass

        text = message.text.strip()
        if not text:
            return

        prefixes = self.get_prefix()
        if isinstance(prefixes, str):
            prefixes = [prefixes]

        if any(text.startswith(prefix) for prefix in prefixes):
            return

        sentence_end_marks = {".", "!", "?", "…"}
        result = ""
        capitalize_next = True

        for char in text:
            if capitalize_next and char.isalpha():
                result += char.upper()
                capitalize_next = False
            else:
                result += char.lower()
            if char in sentence_end_marks:
                capitalize_next = True
            elif char in {",", ":", "-", "#", "/", '"'}:
                capitalize_next = False

        last_char = result[-1] if result else ""
        is_special = not last_char.isalnum() and not self.is_emoji(last_char)

        if (
            result
            and last_char not in sentence_end_marks
            and not self.is_emoji(last_char)
            and not is_special
        ):
            result += "."

        if result != text:
            await message.edit(result)

    def is_emoji(self, char: str) -> bool:
        return any([
            "\U0001F600" <= char <= "\U0001F64F",
            "\U0001F300" <= char <= "\U0001F5FF",
            "\U0001F680" <= char <= "\U0001F6FF",
            "\U0001F700" <= char <= "\U0001F77F",
            "\U0001F780" <= char <= "\U0001F7FF",
            "\U0001F800" <= char <= "\U0001F8FF",
            "\U0001F900" <= char <= "\U0001F9FF",
            "\U0001FA00" <= char <= "\U0001FA6F",
            "\U0001FA70" <= char <= "\U0001FAFF",
            "\U00002702" <= char <= "\U000027B0",
            "\U000024C2" <= char <= "\U0001F251",
        ])