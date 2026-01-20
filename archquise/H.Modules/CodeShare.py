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
# Name: CodeShare
# Description: Uploads your code at the kmi.aeza.net (Pastebin and GitHub Gist alternative)
# Author: @hikka_mods
# ---------------------------------------------------------------------------------
# meta developer: @hikka_mods
# requires: aiofiles
# ---------------------------------------------------------------------------------

import aiohttp
import aiofiles
import os
import logging

from .. import loader, utils
from telethon.types import MessageMediaDocument

logger = logging.getLogger(__name__)


@loader.tds
class CodeShareMod(loader.Module):
    """Uploads your code at the kmi.aeza.net (Pastebin and GitHub Gist alternative)"""

    strings = {
        "name": "CodeShare",
        "invalid_args": "<emoji document_id=5854929766146118183>❌</emoji> There is no arguments or reply with a file, or they are invalid",
        "_cls_doc": "Uploads your code at the kmi.aeza.net (Pastebin and GitHub Gist alternative)",
        "link_ready": "<emoji document_id=5854762571659218443>✅</emoji> <b>Code uploaded! Link:</b> <code>{}</code>",
    }

    strings_ru = {
        "_cls_doc": "Загружает ваш код на kmi.aeza.net (альтернатива Pastebin и GitHub Gist)",
        "invalid_args": "<emoji document_id=5854929766146118183>❌</emoji> Нет аргументов или реплая с файлом, или они неверны",
        "link_ready": "<emoji document_id=5854762571659218443>✅</emoji> <b>Код загружен! Ссылка:</b> <code>{}</code>",
    }

    async def upload_to_kmi(self, content: str) -> str:
        url = "https://kmi.aeza.net"
        data = aiohttp.FormData()
        data.add_field("kmi", content)

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    link = await response.text()
                    return link
                else:
                    logger.error(f"Error occurred! Status code: {response.status}")
                    return

    @loader.command(
        ru_doc="Загрузка кода на сайт",
        en_doc="Upload code to the site",
    )
    async def codesharecmd(self, message):
        args = utils.get_args(message)
        reply = await message.get_reply_message()
        if args:
            link = await self.upload_to_kmi(args)
            await utils.answer(message, self.strings["link_ready"].format(link))
            return
        if reply and isinstance(reply.media, MessageMediaDocument):
            file_name = await reply.download_media()
            async with aiofiles.open(file_name, mode="r") as f:
                content = await f.read()
            link = await self.upload_to_kmi(content)
            await os.remove(file_name)
            await utils.answer(message, self.strings["link_ready"].format(link))
            return
        await utils.answer(message, self.strings["invalid_args"])
