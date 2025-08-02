__version__ = (1, 0, 0)
#                                                                                                          
#                                                                                                       88  
#                                                    ,d                                          ,d     88  
#                                                    88                                          88     88  
#  ,adPPYba,  8b,dPPYba,  8b       d8  8b,dPPYba,  MM88MMM  ,adPPYba,  8b,     ,d8  ,adPPYba,  MM88MMM  88  
# a8"     ""  88P'   "Y8  `8b     d8'  88P'    "8a   88    a8P_____88   `Y8, ,8P'  a8"     ""    88     88  
# 8b          88           `8b   d8'   88       d8   88    8PP"""""""     )888(    8b            88     88  
#  "8a,   ,aa  88            `8b,d8'    88b,   ,a8"   88,   "8b,   ,aa   ,d8" "8b,  "8a,   ,aa    88,    88  
#  `"Ybbd8"'  88              Y88'     88`YbbdP"'    "Y888  `"Ybbd8"'  8P'     `Y8  `"Ybbd8"'    "Y888  88  
#                            d8'      88                                                                   
#                           d8'       88                                                                   
#              © Copyright 2024
#           https://t.me/cryptexctl
#
# 🔒      Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html
# premium_emoji_id.py
# meta developer: @systemxplore
# scope: hikka_only

from telethon.tl.types import MessageEntityCustomEmoji
from .. import loader, utils

class GetPremiumEmojiID(loader.Module):
    """Получение ID премиум-эмодзи"""
    strings = {"name": "PremiumEmojiID"}

    @loader.command()
    async def getemoji_id(self, message):
        """
        Получает ID премиум-эмодзи из сообщения
        Использование: .getemoji_id <эмодзи>
        """
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(
                message, "❌ Пожалуйста, добавьте премиум-эмодзи после команды."
            )
            return

        entities = message.entities
        if not entities:
            await utils.answer(message, "❌ Эмодзи не найдено.")
            return

        for entity in entities:
            if isinstance(entity, MessageEntityCustomEmoji):
                emoji_id = entity.document_id
                await utils.answer(
                    message,
                    f"✅ Найден премиум-эмодзи:\n\n"
                    f"💎 ID: `{emoji_id}`\n\n"
                    f"Теперь вы можете использовать его в своих модулях!",
                )
                return

        await utils.answer(message, "❌ Это не премиум-эмодзи.")
