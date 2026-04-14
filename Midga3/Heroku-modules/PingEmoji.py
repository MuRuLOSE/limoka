#Midga3
#Placeholder system is the best

# meta developer: @midga3_modules
__version__ = (1, 1, 2)

import logging
import aiohttp
import asyncio
from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class PingEmoji(loader.Module):
    strings = {
        "name": "PingEmoji"
    }
    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "emoji", 
                "<tg-emoji emoji-id=5276307163529092252>🔴</tg-emoji>",
                "Ping Emoji",
            )
        )
    async def client_ready(self, client, db):
        self._client = client
        utils.register_placeholder("ping_emoji", self.get_emoji)

    async def get_emoji(self, data):
        if data['ping'] > 300:
            return self.config['emoji']
        else:
            return ""
