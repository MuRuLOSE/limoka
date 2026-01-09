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
# Name: PastebinAPI
# Description: fills in the code on pastebin
# Author: @hikka_mods
# ---------------------------------------------------------------------------------
# meta developer: @hikka_mods
# scope: PastebinAPI
# scope: PastebinAPI 0.0.1
# requires: aiohttp
# ---------------------------------------------------------------------------------

import logging
import asyncio
from typing import Optional

import aiohttp

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class PastebinAPIMod(loader.Module):
    """PastebinAPI"""

    strings = {
        "name": "PastebinAPI",
        "no_text": "<emoji document_id=5462882007451185227>🚫</emoji> No text provided. Use command with text or reply to a message.",
        "no_key": "<emoji document_id=5843952899184398024>🚫</emoji> Pastebin API key not configured. Get one at https://pastebin.com/doc_api#1",
        "uploading": "<emoji document_id=5188311512791393083>🌎</emoji> Uploading to Pastebin...",
        "done": "<emoji document_id=5854762571659218443>✅</emoji> Successfully uploaded!\n<emoji document_id=5985571061993837069>➡️</emoji> <code>{url}</code>",
        "error_api": "<emoji document_id=5854929766146118183>❌</emoji> Pastebin API error: {error}",
        "error_network": "<emoji document_id=5854929766146118183>❌</emoji> Network error: {error}",
        "error_general": "<emoji document_id=5854929766146118183>❌</emoji> An error occurred: {error}",
    }

    strings_ru = {
        "no_text": "<emoji document_id=5462882007451185227>🚫</emoji> Текст не предоставлен. Используйте команду с текстом или ответьте на сообщение.",
        "no_key": "<emoji document_id=5843952899184398024>🚫</emoji> API ключ Pastebin не настроен. Получите его на https://pastebin.com/doc_api#1",
        "uploading": "<emoji document_id=5188311512791393083>🌎</emoji> Загрузка в Pastebin...",
        "done": "<emoji document_id=5854762571659218443>✅</emoji> Успешно загружено!\n<emoji document_id=5985571061993837069>➡️</emoji> <code>{url}</code>",
        "error_api": "<emoji document_id=5854929766146118183>❌</emoji> Ошибка API Pastebin: {error}",
        "error_network": "<emoji document_id=5854929766146118183>❌</emoji> Ошибка сети: {error}",
        "error_general": "<emoji document_id=5854929766146118183>❌</emoji> Произошла ошибка: {error}",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "pastebin",
                None,
                lambda: "Get API key at https://pastebin.com/doc_api#1",
                validator=loader.validators.Hidden(),
            ),
            loader.ConfigValue(
                "expiration",
                "N",
                lambda: "Paste expiration: N=Never, 10M=10min, 1H=1hour, 1D=1day, 1W=1week",
                validator=loader.validators.String(["N", "10M", "1H", "1D", "1W"]),
            ),
            loader.ConfigValue(
                "privacy",
                "0",
                lambda: "Paste privacy: 0=Public, 1=Unlisted, 2=Private",
                validator=loader.validators.String(["0", "1", "2"]),
            ),
        )
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session

    async def _get_text_from_message(self, message) -> Optional[str]:
        """Extract text from command args or replied message"""

        args = utils.get_args_raw(message)
        if args:
            return args

        if message.is_reply:
            replied = await message.get_reply_message()
            if replied and replied.text:
                return replied.text

        if message.text:
            command_parts = message.text.split(maxsplit=1)
            if len(command_parts) > 1:
                return command_parts[1]

        return None

    def _validate_pastebin_response(self, response_text: str) -> bool:
        """Validate Pastebin API response"""

        return response_text.startswith("https://pastebin.com/")

    async def _handle_error(self, message, error: Exception):
        """Handle different types of errors"""
        if isinstance(error, aiohttp.ClientError):
            await utils.answer(
                message, self.strings("error_network").format(error=str(error))
            )
        elif isinstance(error, asyncio.TimeoutError):
            await utils.answer(
                message, self.strings("error_network").format(error="Request timeout")
            )
        else:
            await utils.answer(
                message, self.strings("error_general").format(error=str(error))
            )

    async def _upload_to_pastebin(self, text: str) -> str:
        """Upload text to Pastebin and return URL"""
        session = await self._get_session()

        data = {
            "api_dev_key": self.config["pastebin"],
            "api_paste_code": text,
            "api_option": "paste",
            "api_paste_expire_date": self.config["expiration"],
            "api_paste_private": self.config["privacy"],
        }

        async with session.post(
            "https://pastebin.com/api/api_post.php",
            data=data,
            headers={"User-Agent": "Hikka-Mod/1.0"},
        ) as response:
            response_text = await response.text()

            if not self._validate_pastebin_response(response_text):
                raise Exception(f"Pastebin API error: {response_text}")

            return response_text

    @loader.command(
        ru_doc="Загрузить текст в Pastebin",
        en_doc="Upload text to Pastebin",
    )
    async def past(self, message):
        """Upload text to Pastebin with configurable options"""
        if self.config["pastebin"] is None:
            await utils.answer(message, self.strings("no_key"))
            return

        text = await self._get_text_from_message(message)
        if not text:
            await utils.answer(message, self.strings("no_text"))
            return

        await utils.answer(message, self.strings("uploading"))

        try:
            paste_url = await self._upload_to_pastebin(text)
            await utils.answer(message, self.strings("done").format(url=paste_url))
        except Exception as e:
            if "Pastebin API error" in str(e):
                error_msg = str(e).replace("Pastebin API error: ", "")
                await utils.answer(
                    message, self.strings("error_api").format(error=error_msg)
                )
            else:
                await self._handle_error(message, e)
