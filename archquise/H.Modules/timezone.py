# Proprietary License Agreement

# Copyright (c) 2026-2029 Archquise

# Permission is hereby granted to any person obtaining a copy of this software and associated documentation files (the "Software"), to use the Software for personal and non-commercial purposes, subject to the following conditions:

# 1. The Software may not be modified, altered, or otherwise changed in any way without the explicit written permission of the author.

# 2. Redistribution of the Software, in original or modified form, is strictly prohibited without the explicit written permission of the author.

# 3. The Software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement. In no event shall the author or copyright holder be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the Software or the use or other dealings in the Software.

# 4. Any use of the Software must include the above copyright notice and this permission notice in all copies or substantial portions of the Software.

# 5. By using the Software, you agree to be bound by the terms and conditions of this license.

# For any inquiries or requests for permissions, please contact archquise@gmail.com

# ---------------------------------------------------------------------------------
# Name: TimeZone
# Description: Prints current time in selected timezone (UTC+n and tzdata formats supported)
# Author: @hikka_mods
# ---------------------------------------------------------------------------------
# meta developer: @hikka_mods
# requires: tzdata
# ---------------------------------------------------------------------------------

import logging
import tzdata

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class TimeZoneMod(loader.Module):
    """Prints current time in selected timezone (UTC+n and tzdata formats supported)"""

    strings = {
        "name": "TimeZone",
        "invalid_args": "<emoji document_id=5854929766146118183>❌</emoji> There is no arguments or they are invalid",
        "_cls_doc": "Prints current time in selected timezone (UTC+n and tzdata formats supported)",
        "time_utc": "<emoji document_id=5276412364458059956>🕓</emoji> Current time by UTC+{}: {}",
        "time_tzdata": "<emoji document_id=5276412364458059956>🕓</emoji> Current time in {}: {}",
    }

    strings_ru = {
        "_cls_doc": "Выводит текущее время в выбранном часовом поясе (поддерживаются форматы UTC+n и tzdata)",
        "invalid_args": "<emoji document_id=5854929766146118183>❌</emoji> Нет аргументов или они неверны",
        "tzdata_error": "<emoji document_id=5854929766146118183>❌</emoji> Произошла ошибка при получении времени по tzdata: {}\n\nУбедитесь, что часовой пояс указан верно",
        "time_utc": "<emoji document_id=5276412364458059956>🕓</emoji> Текущее время по UTC+{}: {}",
        "time_tzdata": "<emoji document_id=5276412364458059956>🕓</emoji> Текущее время в {}: {}",
    }

    @loader.command(
        ru_doc="Выводит время по UTC+n | Использование: .utc 4",
        en_doc="Prints UTC+n time | Usage: .utc 4",
    )
    async def utccmd(self, message):
        args = utils.get_args(message)
        if not args or not args[0].isdigit() or len(args) > 1:
            await utils.answer(message, self.strings["invalid_args"])
            return
        offset = timedelta(hours=int(args[0]))
        tz = timezone(offset)
        time = datetime.now(tz)
        await utils.answer(
            message, self.strings["time_utc"].format(args[0], time.strftime("%H:%M:%S"))
        )

    @loader.command(
        ru_doc="Выводит время по часовому поясу tzdata | Использование: .tzdata Europe/Moscow",
        en_doc="Prints time by tzdata timezone | Usage: .tzdata Europe/Moscow",
    )
    async def tzdatacmd(self, message):
        args = utils.get_args(message)
        if args[0].isdigit() or not args or len(args) > 1:
            await utils.answer(message, self.strings["invalid_args"])
            return
        try:
            time = datetime.now(ZoneInfo(args[0]))
        except Exception as e:
            await utils.answer(message, self.strings["tzdata_error"].format(e))
            logger.error(self.strings["tzdata_error"].format(e))
            return
        await utils.answer(
            message,
            self.strings["time_tzdata"].format(args[0], time.strftime("%H:%M:%S")),
        )
