__version__ = (1, 1, 2)
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
# avaclone.py
# meta developer: @systemxplore
# scope: hikka_only
# scope: hikka_min 1.6.3

import asyncio
from telethon.tl.functions.photos import UploadProfilePhotoRequest
from telethon.errors.rpcerrorlist import PhotoCropSizeSmallError, FilePartsInvalidError
from telethon.tl.types import InputFile
from .. import loader, utils

class AvaCloneMod(loader.Module):
    """Устанавливает фото/видео/гиф аватарку многократно.\nОсторожно: возможен бан или флудвейт."""
    strings = {"name": "AvaClone"}

    @loader.command()
    async def avaclone(self, message):
        """
        Устанавливает аватарку указанное количество раз.
        Используйте: .avaclone <количество> [ответ на файл/ссылка]
        """
        args = utils.get_args(message)
        if len(args) < 1:
            await utils.answer(message, "Укажите количество раз и прикрепите файл.")
            return

        try:
            count = int(args[0])
            if count <= 0:
                raise ValueError
        except ValueError:
            await utils.answer(message, "Некорректное количество раз.")
            return

        reply = await message.get_reply_message()
        media = None

        if reply and reply.media:
            media = await self.client.download_media(reply.media)
        elif len(args) > 1:
            media = args[1]
        else:
            await utils.answer(message, "Ответьте на файл или укажите ссылку на файл.")
            return

        extension = media.split(".")[-1].lower()
        if extension not in ["jpg", "jpeg", "png", "gif", "mp4"]:
            await utils.answer(message, "❌ Формат не поддерживается. Используйте JPG, PNG, GIF или MP4.")
            return

        success_count = 0
        for i in range(count):
            try:
                uploaded_file = await self.client.upload_file(media)
                if extension in ["gif", "mp4"]:
                    await self.client(UploadProfilePhotoRequest(
                        file=InputFile(
                            id=uploaded_file.id,
                            parts=uploaded_file.parts,
                            name=media,
                            md5_checksum=uploaded_file.md5_checksum
                        )
                    ))
                else:
                    await self.client(UploadProfilePhotoRequest(file=uploaded_file))
                success_count += 1
                await asyncio.sleep(2)
            except PhotoCropSizeSmallError:
                await utils.answer(message, "❌ Файл слишком маленький.")
                break
            except FilePartsInvalidError:
                await utils.answer(message, "❌ Неверный файл.")
                break
            except Exception as e:
                await utils.answer(message, f"Ошибка: {e}")
                break

        if success_count > 0:
            await utils.answer(
                message,
                f"✅ Установлено {success_count} раз(а). Возможен флудвейт, подождите 3 минуты перед следующим использованием."
            )
        else:
            await utils.answer(message, "❌ Не удалось установить аватарку.")