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
# Name: AccountData
# Description: Find out the approximate date of registration of the telegram account
# Author: @hikka_mods
# ---------------------------------------------------------------------------------
# meta developer: @hikka_mods
# scope: Api AccountData
# scope: Api AccountData 0.0.1
# ---------------------------------------------------------------------------------

import asyncio
import logging
from datetime import datetime
from typing import Optional

import aiohttp

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class AccountData(loader.Module):
    """Find out the approximate date of registration of the telegram account"""

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_token",
                "7518491974:1ea2284eec9dc40a9838cfbcb48a2b36",
                "API token for datereg.pro",
                validator=loader.validators.Hidden(),
            )
        )
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15)
            )
        return self._session

    async def on_unload(self):
        if self._session and not self._session.closed:
            await self._session.close()

    strings = {
        "name": "AccountData",
        "_cls_doc": "Find out the approximate date of registration of the telegram account",
        "date_text": "<emoji document_id=5983150113483134607>⏰️</emoji> Date of registration of this account: {data} (Accuracy: {accuracy}%)",
        "date_text_ps": "<emoji document_id=6028435952299413210>ℹ</emoji> <i>Tip: To increase accuracy, the person whose registration date is being checked can write any message to</i> @mewpl2.\n\nDon't worry, this account is not run by a person, but by a userbot just like yours, which will check the registration date using Telegram's built-in tool.",
        "no_reply": "<emoji document_id=6030512294109122096>💬</emoji> You did not reply to the user's message",
    }

    strings_ru = {
        "date_text": "<emoji document_id=5983150113483134607>⏰️</emoji> Дата регистрации этого аккаунта: {data} (Точность: {accuracy}%)",
        "_cls_doc": "Узнайте примерную дату регистрации Telegram-аккаунта",
        "date_text_ps": "<emoji document_id=6028435952299413210>ℹ</emoji> <i>Совет: Для повышения точности, человек, дата регистрации которого проверяется, может написать любое сообщение</i> @mewpl2.\n\nНе бойтесь, на этом аккаунте сидит не человек, а такой же юзербот, как и у вас, который проверит дату регистрации при помощи встроенного инструмента Telegram.",
        "no_reply": "<emoji document_id=6030512294109122096>💬</emoji> Вы не ответили на сообщение пользователя",
    }

    async def get_creation_date(self, user_id: int) -> dict:
        api_token = self.config["api_token"]
        if not api_token:
            return {"error": "API token not configured"}

        url = "https://api.datereg.pro/api/v1/users/getCreationDateFast"
        params = {"token": api_token, "user_id": user_id}

        session = await self._get_session()
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    json_response = await response.json()
                    if json_response["success"]:
                        return {
                            "creation_date": json_response["creation_date"],
                            "accuracy_percent": json_response["accuracy_percent"],
                        }
                    else:
                        return {"error": json_response["error"]["message"]}
                else:
                    return {"error": f"HTTP {response.status}"}
        except asyncio.TimeoutError:
            return {"error": "Request timed out"}
        except Exception as e:
            return {"error": str(e)}

    @loader.command(
        ru_doc="Узнать примерную дату регистрации Telergam-аккаунта",
        en_doc="Find out the approximate date of registration of the telegram account",
    )
    async def accdata(self, message):
        if reply := await message.get_reply_message():
            result = await self.get_creation_date(user_id=reply.sender.id)

            if "error" in result or not result.get("creation_date"):
                error_msg = result.get("error", "Unknown error occurred")
                await utils.answer(message, f"Ошибка: {error_msg}")
                return

            try:
                month, year = map(int, result["creation_date"].split("."))
                date_object = datetime(year, month, 1)
                formatted = date_object.strftime("%B %Y")

                await utils.answer(
                    message,
                    f"{self.strings('date_text').format(data=formatted, accuracy=result['accuracy_percent'])}\n\n{self.strings('date_text_ps')}",
                )
            except (ValueError, KeyError) as e:
                await utils.answer(message, f"Ошибка обработки данных: {str(e)}")
        else:
            await utils.answer(message, self.strings("no_reply"))
