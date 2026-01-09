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
# Name: Profile
# Description: This module can change your Telegram profile
# Author: @hikka_mods
# ---------------------------------------------------------------------------------
# meta developer: @hikka_mods
# scope: Profile
# scope: Profile 0.0.1
# ---------------------------------------------------------------------------------

import logging
import re

from telethon.errors.rpcerrorlist import UsernameOccupiedError, FloodWaitError
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class ProfileEditorMod(loader.Module):
    """This module can change your Telegram profile."""

    strings = {
        "name": "Profile",
        "error_format": "<emoji document_id=5854929766146118183>❌</emoji> Incorrect format. Try again.",
        "done_name": "<emoji document_id=5854762571659218443>✅</emoji> Name successfully updated!",
        "done_bio": "<emoji document_id=5854762571659218443>✅</emoji> Bio successfully updated!",
        "done_username": "<emoji document_id=5854762571659218443>✅</emoji> Username successfully updated!",
        "error_occupied": "<emoji document_id=5854929766146118183>❌</emoji> Username is already occupied!",
        "error_invalid_username": "<emoji document_id=5854929766146118183>❌</emoji> Invalid username format!",
        "error_flood": "<emoji document_id=5854929766146118183>❌</emoji> Too many requests. Try again later.",
        "error_general": "<emoji document_id=5854929766146118183>❌</emoji> An error occurred: {error}",
    }

    strings_ru = {
        "error_format": "<emoji document_id=5854929766146118183>❌</emoji> Неверный формат. Попробуйте еще раз.",
        "done_name": "<emoji document_id=5854762571659218443>✅</emoji> Имя успешно обновлено!",
        "done_bio": "<emoji document_id=5854762571659218443>✅</emoji> Био успешно обновлено!",
        "done_username": "<emoji document_id=5854762571659218443>✅</emoji> Имя пользователя успешно обновлено!",
        "error_occupied": "<emoji document_id=5854929766146118183>❌</emoji> Имя пользователя уже занято!",
        "error_invalid_username": "<emoji document_id=5854929766146118183>❌</emoji> Неверный формат имени пользователя!",
        "error_flood": "<emoji document_id=5854929766146118183>❌</emoji> Слишком много запросов. Попробуйте позже.",
        "error_general": "<emoji document_id=5854929766146118183>❌</emoji> Произошла ошибка: {error}",
    }

    def __init__(self):
        pass

    def _validate_username(self, username: str) -> bool:
        """Validate username format"""
        if not username:
            return False

        username = username.strip("@")
        if len(username) < 5 or len(username) > 32:
            return False

        return re.match(r"^[a-zA-Z0-9_]+$", username) is not None

    def _sanitize_name(self, name: str) -> str:
        """Sanitize name input"""
        if not name:
            return ""

        return " ".join(name.split())[:64]

    def _sanitize_bio(self, bio: str) -> str:
        """Sanitize bio input"""
        if not bio:
            return ""

        bio = bio.strip()
        limit = 70 if not self._client.hikka_me.premium else 140
        if len(bio) < limit:
            return bio[:limit]
        else:
            return bio[: limit - 3] + "..."

    async def _handle_error(self, message, error: Exception):
        """Handle common errors"""
        if isinstance(error, UsernameOccupiedError):
            await utils.answer(message, self.strings("error_occupied"))
        elif isinstance(error, FloodWaitError):
            await utils.answer(message, self.strings("error_flood"))
        else:
            await utils.answer(
                message, self.strings("error_general").format(error=str(error))
            )

    @loader.command(
        ru_doc="для того, чтобы сменить свое имя/отчество",
        en_doc="for change your first/second name",
    )
    async def namecmd(self, message):
        """Change first name and last name"""
        args = utils.get_args_raw(message)
        if not args:
            return await utils.answer(message, self.strings("error_format"))

        if "/" in args:
            parts = args.split("/", 1)
        else:
            parts = args.split(" ", 1)

        if len(parts) < 1:
            return await utils.answer(message, self.strings("error_format"))

        firstname = self._sanitize_name(parts[0])
        lastname = self._sanitize_name(parts[1]) if len(parts) > 1 else ""

        if not firstname:
            return await utils.answer(message, self.strings("error_format"))

        try:
            await message.client(
                UpdateProfileRequest(first_name=firstname, last_name=lastname)
            )
            await utils.answer(message, self.strings("done_name"))
        except Exception as e:
            await self._handle_error(message, e)

    @loader.command(
        ru_doc="для изменения вашего имени пользователя. Введите значение без '@'",
        en_doc="for change your username. Enter value without '@'",
    )
    async def aboutcmd(self, message):
        """Change profile bio"""
        args = utils.get_args_raw(message)
        if not args:
            return await utils.answer(message, self.strings("error_format"))

        bio = self._sanitize_bio(args)

        try:
            await message.client(UpdateProfileRequest(about=bio))
            await utils.answer(message, self.strings("done_bio"))
        except Exception as e:
            await self._handle_error(message, e)

    @loader.command(
        ru_doc="для изменения вашего имени пользователя. Введите значение без '@'",
        en_doc="for change your username. Enter value without '@'",
    )
    async def usercmd(self, message):
        """Change username"""
        args = utils.get_args_raw(message)
        if not args:
            return await utils.answer(message, self.strings("error_format"))

        username = args.strip("@")

        if not self._validate_username(username):
            return await utils.answer(message, self.strings("error_invalid_username"))

        try:
            await message.client(UpdateUsernameRequest(username))
            await utils.answer(message, self.strings("done_username"))
        except Exception as e:
            await self._handle_error(message, e)
