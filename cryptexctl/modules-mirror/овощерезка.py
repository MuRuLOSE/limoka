__version__ = (1, 4, 0)
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
# овощерезка.py
# meta developer: @systemxplore
# scope: hikka_only
# scope: hikka_min 1.6.3

import random
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import Message, MessageMediaPhoto
from .. import loader, utils

class RandomPostMod(loader.Module):
    """Отправляет случайный пост из p2 или pixelgang с картинками."""
    strings = {"name": "Овощерезка"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "POSTS_LIMIT", 50,  # Количество постов для загрузки
            lambda: "Количество постов для загрузки из каналов."
        )

    async def get_random_post(self, channel):
        """Вгетаем фоточке из канала"""
        try:
            history = await self.client(GetHistoryRequest(
                peer=channel,
                limit=self.config["POSTS_LIMIT"],  # Количество постов из .config
                offset_date=None,
                offset_id=0,
                add_offset=0,
                max_id=0,
                min_id=0,
                hash=0,
            ))
            messages = [
                msg for msg in history.messages
                if isinstance(msg, Message) and isinstance(msg.media, MessageMediaPhoto)
            ]
            return random.choice(messages) if messages else None
        except Exception as e:
            return f"Ошибка при получении поста: {e}"

    @loader.command()
    async def овощерезка(self, message):
        """
        Отправляет случайный мемасек из p2 или pixelgang 
        """
        channel = random.choice(["pocobytes", "pixelgang"])  # Случайный выбор канала
        post = await self.get_random_post(channel)

        if isinstance(post, Message):
            await self.client.send_file(message.chat_id, post.media, caption=post.message or "")
        else:
            await utils.answer(message, f"❌ Не удалось получить пост. Причина: {post}")