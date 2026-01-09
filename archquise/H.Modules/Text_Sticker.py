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
# Name: Text in sticker
# Description: Text in sticker
# Author: @hikka_mods
# Commands:
# .st <hex color> [text]
# ---------------------------------------------------------------------------------
# meta developer: @hikka_mods
# scope: Text in sticker
# scope: Text in sticker 0.0.1
# requires: requests
# ---------------------------------------------------------------------------------

import io
import logging
from textwrap import wrap

import requests
from PIL import Image, ImageColor, ImageDraw, ImageFont

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class TextinstickerMod(loader.Module):
    """Text to sticker"""

    strings = {
        "name": "Text in sticker",
        "error": "white st <color name> [text]",
    }

    strings_ru = {
        "error": "Укажите .st <color name> [text]",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "font",
                "https://github.com/CodWize/ReModules/blob/main/assets/Samson.ttf?raw=true",
                lambda: "add a link to the font you want",
            )
        )

    @loader.command(
        ru_doc="<название цвета> [текст]",
        en_doc="<color name> [text]",
    )
    @loader.owner
    async def stcmd(self, message):
        await message.delete()

        text = utils.get_args_raw(message)
        reply = await message.get_reply_message()

        if not text:
            if reply and reply.message:
                text = reply.raw_text
            else:
                text = self.strings("error")

        parts = text.split(" ", 1)
        color_name = parts[0].lower()

        if len(parts) > 1:
            text = parts[1]
        elif reply and reply.message:
            text = reply.raw_text

        try:
            color = ImageColor.getrgb(color_name)
        except ValueError:
            color = (255, 255, 255)

        wrapped_lines = []
        for line in text.split("\n"):
            wrapped_lines.extend(wrap(line, 30))
        wrapped_text = "\n".join(wrapped_lines)

        if not hasattr(self, "_font_cache") or self._font_url != self.config["font"]:
            response = requests.get(self.config["font"])
            response.raise_for_status()
            self._font_cache = io.BytesIO(response.content)
            self._font_url = self.config["font"]

        font = ImageFont.truetype(self._font_cache, 100)

        temp_image = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp_image)
        bbox = temp_draw.multiline_textbbox((0, 0), wrapped_text, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]

        image = Image.new("RGBA", (w + 100, h + 100), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.multiline_text(
            (50, 50), wrapped_text, font=font, fill=color, align="center"
        )

        output = io.BytesIO()
        output.name = f"{color_name}.webp"
        image.save(output, "WEBP")
        output.seek(0)
        await self.client.send_file(message.to_id, output, reply_to=reply)
