# Proprietary License Agreement

# Copyright (c) 2026-2029

# Permission is hereby granted to any person obtaining a copy of this software and associated documentation files (the "Software"), to use the Software for personal and non-commercial purposes, subject to the following conditions:

# 1. The Software may not be modified, altered, or otherwise changed in any way without the explicit written permission of the author.

# 2. Redistribution of the Software, in original or modified form, is strictly prohibited without the explicit written permission of the author.

# 3. The Software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement. In no event shall the author or copyright holder be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the Software or the use or other dealings in the Software.

# 4. Any use of the Software must include the above copyright notice and this permission notice in all copies or substantial portions of the Software.

# 5. By using the Software, you agree to be bound by the terms and conditions of this license.

# For any inquiries or requests for permissions, please contact archquise@gmail.com

# ---------------------------------------------------------------------------------
# Name: YTDL
# Description: Downloads and sends audio/video from YouTube
# Author: @hikka_mods
# ---------------------------------------------------------------------------------
# meta developer: @hikka_mods
# requires: yt_dlp ffmpeg
# ---------------------------------------------------------------------------------

import shutil
import platform
import aiohttp
import aiofiles
import zipfile
import os
import re

import logging

from pathlib import Path
from yt_dlp import YoutubeDL

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class YTDLMod(loader.Module):
    """Downloads and sends audio/video from YouTube"""

    strings = {
        "name": "YTDL",
        "_cls_doc": "Downloads and sends audio/video from YouTube",
        "invalid_args": "<emoji document_id=5854929766146118183>❌</emoji> There is no arguments or they are invalid",
        "downloading": "<emoji document_id=5215484787325676090>🕐</emoji> Downloading...",
        "done": "<emoji document_id=5854762571659218443>✅</emoji> Done!",
    }

    strings_ru = {
        "_cls_doc": "Скачивает и отправляет аудио/видео с Ютуба",
        "invalid_args": "<emoji document_id=5854929766146118183>❌</emoji> Нет аргументов или они неверны",
        "downloading": "<emoji document_id=5215484787325676090>🕐</emoji> Скачиваю...",
        "done": "<emoji document_id=5854762571659218443>✅</emoji> Готово!",
    }

    def _validate_url(self, url: str) -> bool:
        """Validate URL format"""
        if not url:
            return False

        url_pattern = re.compile(
            r"^(?:https?://)?(?:www\.|m\.)?(?:youtube\.com|youtu\.be|music\.youtube\.com)/(?:watch\?v=|playlist\?list=|channel/|@|live/|shorts/)?[\w-]+",
            re.IGNORECASE,
        )

        return url_pattern.match(url) is not None

    async def get_target(self):
        system = platform.system()
        machine = platform.machine().lower()

        if system == "Windows":
            return "Windows"

        if system == "Darwin":
            return (
                "aarch64-apple-darwin" if machine == "arm64" else "x86_64-apple-darwin"
            )

        if system == "Linux":
            return (
                "aarch64-unknown-linux-gnu"
                if machine in ("aarch64", "arm64")
                else "x86_64-unknown-linux-gnu"
            )

        return "x86_64-unknown-linux-gnu"

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "youtube_cookie",
                None,
                "Cookie вашего Ютуб-аккаунта (повышает стабильность и помогает скачивать видео с жесткими возрастными ограничениями) | Cookie of your YouTube-account (increases stability and helps downloading video with strict age rating restricrions)",
                validator=loader.validators.Hidden(),
            ),
        )

    async def client_ready(self, client, db):
        deno_path = Path("deno")
        deno_which = shutil.which("deno")

        # Trying to fix previous shitcode...
        if self.get("deno_source") == "file":
            self.set("deno_source", str(deno_path.resolve())) 
            
        if not deno_which and not deno_path.is_file():
            logger.warning("Deno is not installed, attempting installation...")
            target = await self.get_target()
            if target == "Windows":
                logger.critical(
                    "Windows platform is unsupported by this module. All future commands will fail. Please, unload the module."
                )
                return
            async with aiohttp.ClientSession() as session:
                download_link = f"https://github.com/denoland/deno/releases/latest/download/deno-{target}.zip"
                async with session.get(download_link) as resp:
                    if resp.status == 200:
                        async with aiofiles.open("deno.zip", mode="wb") as f:
                            async for chunk in resp.content.iter_chunked(8192):
                                await f.write(chunk)
                    else:
                        logger.critical(f"Failed to download Deno: HTTP {resp.status}")
                        self.set("deno_source", "install_failed")
                        return
            if Path("deno.zip").is_file():
                with zipfile.ZipFile("deno.zip", "r") as zip_ref:
                    zip_ref.extractall()
                os.remove("deno.zip")
                os.chmod(deno_path, 0o755)
                self.set("deno_source", str(deno_path.resolve()))
        elif deno_which:
            self.set("deno_source", deno_which)

    @loader.command(en_doc="Download video", ru_doc="Скачать видео")
    async def ytdlvcmd(self, message):
        args = utils.get_args(message)
        if not args or not self._validate_url(args[0]) or len(args) > 1:
            await utils.answer(message, self.strings["invalid_args"])
            return

        source = self.get("deno_source")
        if source == "install_failed" or not Path(source).is_file():
            logger.critical(
                "Deno wasn't installed in auto-mode. Please, install it manually or resolve the issue and reboot userbot."
            )
            return

        await utils.answer(message, self.strings["downloading"])

        filename_prefix = f"video_{message.id}"
        ydl_opts = {
            "quiet": True,
            "outtmpl": f"{filename_prefix}.%(ext)s",
            "js_runtimes": {"deno": {"path": source}},
            "postprocessors": [
                {
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": "mp4",
                }
            ],
            "postprocessor_args": {
                "video_convertor": [
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "23",
                    "-c:a",
                    "aac",
                ],
                "merger": ["-movflags", "faststart"],
            },
        }
        if self.get("youtube_cookie"):
            ydl_opts["cookiefile"] = self.get("youtube_cookie")
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(args[0], download=True)
            filename = ydl.prepare_filename(info).split(".")[0] + ".mp4"
            await utils.answer(message, self.strings['done'], file=filename, invert_media=True)
            os.remove(filename)

    @loader.command(en_doc="Download audio", ru_doc="Скачать аудио")
    async def ytdlacmd(self, message):
        args = utils.get_args(message)
        if not args or not self._validate_url(args[0]) or len(args) > 1:
            await utils.answer(message, self.strings["invalid_args"])
            return

        source = self.get("deno_source")
        if source == "install_failed" or not Path(source).is_file():
            logger.critical(
                "Deno wasn't installed in auto-mode. Please, install it manually or resolve the issue and reboot userbot."
            )
            return

        await utils.answer(message, self.strings["downloading"])

        filename_prefix = f"audio_{message.id}"
        ydl_opts = {
            "quiet": True,
            "outtmpl": f"{filename_prefix}.%(ext)s",
            "js_runtimes": {"deno": {"path": source}},
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "0",
                },
                {
                    "key": "FFmpegMetadata",
                    "add_metadata": True,
                },
                {
                    "key": "EmbedThumbnail",
                },
            ],
            "writethumbnail": True,
        }
        if self.get("youtube_cookie"):
            ydl_opts["cookiefile"] = self.get("youtube_cookie")
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(args[0], download=True)
            filename = ydl.prepare_filename(info).split(".")[0] + ".mp3"
            await utils.answer(message, self.strings['done'], file=filename)
            os.remove(filename)
