__version__ = (0, 0, 2)
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
# something.py
# meta developer: @systemxplore
# scope: hikka_only
from telethon.tl.functions.messages import SendMediaRequest
from telethon.tl.types import InputMediaPhotoExternal
from .. import loader, utils


@loader.tds
class ScriptErrorMod(loader.Module):
    strings = {"name": "ScriptErrorSender"}

    async def client_ready(self, client, db):
        self.client = client

    @loader.command()
    async def скриптовыеошибки(self, message):
        image_url = "https://0x0.st/s/57tTFWzUT0tc4HmuG75z_Q/XnMz.jpg"
        caption = "⚠️Что-то создает скриптовые ошибки"

        reply_to = await message.get_reply_message()

        try:
            await self.client(
                SendMediaRequest(
                    peer=message.chat_id,
                    media=InputMediaPhotoExternal(url=image_url),
                    message=caption,
                    reply_to_msg_id=reply_to.id if reply_to else None
                )
            )
        except Exception as e:
            await utils.answer(message, f"⚠️Что-то создает скриптовые ошибки")

        # Удаляем команду после выполнения
        await message.delete()
