# Proprietary License Agreement

# Copyright (c) 2024-29 Archquise

# Permission is hereby granted to any person obtaining a copy of this software and associated documentation files (the "Software"), to use the Software for personal and non-commercial purposes, subject to the following conditions:

# 1. The Software may not be modified, altered, or otherwise changed in any way without the explicit written permission of the author.

# 2. Redistribution of the Software, in original or modified form, is strictly prohibited without the explicit written permission of the author.

# 3. The Software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement. In no event shall the author or copyright holder be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the Software or the use or other dealings in the Software.

# 4. Any use of the Software must include the above copyright notice and this permission notice in all copies or substantial portions of the Software.

# 5. By using the Software, you agree to be bound by the terms and conditions of this license.

# For any inquiries or requests for permissions, please contact archquise@gmail.com

# ---------------------------------------------------------------------------------
# Name: Aniliberty
# Description: Searches and gives random anime on the Aniliberty database.
# Author: @hikka_mods
# ---------------------------------------------------------------------------------
# meta developer: @hikka_mods
# requires: dacite
# scope: AniLiberty
# scope: AniLiberty 0.0.1
# ---------------------------------------------------------------------------------

import logging

from aiogram.types import CallbackQuery, InlineQueryResultPhoto
from dataclasses import dataclass
from json import JSONDecodeError
from dacite import from_dict
from typing import Optional


import aiohttp

from .. import loader
from ..inline.types import InlineQuery

logger = logging.getLogger(__name__)

BASE_API_URL = "https://aniliberty.top/api/v1" 

# Датаклассы для парсинга и хранения json
@dataclass
class Genre:
    name: str
@dataclass 
class Name:
    main: str
@dataclass
class Type:
    description: str
@dataclass
class Poster:
    preview: str
    thumbnail: str
@dataclass
class ReleaseInfo:
    id: int
    genres: Optional[list[Genre]] 
    name: Name
    is_ongoing: bool
    type: Type
    description: str
    added_in_users_favorites: int
    alias: str
    poster: Poster

@loader.tds
class AniLibertyMod(loader.Module):
    """Ищет и возвращает случайное аниме из базы Aniliberty"""

    strings = {
        "name": "AniLiberty",
        "announce": "<b>The announcement</b>:",
        "ongoing": "<b>Ongoing</b>:",
        "type": "<b>Type</b>:",
        "genres": "<b>Genres</b>:",
        "favorite": "<b>Favourites &lt;3</b>:",  # &lt; == <
    }

    strings_ru = {
        "announce": "<b>Анонс</b>:",
        "ongoing": "<b>Онгоинг</b>:",
        "type": "<b>Тип</b>:",
        "genres": "<b>Жанры</b>:",
        "favorite": "<b>Избранное &lt;3</b>:",  # &lt; == <
    }

    async def search_title(self, query):
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{BASE_API_URL}/app/search/releases?query={query}&include=id%2Cname.main%2Cis_ongoing%2Ctype.description%2Cdescription%2Cadded_in_users_favorites%2Calias%2Cposter.preview%2Cposter.thumbnail') as resp:
                json_answer = await resp.json()
                results = []
                for i in json_answer:
                    obj = from_dict(data_class=ReleaseInfo, data=i) 
                    results.append(obj) 
                return results   
   
    async def get_title(self, release_id):
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{BASE_API_URL}/anime/releases/{release_id}?include=id%2Cgenres.name%2Cname.main%2Cis_ongoing%2Ctype.description%2Cdescription%2Cadded_in_users_favorites%2Calias%2Cposter.preview%2Cposter.thumbnail') as resp:
                    try:
                        json_answer = await resp.json()
                        data = from_dict(data_class=ReleaseInfo, data=json_answer)
                        return data
                    except JSONDecodeError:
                        logger.error("Ошибка парсинга JSON!")

    async def get_random_title(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{BASE_API_URL}/anime/releases/random?limit=1&include=id') as resp:
                randid = await resp.json()
                """ 
                Приходится запрашивать по второму кругу, т.к. API в рандомных релизах не отдает жанры, даже если попросить через include
                """
                data = await self.get_title(randid[0]['id'])
                return data
            
    @loader.command(
        ru_doc="Возвращает случайный релиз из базы",
        en_doc="Returns a random release from the database",
    )
    async def arandom(self, message) -> None:
        anime_release = await self.get_random_title()
        genres_str = ""
        for genre in anime_release.genres[:-1]:
            genres_str += f'{genre.name}, '
        genres_str += anime_release.genres[-1].name

        
        text = f"{anime_release.name.main} \n"
        text += f"{self.strings['ongoing']} {'Да' if anime_release.is_ongoing else 'Нет'}\n\n"
        text += f"{self.strings['type']} {anime_release.type.description}\n"
        text += f"{self.strings['genres']} {genres_str}\n\n"
        
        text += f"<code>{anime_release.description}</code>\n\n"
        text += f"{self.strings['favorite']} {str(anime_release.added_in_users_favorites)}"

        kb = [
            [
                {
                    "text": "Ссылка",
                    "url": f"https://aniliberty.top/anime/releases/release/{anime_release.alias}/episodes",
                }
            ]
        ]

        kb.append([{"text": "🔃 Обновить", "callback": self.inline__update}])
        kb.append([{"text": "🚫 Закрыть", "callback": self.inline__close}])

        await self.inline.form(
            text=text,
            photo=f"https://aniliberty.top{anime_release.poster.preview}",
            message=message,
            reply_markup=kb,
            silent=True,
        )

    @loader.inline_handler(
        ru_doc="Возвращает список найденных по названию тайтлов",
        en_doc="Returns a list of titles found by name",
    )
    async def asearch_inline_handler(self, query: InlineQuery) -> None:
        text = query.args

        if not text:
            return

        anime_releases = await self.search_title(text)

        inline_query = []
        for anime_release in anime_releases:
            """ 
            Приходится запрашивать по второму кругу, т.к. API в поиске не отдает жанры, даже если попросить через include
            """
            release_genres = await self.get_title(anime_release.id) 
            genres_str = ""
            for genre in release_genres.genres[:-1]:
                genres_str += f'{genre.name}, '
            genres_str += release_genres.genres[-1].name
            release_text = (
                f"{anime_release.name.main}\n"
                f"{self.strings['ongoing']} {"Да" if anime_release.is_ongoing else "Нет"}\n\n"
                f"{self.strings['type']} {anime_release.type.description}\n"
                f"{self.strings['genres']} {genres_str}\n\n"
                f"<code>{anime_release.description}</code>\n\n"
                f"{self.strings['favorite']} {anime_release.added_in_users_favorites}"
            )

            inline_query.append(
                InlineQueryResultPhoto(
                    id=str(anime_release.id),
                    title=anime_release.name.main,
                    description=anime_release.type.description,
                    caption=release_text,
                    thumbnail_url=f"https://aniliberty.top{anime_release.poster.thumbnail}",
                    photo_url=f"https://aniliberty.top{anime_release.poster.preview}",
                    parse_mode="html",
                )
            )
        method = query.answer(inline_query, cache_time=0)
        await method.as_(self.inline.bot)

    async def inline__close(self, call: CallbackQuery) -> None:
        await call.delete()

    async def inline__update(self, call: CallbackQuery) -> None:
        anime_release = await self.get_random_title()
        genres_str = ""
        for genre in anime_release.genres[:-1]:
            genres_str += f'{genre.name}, '
        genres_str += anime_release.genres[-1].name

        text = f"{anime_release.name.main} \n"
        text += f"{self.strings['ongoing']} {"Да" if anime_release.is_ongoing else "Нет"}\n\n"
        text += f"{self.strings['type']} {anime_release.type.description}\n"
        text += f"{self.strings['genres']} {genres_str}\n\n"

        text += f"<code>{anime_release.description}</code>\n\n"
        text += f"{self.strings['favorite']} {str(anime_release.added_in_users_favorites)}"

        kb = [
            [
                {
                    "text": "Ссылка",
                    "url": f"https://aniliberty.top/anime/releases/release/{anime_release.alias}/episodes",
                }
            ]
        ]
        kb.append([{"text": "🔃 Обновить", "callback": self.inline__update}])
        kb.append([{"text": "🚫 Закрыть", "callback": self.inline__close}])

        await call.edit(
            text=text,
            photo=f"https://aniliberty.top{anime_release.poster.preview}",
            reply_markup=kb,
        )
