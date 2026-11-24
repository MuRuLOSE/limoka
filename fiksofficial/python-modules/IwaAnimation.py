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

import asyncio
import os
import toml

from .. import loader, utils
from herokutl.tl.types import Message


@loader.tds
class IwaAnimation(loader.Module):
    """Frame-by-frame text animations loaded from .anim TOML files"""

    strings = {
        "name": "IwaAnimation",
        "err_no_reply":    "<b>{e} Reply to a .anim file.</b>",
        "err_not_anim":    "<b>{e} File must have .anim extension.</b>",
        "err_bad_format":  "<b>{e} Invalid file format (missing name or cmd).</b>",
        "err_no_frames":   "<b>{e} No frames found in the file.</b>",
        "err_not_found":   "<b>{e} Animation not found.</b>",
        "err_no_cmd":      "<b>{e} Specify a command name.</b>",
        "err_generic":     "<b>{e} Error:</b>\n\n{exc}",
        "ok_loaded":       "<b>{s} Loaded: {name}\nCommand: <code>.anim {cmd}</code></b>",
        "ok_deleted":      "<b>{s} Deleted.</b>",
        "list_header":     "<blockquote><b>Animations:</b></blockquote>\n\n<blockquote expandable><b>",
        "list_row":        "• <code>{cmd}</code> — {name} ({n} frames)\n",
        "list_footer":     "</b></blockquote>",
        "list_empty":      "<b>{e} No animations.</b>",
    }

    strings_ru = {
        "name": "IwaAnimation",
        "err_no_reply":    "<b>{e} Ответьте на .anim файл.</b>",
        "err_not_anim":    "<b>{e} Файл должен быть формата .anim</b>",
        "err_bad_format":  "<b>{e} Неверный формат файла (нет name или cmd).</b>",
        "err_no_frames":   "<b>{e} В файле нет кадров.</b>",
        "err_not_found":   "<b>{e} Анимация не найдена.</b>",
        "err_no_cmd":      "<b>{e} Укажи команду.</b>",
        "err_generic":     "<b>{e} Ошибка:</b>\n\n{exc}",
        "ok_loaded":       "<b>{s} Загружено: {name}\nКоманда: <code>.anim {cmd}</code></b>",
        "ok_deleted":      "<b>{s} Удалено.</b>",
        "list_header":     "<blockquote><b>Анимации:</b></blockquote>\n\n<blockquote expandable><b>",
        "list_row":        "• <code>{cmd}</code> — {name} ({n} кадров)\n",
        "list_footer":     "</b></blockquote>",
        "list_empty":      "<b>{e} Нет анимаций.</b>",
    }

    _E = "<emoji document_id=5774077015388852135>❌</emoji>"
    _S = "<emoji document_id=5774022692642492953>✅</emoji>"

    async def client_ready(self):
        if not self.db.get("IwaAnimations", "anims", False):
            self.db.set("IwaAnimations", "anims", {})

    @loader.command(ru_doc="- Загрузить анимацию из полученного .anim файла")
    async def lanimcmd(self, message: Message):
        """- Load animation from a replied .anim file"""
        reply = await message.get_reply_message()
        if not reply or not reply.document:
            return await utils.answer(
                message, self.strings["err_no_reply"].format(e=self._E)
            )

        filename = reply.file.name or ""
        if not filename.endswith(".anim"):
            return await utils.answer(
                message, self.strings["err_not_anim"].format(e=self._E)
            )

        tmp = "anim_load.anim"
        await reply.download_media(tmp)
        try:
            data = toml.load(tmp)
            name  = data.get("name")
            cmd   = data.get("cmd")
            delay = float(data.get("time", 0.5))

            if not name or not cmd:
                return await utils.answer(
                    message, self.strings["err_bad_format"].format(e=self._E)
                )

            frames = []
            for key in sorted(
                (k for k in data if str(k).isdigit()), key=lambda x: int(x)
            ):
                frame = data[key]
                frames.append("\n".join(frame) if isinstance(frame, list) else str(frame))

            if not frames:
                return await utils.answer(
                    message, self.strings["err_no_frames"].format(e=self._E)
                )

            anims = self.db.get("IwaAnimations", "anims", {})
            anims[cmd] = {"name": name, "frames": frames, "delay": delay}
            self.db.set("IwaAnimations", "anims", anims)

            await utils.answer(
                message,
                self.strings["ok_loaded"].format(s=self._S, name=name, cmd=cmd),
            )
        except Exception as exc:
            await utils.answer(
                message, self.strings["err_generic"].format(e=self._E, exc=exc)
            )
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    @loader.command(ru_doc="<cmd> - Воспроизвести загруженную анимацию")
    async def animcmd(self, message: Message):
        """<cmd> - Play a loaded animation"""
        cmd = utils.get_args_raw(message)
        if not cmd:
            return await utils.answer(
                message, self.strings["err_no_cmd"].format(e=self._E)
            )

        anims = self.db.get("IwaAnimations", "anims", {})
        if cmd not in anims:
            return await utils.answer(
                message, self.strings["err_not_found"].format(e=self._E)
            )

        anim = anims[cmd]
        msg  = await utils.answer(message, anim["frames"][0])
        try:
            for frame in anim["frames"][1:]:
                await asyncio.sleep(anim["delay"])
                await msg.edit(frame)
        except Exception:
            pass

    @loader.command(ru_doc="- Отобразить список всех загруженных анимаций")
    async def animscmd(self, message: Message):
        """- List all loaded animations"""
        anims = self.db.get("IwaAnimations", "anims", {})
        if not anims:
            return await utils.answer(
                message, self.strings["list_empty"].format(e=self._E)
            )

        text = self.strings["list_header"]
        for cmd, data in anims.items():
            text += self.strings["list_row"].format(
                cmd=cmd, name=data["name"], n=len(data["frames"])
            )
        text += self.strings["list_footer"]
        await utils.answer(message, text)

    @loader.command(ru_doc="<cmd> - Удалить анимацию")
    async def delanimcmd(self, message: Message):
        """<cmd> - Delete an animation"""
        cmd   = utils.get_args_raw(message)
        anims = self.db.get("IwaAnimations", "anims", {})

        if cmd not in anims:
            return await utils.answer(
                message, self.strings["err_not_found"].format(e=self._E)
            )

        anims.pop(cmd)
        self.db.set("IwaAnimations", "anims", anims)
        await utils.answer(message, self.strings["ok_deleted"].format(s=self._S))

    @loader.command(ru_doc="<cmd> - Экспорт анимации в файл .anim")
    async def dumpanimcmd(self, message: Message):
        """<cmd> - Export an animation to a .anim file"""
        cmd   = utils.get_args_raw(message)
        anims = self.db.get("IwaAnimations", "anims", {})

        if cmd not in anims:
            return await utils.answer(
                message, self.strings["err_not_found"].format(e=self._E)
            )

        anim = anims[cmd]
        data = {"name": anim["name"], "cmd": cmd, "time": str(anim["delay"])}
        for i, frame in enumerate(anim["frames"], start=1):
            data[str(i)] = frame.split("\n")

        file = f"{cmd}.anim"
        try:
            with open(file, "w", encoding="utf-8") as f:
                toml.dump(data, f)
            await message.delete()
            await self._client.send_file(message.to_id, file)
        finally:
            if os.path.exists(file):
                os.remove(file)