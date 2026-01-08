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
# Name: Search
# Description: Search for your question on the Internet
# Author: @hikka_mods
# ---------------------------------------------------------------------------------
# meta developer: @hikka_mods
# scope: Api Search
# scope: Api Search 0.0.1
# ---------------------------------------------------------------------------------

import logging
import urllib.parse

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class Search(loader.Module):
    """Поисковик"""

    strings = {
        "name": "Search",
        "search": "<emoji document_id=5188311512791393083>🌎</emoji><b> I searched for information for you</b>",
        "isearch": "🔎<b> I searched for information for you</b> ",
        "link": "🗂️ Link to your request",
        "close": "❌ Close",
        "no_query": "<emoji document_id=5854929766146118183>❌</emoji> Please provide a search query.",
    }

    strings_ru = {
        "search": "<emoji document_id=5188311512791393083>🌎</emoji><b> Я поискал информацию за тебя</b>",
        "isearch": "🔎<b> Я поискал информацию за тебя</b> ",
        "link": "🗂️ Ссылка на ваш запрос",
        "close": "❌ Закрыть",
        "no_query": "<emoji document_id=5854929766146118183>❌</emoji> Пожалуйста, укажите поисковый запрос.",
    }

    def __init__(self):
        self.search_engines = {
            "google": "https://google.com/search?q=",
            "yandex": "https://yandex.ru/?q=",
            "duckduckgo": "https://duckduckgo.com/?q=",
            "bing": "https://bing.com/?q=",
            "you": "https://you.com/?q=",
        }

    def _create_search_url(self, engine: str, query: str) -> str:
        """Create search URL with proper encoding"""
        if not query.strip():
            return None

        base_url = self.search_engines.get(engine)
        if not base_url:
            return None

        encoded_query = urllib.parse.quote_plus(query.strip())
        return f"{base_url}{encoded_query}"

    def _create_inline_markup(self, search_url: str):
        """Create inline keyboard markup"""
        return [
            [
                {
                    "text": self.strings("link"),
                    "url": search_url,
                }
            ],
            [{"text": self.strings("close"), "action": "close"}],
        ]

    async def _search_command(self, message, engine: str, inline: bool = False):
        """Universal search command handler"""
        query = utils.get_args_raw(message)

        if not query.strip():
            await utils.answer(message, self.strings("no_query"))
            return

        search_url = self._create_search_url(engine, query)
        if not search_url:
            await utils.answer(message, self.strings("no_query"))
            return

        if inline:
            await self.inline.form(
                text=self.strings("isearch"),
                message=message,
                reply_markup=self._create_inline_markup(search_url),
                silent=True,
            )
        else:
            await utils.answer(
                message, self.strings("search") + f": <a href={search_url}>link</a>"
            )

    @loader.command(
        ru_doc="Поискать в Google",
        en_doc="Search on Google",
    )
    async def google(self, message):
        await self._search_command(message, "google")

    @loader.command(
        ru_doc="Поискать в Yandex",
        en_doc="Search on Yandex",
    )
    async def yandex(self, message):
        await self._search_command(message, "yandex")

    @loader.command(
        ru_doc="Поискать в Duckduckgo",
        en_doc="Search on Duckduckgo",
    )
    async def duckduckgo(self, message):
        await self._search_command(message, "duckduckgo")

    @loader.command(
        ru_doc="Поискать в Bing",
        en_doc="Search on Bing",
    )
    async def bing(self, message):
        await self._search_command(message, "bing")

    @loader.command(
        ru_doc="Поискать в You",
        en_doc="Search on You",
    )
    async def you(self, message):
        await self._search_command(message, "you")

    @loader.command(
        ru_doc="Поискать в Google инлайн",
        en_doc="Search on Google inline",
    )
    async def igoogle(self, message):
        await self._search_command(message, "google", inline=True)

    @loader.command(
        ru_doc="Поискать в Yandex инлайн",
        en_doc="Search on Yandex inline",
    )
    async def iyandex(self, message):
        await self._search_command(message, "yandex", inline=True)

    @loader.command(
        ru_doc="Поискать в Duckduckgo инлайн",
        en_doc="Search on Duckduckgo inline",
    )
    async def iduckduckgo(self, message):
        await self._search_command(message, "duckduckgo", inline=True)

    @loader.command(
        ru_doc="Поискать в Bing инлайн",
        en_doc="Search on Bing inline",
    )
    async def ibing(self, message):
        await self._search_command(message, "bing", inline=True)

    @loader.command(
        ru_doc="Поискать в You инлайн",
        en_doc="Search on You inline",
    )
    async def iyou(self, message):
        await self._search_command(message, "you", inline=True)

    async def close(self, call):
        """Callback button"""
        await call.delete()
