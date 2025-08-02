__version__ = (1, 1, 0)
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
# randomtrack.py
# meta developer: @systemxplore
# scope: hikka_only
# scope: hikka_min 1.6.3

import random
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import Message, MessageMediaDocument
from .. import loader, utils

class RandomTrackMod(loader.Module):
    """Отправляет случайный трек из указанного канала."""
    strings = {"name": "RandomTrack"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "MUSIC_CHANNEL_ID", 0,  # ID канала с музыкой
            lambda: "ID вашего канала с музыкой. Например: 123456789"
        )

    async def get_random_track(self, channel_id):
        """Получает случайный трек из указанного канала по ID."""
        try:
            history = await self.client(GetHistoryRequest(
                peer=channel_id,
                limit=100,  # Загружает последние 100 сообщений
                offset_date=None,
                offset_id=0,
                add_offset=0,
                max_id=0,
                min_id=0,
                hash=0,
            ))
            
            tracks = [
                msg for msg in history.messages
                if isinstance(msg, Message) and isinstance(msg.media, MessageMediaDocument)
                and msg.media.document.mime_type.startswith("audio")
            ]
            return random.choice(tracks) if tracks else None
        except Exception as e:
            return f"Ошибка при получении трека: {e}"

    @loader.command()
    async def randomtrack(self, message):
        """
        Отправляет случайный трек из вашего канала.
        """
        channel_id = self.config["MUSIC_CHANNEL_ID"]
        if not channel_id:
            await utils.answer(message, "❌ Укажите ID канала с музыкой в .config")
            return

        track = await self.get_random_track(channel_id)
        if isinstance(track, Message):
            await self.client.send_file(message.chat_id, track.media, caption=track.message or "")
        else:
            await utils.answer(message, f"❌ Не удалось получить трек. Причина: {track}")