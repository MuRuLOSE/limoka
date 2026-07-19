# requires: Pillow
# meta developer: @H_SunMods
# meta pic: https://r2.fakecrime.bio/uploads/47308ab9-6035-4e7d-bc96-6b58f864bb33.jpg
# meta banner: https://r2.fakecrime.bio/uploads/47308ab9-6035-4e7d-bc96-6b58f864bb33.jpg
# meta fhsdesc: Theme, Темы, Sunnex, SunnexGB, H_SunMods
# это прям жеске тест, все мега поносно,я буду стараяться это обновлять,чисто так коментарий для тех кто любит читать код или... 
# сувать свой нос куда попало. Ну а потом планируеться там условно сделать для IOS и Desktop тоже самое.
# баннер я тоже переделаю,но мне лень пока что...

import io
import logging
from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class tgtheme(loader.Module):
    """Module that creates an android-theme from a photo"""

    strings = {
        "name": "TgTheme (Mega-BETA)",
        "no_photo": "<b>Reply to a photo/b>",
        "no_lib": "<b>Library not loaded</b>",
    }

    strings_ru = {
        "_cls_doc": "Модуль который создает тг-тему по фото",
        "no_photo": "<b>Ответьте на фото</b>",
        "no_lib": "<b>Библиотека не загружена</b>",
    }

    def __init__(self):
        self.lib = None

    async def client_ready(self):
        try:
            self.lib = await self.import_lib(
                "https://raw.githubusercontent.com/SunnexGB/Heroku-Modules/refs/heads/main/Assets/TgTheme/TgThemeLib.py",
                suspend_on_error=True,
            )
        except Exception:
            logger.exception("Failed to load library")
            self.lib = None

    @loader.command(ru_doc="- Создать тг-тему по фото")
    async def android(self, message):
        """- Create tg-theme from a photo"""
        if not self.lib:
            return await utils.answer(message, self.strings["no_lib"])
        args = utils.get_args_raw(message)
        transparency = 100
        if args.strip().isdigit():
            transparency = max(0, min(100, int(args.strip())))
        alpha = f"{int(transparency / 100 * 255):02x}"
        reply = await message.get_reply_message() or message
        photo = None
        if reply.photo:
            photo = reply.photo
        elif reply.document and reply.document.mime_type and reply.document.mime_type.startswith("image/"):
            photo = reply.document
        if photo is None:
            await utils.answer(message, self.strings["no_photo"])
            return
        try:
            photo_bytes = await self.client.download_media(photo, bytes)
            theme_bytes = self.lib.process_photo(photo_bytes, alpha)
            file = io.BytesIO(theme_bytes)
            file.name = "android.attheme"
            await message.edit(file=file, text="<3")
        except Exception:
            pass
