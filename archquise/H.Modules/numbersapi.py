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
# Name: NumbersAPI
# Description: Many interesting facts about numbers.
# Author: @hikka_mods
# ---------------------------------------------------------------------------------
# meta developer: @hikka_mods
# scope: NumbersAPI
# scope: NumbersAPI 0.0.1
# ---------------------------------------------------------------------------------

import logging
import asyncio
from typing import Optional

import aiohttp

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class NumbersAPI(loader.Module):
    """Many interesting facts about numbers."""

    strings = {
        "name": "NumbersAPI",
        "usage": "<emoji document_id=5854929766146118183>❌</emoji> Usage: .num <number or date> <type>\nExamples: .num 42 math, .num 01.15 date",
        "error_date_format": "<emoji document_id=5854929766146118183>❌</emoji> Invalid date format. Use: month.day (e.g., 01.15)",
        "error_number_format": "<emoji document_id=5854929766146118183>❌</emoji> Invalid number format.",
        "error_invalid_type": "<emoji document_id=5854929766146118183>❌</emoji> Invalid fact type. Available: math, trivia, date",
        "error_api": "<emoji document_id=5854929766146118183>❌</emoji> Failed to get fact. Please try again later.",
        "fetching": "<emoji document_id=5188311512791393083>🌎</emoji> Fetching fact...",
    }

    strings_ru = {
        "usage": "<emoji document_id=5854929766146118183>❌</emoji> Использование: .num <число или дата> <тип>\nПримеры: .num 42 math, .num 01.15 date",
        "error_date_format": "<emoji document_id=5854929766146118183>❌</emoji> Неверный формат даты. Используйте: месяц.день (например, 01.15)",
        "error_number_format": "<emoji document_id=5854929766146118183>❌</emoji> Неверный формат числа.",
        "error_invalid_type": "<emoji document_id=5854929766146118183>❌</emoji> Неверный тип факта. Доступны: math, trivia, date",
        "error_api": "<emoji document_id=5854929766146118183>❌</emoji> Не удалось получить факт. Попробуйте позже.",
        "fetching": "<emoji document_id=5188311512791393083>🌎</emoji> Получение факта...",
    }

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self.valid_fact_types = ["math", "trivia", "date"]

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15)
            )
        return self._session

    def _parse_date(self, date_str: str) -> Optional[tuple[int, int]]:
        """Parse date string in format MM.DD"""
        try:
            parts = date_str.split(".")
            if len(parts) != 2:
                return None

            month, day = map(int, parts)
            if not (1 <= month <= 12 and 1 <= day <= 31):
                return None

            return month, day
        except ValueError:
            return None

    def _parse_number(self, num_str: str) -> Optional[int]:
        """Parse number string"""
        try:
            return int(num_str)
        except ValueError:
            return None

    async def _fetch_fact(self, url: str) -> str:
        """Fetch fact from Numbers API"""
        session = await self._get_session()

        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.error(f"Numbers API error: {response.status}")
                    return self.strings("error_api")
        except asyncio.TimeoutError:
            logger.error("Numbers API timeout")
            return self.strings("error_api")
        except Exception as e:
            logger.error(f"Numbers API error: {e}")
            return self.strings("error_api")

    async def _get_number_fact(self, number: int, fact_type: str) -> str:
        """Get fact about number"""
        url = f"http://numbersapi.com/{number}/{fact_type}"
        return await self._fetch_fact(url)

    async def _get_date_fact(self, month: int, day: int) -> str:
        """Get fact about date"""
        date_str = f"{month:02d}/{day:02d}"
        url = f"http://numbersapi.com/{date_str}/date"
        return await self._fetch_fact(url)

    @loader.command(
        ru_doc="Дает интересный факт про число или дату\nНапример: .num 10 math или .num 01.01 date",
        en_doc="Gives an interesting fact about a number or date\nexample: .num 10 math or .num 01.01 date",
    )
    async def num(self, message):
        """Get interesting fact about number or date"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings("usage"))
            return

        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            await utils.answer(message, self.strings("usage"))
            return

        input_value = parts[0].strip()
        fact_type = parts[1].strip().lower()

        if fact_type not in self.valid_fact_types:
            await utils.answer(message, self.strings("error_invalid_type"))
            return

        await utils.answer(message, self.strings("fetching"))

        if "." in input_value:
            date_parts = self._parse_date(input_value)
            if date_parts is None:
                await utils.answer(message, self.strings("error_date_format"))
                return

            month, day = date_parts
            result = await self._get_date_fact(month, day)
        else:
            number = self._parse_number(input_value)
            if number is None:
                await utils.answer(message, self.strings("error_number_format"))
                return

            result = await self._get_number_fact(number, fact_type)

        await utils.answer(message, result)
