# █▀▀▄   █▀▄▀█ █▀█ █▀▄ █▀
# ▀▀▀█ ▄ █ ▀ █ █▄█ █▄▀ ▄█

# #### Copyright (c) 2026 Archquise #####

# 💬 Contact: https://t.me/archquise
# 🔒 Licensed under the GNU AGPLv3.
# 📄 LICENSE: https://raw.githubusercontent.com/archquise/Q.Mods/main/LICENSE
# ---------------------------------------------------------------------------------
# Name: face
# Description: Random face
# Author: @quise_m
# ---------------------------------------------------------------------------------
# meta developer: @quise_m
# meta banner: https://raw.githubusercontent.com/archquise/qmods_meta/main/face.png
# requires: aiohttp
# ---------------------------------------------------------------------------------

import logging
import random
import re
from http import HTTPStatus

import aiohttp

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class FaceMod(loader.Module):
    """Gives you a random kaomoji."""

    strings = {  # noqa: RUF012
        "name": "Face",
        "loading": (
            "<emoji document_id=5348399448017871250>🔍</emoji> I'm looking for you kaomoji"
        ),
        "random_face": (
            "<emoji document_id=5208878706717636743>🗿</emoji> Here is your random one kaomoji\n<code>{}</code>"
        ),
        "error": "An error has occurred!",
    }

    strings_ru = {  # noqa: RUF012
        "loading": (
            "<emoji document_id=5348399448017871250>🔍</emoji> Ищу вам kaomoji"
        ),
        "random_face": (
            "<emoji document_id=5208878706717636743>🗿</emoji> Вот ваш рандомный kaomoji\n<code>{}</code>"
        ),
        "error": "Произошла ошибка!",
        "_cls_doc": "Выдает случайное каомодзи (японские эмодзи)",
    }

    @loader.command(
        ru_doc="Случайное каомодзи",
        en_doc="Random kaomoji",
    )
    async def rfacecmd(self, message) -> None:  # noqa: D102, ANN001
        await utils.answer(message, self.strings["loading"])

        url = "https://files.archquise.ru/kaomoji.txt"

        async with aiohttp.ClientSession() as session, session.get(url) as response:
            if response.status == HTTPStatus.OK:
                data = await response.text()
                kaomoji_list = [
                    s.strip() for s in re.split(r"[\t\r\n]+", data) if s.strip()
                ]
                kaomoji = random.choice(kaomoji_list)  # noqa: S311
                await utils.answer(
                    message,
                    self.strings["random_face"].format(kaomoji),
                )
            else:
                await utils.answer(message, self.strings["error"])
