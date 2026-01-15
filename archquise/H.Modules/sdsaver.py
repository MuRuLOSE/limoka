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
# Name: SDSaver
# Description: The module for automatically saving self-destructing mediat
# Author: @hikka_mods
# ---------------------------------------------------------------------------------
# meta developer: @hikka_mods
# scope: SDSaver
# scope: SDSaver 0.0.1
# ---------------------------------------------------------------------------------

import logging

import aiogram
import telethon

from .. import loader, utils


logger = logging.getLogger(__name__)


@loader.tds
class SDSaverMod(loader.Module):
    """The module for automatically saving self-destructing media"""

    strings = {
        "name": "SDSaver",
        "sdmode_on": "<emoji document_id=5769230088960741619>🔥</emoji> <b>Automatic saving self-destructing media is enabled</b>",
        "sdmode_off": "<emoji document_id=5769230088960741619>🔥</emoji> <b>Automatic saving self-destructing media is disabled</b>",
        "sd": '🔥 <b><a href="{link}">{name}</a> sent self-destructing media:</b>\n{caption}',
    }

    strings_ru = {
        "_cls_doc": "Модуль для автоматического сохранения самоуничтожающихся медиа",
        "sdmode_on": "<emoji document_id=5769230088960741619>🔥</emoji> <b>Автоматическое сохранение самоуничтожающихся медиа включено</b>",
        "sdmode_off": "<emoji document_id=5769230088960741619>🔥</emoji> <b>Автоматическое сохранение самоуничтожающихся медиа выключено</b>",
        "sd": '🔥 <b><a href="{link}">{name}</a> отправил(а) самоуничтожающееся медиа:</b>\n{caption}',
    }

    async def client_ready(self, client, db):
        self._client = client
        self._db = db

        channel, _ = await utils.asset_channel(
            self._client,
            "heroku-sd",
            "Self-destruction media will appear there",
            invite_bot=True,
            avatar="https://i.pinimg.com/originals/6c/1e/cf/6c1ecf3afca663a9ebc0b18788b337ee.jpg",
            _folder="heroku",
        )
        self._channel = int(f"-100{channel.id}")

    @loader.command(
        ru_doc="Включить/Выключить автоматическое сохранение самоуничтожающихся медиа",
        en_doc="Enable/Disable automatic saving self-destructing media",
    )
    async def sdmodecmd(self, message: telethon.types.Message):
        need_mode = not self.get("save_sd", True)
        self.set("save_sd", need_mode)
        await utils.answer(
            message, self.strings(f"sdmode_{'on' if need_mode else 'off'}")
        )

    @loader.watcher("in", only_messages=True)
    async def watcher(self, message: telethon.types.Message):
        if (
            (not self.get("save_sd", True))
            or (not message.media)
            or (not getattr(message.media, "ttl_seconds", None))
        ):
            return

        try:
            sender = await self.client.get_entity(message.sender_id, exp=0)
        except Exception:
            sender = await message.get_sender()

        media = await self.client.download_media(message.media, bytes)
        args = {
            "chat_id": self._channel,
            "caption": self.strings("sd").format(
                link=utils.get_entity_url(sender),
                name=utils.escape_html(telethon.utils.get_display_name(sender)),
                caption=message.text if message.text else "",
            ),
        }
        if message.photo:
            args["photo"] = aiogram.types.BufferedInputFile(media, "sd.png")
            method = self.inline.bot.send_photo
        if message.video or message.video_note:
            args["video"] = aiogram.types.BufferedInputFile(media, "sd.mp4")
            method = self.inline.bot.send_video
        if message.voice:
            args["voice"] = aiogram.types.BufferedInputFile(media, "sd.ogg")
            method = self.inline.bot.send_voice

        await method(**args)
