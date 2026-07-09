# -- version --
__version__ = (1, 0, 0)
# -- version --


# ███╗░░░███╗███████╗░█████╗░██████╗░░█████╗░░██╗░░░░░░░██╗░██████╗░██████╗
# ████╗░████║██╔════╝██╔══██╗██╔══██╗██╔══██╗░██║░░██╗░░██║██╔════╝██╔════╝
# ██╔████╔██║█████╗░░███████║██║░░██║██║░░██║░╚██╗████╗██╔╝╚█████╗░╚█████╗░
# ██║╚██╔╝██║██╔══╝░░██╔══██║██║░░██║██║░░██║░░████╔═████║░░╚═══██╗░╚═══██╗
# ██║░╚═╝░██║███████╗██║░░██║██████╔╝╚█████╔╝░░╚██╔╝░╚██╔╝░██████╔╝██████╔╝
# ╚═╝░░░░░╚═╝╚══════╝╚═╝░░╚═╝╚═════╝░░╚════╝░░░░╚═╝░░░╚═╝░░╚═════╝░╚═════╝░
#                © Copyright 2026
#            ✈ https://t.me/mead0wssMods


# meta developer: @mead0wssMods
# scope: heroku_only
# requires: aiohttp pillow

import io
import aiohttp
import logging
from PIL import Image
from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class RamkaMod(loader.Module):
    """Вставляет фото в рамку"""

    strings = {
        "name": "Ramka",
        "no_reply": "<b><tg-emoji emoji-id=5870782662234346251>🖼</tg-emoji></b><b> Требуется реплай на фото!</b>",
        "processing": "<tg-emoji emoji-id=5116476703002068797>⌛️</tg-emoji> <b>Процесс создания рамки...</b>",
        "download_error": "<tg-emoji emoji-id=5078075400408531654>❌</tg-emoji> <b>Ошибка при скачивании исходника рамки.</b>",
        "process_error": "<tg-emoji emoji-id=5078075400408531654>❌</tg-emoji> <b>Ошибка при обработке фото:</b> <code>{}</code>"
    }

    async def client_ready(self, client, db):
        self.client = client
    
    async def fetch_bytes(self, url: str) -> bytes:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
        return None

    @loader.command()
    async def ramka(self, message):
        """- Сделай реплай на фото, чтобы вставить его в рамку"""
        
        reply = await message.get_reply_message()

        if not reply or not reply.photo:
            return await utils.answer(message, self.strings["no_reply"])

        m = await utils.answer(message, self.strings["processing"])

        frame_bytes = await self.fetch_bytes("https://raw.githubusercontent.com/mead0wsss/mead0wsMods/modules/rama.png")
        if not frame_bytes:
            return await utils.answer(message, self.strings["download_error"])

        photo_bytes = await reply.download_media(bytes)

        try:
            frame_img = Image.open(io.BytesIO(frame_bytes)).convert("RGBA")
            bg_color = frame_img.getpixel((0, 0))
            if bg_color[3] != 0:
                data = frame_img.getdata()
                new_data = [(0, 0, 0, 0) if item == bg_color else item for item in data]
                frame_img.putdata(new_data)

            fw, fh = frame_img.size
            user_img = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")

            user_img_stretched = user_img.resize(
                (fw - int(fw * 0.16) - int(fw * 0.16), fh - int(fh * 0.16) - int(fh * 0.15)), 
                Image.Resampling.LANCZOS
            )

            result_img = Image.new("RGBA", (fw, fh), (0, 0, 0, 255))
            result_img.paste(user_img_stretched, (int(fw * 0.16) + 20, int(fh * 0.16)))
            result_img.paste(frame_img, (0, 0), frame_img)

            output = io.BytesIO()
            result_img.save(output, format="PNG")
            output.seek(0)
            output.name = "framed_photo.png"

            await self.client.send_file(
                message.peer_id, 
                file=output,
                reply_to=reply.id
            )
            
            await m.delete()

        except Exception as e:
            logger.error(f"Error in Ramka: {e}")
            await utils.answer(message, self.strings["process_error"].format(str(e)))