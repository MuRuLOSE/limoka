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
# Name: Video2GIF
# Description: Converts video to GIF
# Author: @hikka_mods
# ---------------------------------------------------------------------------------
# meta developer: @hikka_mods
# scope: Video2GIF
# scope: Video2GIF 0.0.1
# ---------------------------------------------------------------------------------

import asyncio
import logging
import os
import shutil
import tempfile

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class Video2GIFMod(loader.Module):
    """Convert video to high quality GIF"""

    strings = {
        "name": "Video2GIF",
        "success": "✅ GIF created",
        "error": "❌ Conversion failed",
        "no_video": "❌ Reply to a video",
        "no_ffmpeg": "❌ FFmpeg not installed. Install: apt install ffmpeg",
        "processing": "🔄 Processing video...",
        "compressing": "📦 Optimizing GIF...",
    }

    strings_ru = {
        "success": "✅ GIF создан",
        "error": "❌ Ошибка конвертации",
        "no_video": "❌ Ответьте на видео",
        "no_ffmpeg": "❌ FFmpeg не установлен. Установите: apt install ffmpeg",
        "processing": "🔄 Обрабатываю видео...",
        "compressing": "📦 Оптимизирую GIF...",
    }

    def __init__(self):
        self._ffmpeg_check = None

    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        self._ffmpeg_check = shutil.which("ffmpeg") is not None

    @loader.command(
        ru_doc="[ответ] [fps] [ширина] - конвертировать видео в GIF",
        en_doc="[reply] [fps] [width] - convert video to GIF",
    )
    async def gifc(self, message):
        """Convert video to GIF"""
        if not self._ffmpeg_check:
            return await utils.answer(message, self.strings["no_ffmpeg"])

        reply = await message.get_reply_message()
        if not reply or not reply.video:
            return await utils.answer(message, self.strings["no_video"])

        args = utils.get_args_raw(message).split()
        fps = 15 if len(args) < 1 else min(int(args[0]), 30)
        width = 480 if len(args) < 2 else min(int(args[1]), 1024)

        msg = await utils.answer(message, self.strings["processing"])

        try:
            gif_path = await self._convert_to_gif(reply, fps, width)

            await self._client.send_file(
                message.chat_id,
                gif_path,
                caption=self.strings["success"],
                reply_to=reply.id,
            )

            os.remove(gif_path)
            await msg.delete()

        except Exception:
            await utils.answer(message, self.strings["error"])

    async def _convert_to_gif(self, reply, fps: int, width: int) -> str:
        """Convert video to optimized GIF"""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, "video.mp4")
            gif_path = os.path.join(tmpdir, "output.gif")

            await reply.download_media(video_path)

            cmd = [
                "ffmpeg",
                "-i",
                video_path,
                "-vf",
                f"fps={fps},scale={width}:-1:flags=lanczos",
                "-lavfi",
                "[0:v]split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
                "-y",
                gif_path,
            ]

            proc = await asyncio.create_subprocess_exec(*cmd)
            await proc.communicate()

            return gif_path
