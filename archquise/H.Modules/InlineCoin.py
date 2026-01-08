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
# Name: InlineCoin
# Description: Mini game heads or tails.
# Author: @hikka_mods
# ---------------------------------------------------------------------------------
# meta developer: @hikka_mods
# scope: InlineCoin
# scope: InlineCoin 0.0.1
# ---------------------------------------------------------------------------------

import logging
import random
from typing import Dict

from .. import loader
from ..inline.types import InlineQuery

logger = logging.getLogger(__name__)


@loader.tds
class CoinFlipMod(loader.Module):
    """Mini coin flip game"""

    strings = {
        "name": "InlineCoin",
        "titles": "🪙 Heads or Tails?",
        "description": "🎲 Let's find out!",
        "heads": "🦅 An eagle fell out!",
        "tails": "🪙 Tails fell out!",
        "edge": "🙀 Miraculously, the coin remained on its edge!",
        "no_args": "<emoji document_id=5854929766146118183>❌</emoji> Please provide a command to flip.",
        "error_general": "<emoji document_id=5854929766146118183>❌</emoji> An error occurred: {error}",
    }

    strings_ru = {
        "titles": "🪙 Орёл или решка?",
        "description": "🎲 Давай узнаем!",
        "heads": "🦅 Выпал орёл!",
        "tails": "🪙 Выпала решка!",
        "edge": "🙀 Чудо, монетка осталась на ребре!",
        "no_args": "<emoji document_id=5854929766146118183>❌</emoji> Укажите команду для подбрасывания монетки.",
        "error_general": "<emoji document_id=5854929766146118183>❌</emoji> Произошла ошибка: {error}",
    }

    def get_coin_flip_result(self) -> Dict[str, str]:
        """Get coin flip result with better formatting"""
        return {
            "title": self.strings["titles"],
            "description": self.strings["description"],
            "message": f"<b>{random.choice([self.strings['heads'], self.strings['tails']])}</b>",
            "thumb": "https://github.com/Codwizer/ReModules/blob/main/assets/images.png",
        }

    @loader.command(
        ru_doc="Подбросить монетку",
        en_doc="Flip a coin",
    )
    async def coin_inline_handler(self, query: InlineQuery):
        """Handle coin flip inline query"""
        if not query.args:
            return {
                "title": self.strings["titles"],
                "description": self.strings["no_args"],
                "message": self.strings["no_args"],
            }

        result = self.get_coin_flip_result()
        return {
            "title": self.strings["titles"],
            "description": self.strings["description"],
            "message": result["message"],
            "thumb": result["thumb"],
        }
