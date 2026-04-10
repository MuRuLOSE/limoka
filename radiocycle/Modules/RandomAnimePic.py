# =======================================
#   _  __         __  __           _
#  | |/ /___     |  \/  | ___   __| |___
#  | ' // _ \    | |\/| |/ _ \ / _` / __|
#  | . \  __/    | |  | | (_) | (_| \__ \
#  |_|\_\___|    |_|  |_|\___/ \__,_|___/
#           @ke_mods
# =======================================
#
#  LICENSE: CC BY-ND 4.0 (Attribution-NoDerivatives 4.0 International)
#  --------------------------------------
#  https://creativecommons.org/licenses/by-nd/4.0/legalcode
# =======================================

# meta developer: @ke_mods
# requires: pillow

import asyncio
import logging
import traceback
from logging import basicConfig
from io import BytesIO

import requests
from PIL import Image

from .. import loader, utils

basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@loader.tds
class RandomAnimePicMod(loader.Module):
    strings = {
        "name": "RandomAnimePic",
        "img": "<tg-emoji emoji-id=4916036072560919511>✅</tg-emoji> <b>Your anime pic</b>\n<tg-emoji emoji-id=5877465816030515018>🔗</tg-emoji> <b>URL:</b> {}",
        "loading": "<tg-emoji emoji-id=4911241630633165627>✨</tg-emoji> <b>Loading image...</b>",
        "categories_loading": "<tg-emoji emoji-id=4911241630633165627>✨</tg-emoji> <b>Loading categories...</b>",
        "categories": "<tg-emoji emoji-id=4916036072560919511>✅</tg-emoji> <b>Available categories</b>\n<blockquote expandable>{}</blockquote>",
        "no_categories": "<tg-emoji emoji-id=5116151848855667552>🚫</tg-emoji> <b>Categories not found</b>",
        "error": "<tg-emoji emoji-id=5116151848855667552>🚫</tg-emoji> <b>An unexpected error occurred...</b>",
    }

    strings_ru = {
        "img": "<tg-emoji emoji-id=4916036072560919511>✅</tg-emoji> <b>Ваша аниме-картинка</b>\n<tg-emoji emoji-id=5877465816030515018>🔗</tg-emoji> <b>Ссылка:</b> {}",
        "loading": "<tg-emoji emoji-id=4911241630633165627>✨</tg-emoji> <b>Загрузка изображения...</b>",
        "categories_loading": "<tg-emoji emoji-id=4911241630633165627>✨</tg-emoji> <b>Загрузка категорий...</b>",
        "categories": "<tg-emoji emoji-id=4916036072560919511>✅</tg-emoji> <b>Доступные категории</b>\n<blockquote expandable>{}</blockquote>",
        "no_categories": "<tg-emoji emoji-id=5116151848855667552>🚫</tg-emoji> <b>Категории не найдены</b>",
        "error": "<tg-emoji emoji-id=5116151848855667552>🚫</tg-emoji> <b>Произошла непредвиденная ошибка...</b>",
    }

    RANDOM_API_URL = "https://api.nekosapi.com/v4/images/random"
    IMAGES_API_URL = "https://api.nekosapi.com/v4/images"
    CATEGORIES_SCAN_LIMIT = 500

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "category",
                "",
                "Category",
                validator=loader.validators.String(),
            ),
        )

    @loader.command(ru_doc="- получить рандомную аниме-картинку 👀")
    async def rapiccmd(self, message):
        """- fetch random anime-pic 👀"""
        await utils.answer(message, self.strings("loading"))

        try:
            category = self.config["category"].strip()

            def fetch_image():
                params = {"limit": 1, "rating": ["safe"]}

                if category:
                    params["tags"] = [category]

                response = requests.get(self.RANDOM_API_URL, params=params, timeout=15)
                response.raise_for_status()

                data = response.json()
                if not isinstance(data, list) or not data:
                    raise ValueError("API returned empty response")

                url = data[0].get("url")
                if not url:
                    raise ValueError("API response does not contain image url")

                image_response = requests.get(url, timeout=20)
                image_response.raise_for_status()

                image_stream = BytesIO(image_response.content)
                image = Image.open(image_stream)
                image.load()

                output = BytesIO()
                if "A" in image.getbands() or image.mode == "P":
                    image.convert("RGBA").save(output, format="PNG")
                    output.name = "anime.png"
                else:
                    image.convert("RGB").save(output, format="JPEG", quality=95)
                    output.name = "anime.jpg"

                output.seek(0)
                return url, output

            url, file = await asyncio.to_thread(fetch_image)
            await utils.answer(
                message,
                self.strings("img").format(url),
                file=file
            )

        except Exception:
            logger.error(
                "Error fetching random anime pic: %s",
                traceback.format_exc(),
            )
            await utils.answer(message, self.strings("error"))

    @loader.command(ru_doc="- получить список категорий из API 👀")
    async def racategoriescmd(self, message):
        """- fetch categories from api 👀"""
        await utils.answer(message, self.strings("categories_loading"))

        try:
            def fetch_categories() -> list[str]:
                tags = set()
                offset = 0

                while offset < self.CATEGORIES_SCAN_LIMIT:
                    response = requests.get(
                        self.IMAGES_API_URL,
                        params={
                            "limit": 100,
                            "offset": offset,
                            "rating": ["safe"],
                        },
                        timeout=20,
                    )
                    response.raise_for_status()

                    data = response.json()
                    items = data.get("items") or data.get("results") or []
                    if not items:
                        break

                    for item in items:
                        tags.update(item.get("tags", []))

                    if len(items) < 100:
                        break

                    offset += 100

                return sorted(tags)

            categories = await asyncio.to_thread(fetch_categories)

            if not categories:
                await utils.answer(message, self.strings("no_categories"))
                return

            formatted_categories = "\n".join(
                f"<code>{category}</code>" for category in categories
            )
            await utils.answer(
                message,
                self.strings("categories").format(formatted_categories),
            )

        except Exception:
            logger.error(
                "Error fetching categories: %s",
                traceback.format_exc(),
            )
            await utils.answer(message, self.strings("error"))