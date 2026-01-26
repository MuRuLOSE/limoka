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
# Name: Privacy
# Description: Module for fast privacy settings management
# Author: @hikka_mods
# ---------------------------------------------------------------------------------
# meta developer: @hikka_mods
# scope: Privacy
# scope: Privacy 0.0.1
# ---------------------------------------------------------------------------------

import logging
import re
from typing import Dict, List, Optional

import telethon
from telethon import types

from .. import inline, loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class PrivacyMod(loader.Module):
    """Module for fast privacy settings management"""

    _PRIVACY_TYPES = {
        "phone": types.InputPrivacyKeyPhoneNumber,
        "add_by_phone": types.InputPrivacyKeyAddedByPhone,
        "online": types.InputPrivacyKeyStatusTimestamp,
        "photos": types.InputPrivacyKeyProfilePhoto,
        "forwards": types.InputPrivacyKeyForwards,
        "calls": types.InputPrivacyKeyPhoneCall,
        "p2p": types.InputPrivacyKeyPhoneP2P,
        "voices": types.InputPrivacyKeyVoiceMessages,
        "bio": getattr(types, "InputPrivacyKeyAbout", None),
        "invites": types.InputPrivacyKeyChatInvite,
    }

    _PRIVACY_RULES = {
        types.PrivacyValueAllowAll: types.InputPrivacyValueAllowAll,
        types.PrivacyValueAllowChatParticipants: types.InputPrivacyValueAllowChatParticipants,
        types.PrivacyValueAllowContacts: types.InputPrivacyValueAllowContacts,
        types.PrivacyValueAllowUsers: types.InputPrivacyValueAllowUsers,
        types.PrivacyValueDisallowAll: types.InputPrivacyValueDisallowAll,
        types.PrivacyValueDisallowChatParticipants: types.InputPrivacyValueDisallowChatParticipants,
        types.PrivacyValueDisallowContacts: types.InputPrivacyValueDisallowContacts,
        types.PrivacyValueDisallowUsers: types.InputPrivacyValueDisallowUsers,
    }

    strings = {
        "name": "Privacy",
        "privacy_types": (
            "<emoji document_id=5974492756494519709>🔗</emoji> <b>Available privacy types:</b>\n"
        ),
        "no_user": "<emoji document_id=5312383351217201533>⚠️</emoji> <b>User not specified</b>",
        "u_silly": (
            "<emoji document_id=5449682572223194186>🥺</emoji> <b>You can't set privacy exceptions for yourself</b>"
        ),
        "choose_type": "🔑 <b>Select privacy type to manage</b>",
        "not_supported_type": (
            "<emoji document_id=5312383351217201533>⚠️</emoji> <b>Privacy type '{}' not supported</b>"
        ),
        "allowed": (
            "<emoji document_id=5298609004551887592>💕</emoji> <b>{user} added to allowed users for [{type}]</b>"
        ),
        "disallowed": (
            "<emoji document_id=5224379368242965520>💔</emoji> <b>{user} added to disallowed users for [{type}]</b>"
        ),
        "privacy": {
            "phone": "Phone Number",
            "add_by_phone": "Find by Phone",
            "p2p": "P2P Calls",
            "online": "Last Seen",
            "photos": "Profile Photos",
            "forwards": "Message Forwards",
            "calls": "Phone Calls",
            "voices": "Voice Messages",
            "bio": "Bio",
            "invites": "Chat Invites",
        },
    }

    strings_ru = {
        "_cls_doc": "Модуль для быстрого управления настройками приватности",
        "privacy_types": (
            "<emoji document_id=5974492756494519709>🔗</emoji> <b>Доступные типы приватности:</b>\n"
        ),
        "no_user": "<emoji document_id=5312383351217201533>⚠️</emoji> <b>Пользователь не указан</b>",
        "u_silly": (
            "<emoji document_id=5449682572223194186>🥺</emoji> <b>Нельзя установить исключения приватности для самого себя</b>"
        ),
        "choose_type": "🔑 <b>Выберите тип настроек приватности</b>",
        "not_supported_type": (
            "<emoji document_id=5312383351217201533>⚠️</emoji> <b>Тип приватности '{}' не поддерживается</b>"
        ),
        "allowed": (
            "<emoji document_id=5298609004551887592>💕</emoji> <b>{user} добавлен в разрешённые для [{type}]</b>"
        ),
        "disallowed": (
            "<emoji document_id=5224379368242965520>💔</emoji> <b>{user} добавлен в запрещённые для [{type}]</b>"
        ),
        "privacy": {
            "phone": "Номер телефона",
            "add_by_phone": "Поиск по номеру",
            "p2p": "P2P звонки",
            "online": "Последний вход",
            "photos": "Фотографии профиля",
            "forwards": "Пересылка сообщений",
            "calls": "Звонки",
            "voices": "Голосовые сообщения",
            "bio": "О себе",
            "invites": "Приглашения в чаты",
        },
    }

    def __init__(self):
        self._client: Optional[telethon.TelegramClient] = None
        self._me: Optional[types.User] = None

    async def client_ready(self, client: telethon.TelegramClient, db) -> None:
        """Initialize client and get current user"""
        self._client = client
        self._me = await client.get_me()

    async def _get_user_id(self, message: types.Message) -> Optional[int]:
        """Extract user ID from reply or username"""
        reply = await message.get_reply_message()
        if reply:
            return reply.sender_id

        args = utils.get_args(message)
        if not args:
            return None

        username = args[0]
        match = re.search(r"(?:t\.me/|@|^(\w+)\.t\.me$)([a-zA-Z0-9_.]+)", username)
        if not match:
            return None

        username = match.group(1) or match.group(2)
        try:
            entity = await self._client.get_entity(username)
            return getattr(entity, "user_id", getattr(entity, "id", None))
        except Exception:
            return None

    def _format_privacy_list(self) -> str:
        """Format privacy types list"""
        lines = [self.strings["privacy_types"]]

        for key, name in self.strings["privacy"].items():
            if key in self._PRIVACY_TYPES:
                lines.append(f"  <code>{key}</code> — {name}")

        return "\n".join(lines)

    def _create_privacy_keyboard(
        self, user: types.User, action: str
    ) -> List[List[Dict]]:
        """Create inline keyboard for privacy type selection"""
        buttons = []

        for key, name in self.strings["privacy"].items():
            if key not in self._PRIVACY_TYPES:
                continue

            buttons.append(
                [
                    {
                        "text": name,
                        "callback": self._privacy_callback_handler,
                        "args": (user, key, action),
                    }
                ]
            )

        return [buttons[i : i + 2] for i in range(0, len(buttons), 2)]

    async def _privacy_callback_handler(self, call: inline.types.InlineCall) -> None:
        """Handle privacy type selection callback"""
        user, privacy_key, action = call.data

        if privacy_key not in self._PRIVACY_TYPES:
            await call.answer(self.strings["not_supported_type"].format(privacy_key))
            return

        privacy_type = self._PRIVACY_TYPES[privacy_key]
        await self._update_privacy_settings(user, privacy_type, action)

        action_text = "allowed" if action == "allow" else "disallowed"
        await call.edit(
            self.strings[action_text].format(
                user=telethon.utils.get_display_name(user),
                type=self.strings["privacy"][privacy_key],
            )
        )

    async def _update_privacy_settings(
        self, user: types.User, privacy_key: types.TypeInputPrivacyKey, action: str
    ) -> None:
        """Update privacy settings for specified user"""
        try:
            current_rules = await self._client(
                telethon.functions.account.GetPrivacyRequest(key=privacy_key)
            )
        except Exception as e:
            logger.error(f"Error getting privacy rules: {e}")
            return

        new_rules = []
        existing_user_ids = set()

        for rule in current_rules.rules:
            rule_type = type(rule)

            if rule_type == types.PrivacyValueAllowUsers:
                for user_id in rule.users:
                    existing_user_ids.add(user_id)
                    if user_id != user.id:
                        new_rules.append(rule)
            elif rule_type == types.PrivacyValueDisallowUsers:
                for user_id in rule.users:
                    existing_user_ids.add(user_id)
                    if user_id != user.id:
                        new_rules.append(rule)

        if action == "allow" and user.id not in existing_user_ids:
            new_rules.append(
                types.InputPrivacyValueAllowUsers(
                    [types.InputUser(user.id, user.access_hash)]
                )
            )
        elif action == "disallow" and user.id in existing_user_ids:
            for rule in new_rules[:]:
                if type(rule) in [
                    types.PrivacyValueAllowUsers,
                    types.PrivacyValueDisallowUsers,
                ]:
                    user_list = getattr(rule, "users", [])
                    if user.id in user_list:
                        user_list.remove(user.id)
                        if not user_list:
                            new_rules.remove(rule)
                            break

        try:
            await self._client(
                telethon.functions.account.SetPrivacyRequest(
                    key=privacy_key, rules=new_rules
                )
            )
        except Exception as e:
            logger.error(f"Error updating privacy settings: {e}")

    @loader.command(
        ru_doc="Список типов настроек приватности",
        en_doc="List of privacy types"
    )
    async def privacytypescmd(self, message: types.Message) -> None:
        """Show available privacy types"""
        await utils.answer(message, self._format_privacy_list())

    @loader.command(
        ru_doc="<user> Добавить в разрешённые",
        en_doc="<user> Add to allowed list",
    )
    async def allowusercmd(self, message: types.Message) -> None:
        """Add user to privacy exceptions"""
        user_id = await self._get_user_id(message)
        if not user_id:
            return await utils.answer(message, self.strings["no_user"])

        if user_id == self._me.id:
            return await utils.answer(message, self.strings["u_silly"])

        try:
            user_entity = await self._client.get_entity(user_id)
        except Exception:
            return await utils.answer(message, self.strings["no_user"])

        await self.inline.form(
            message=message,
            text=self.strings["choose_type"],
            reply_markup=self._create_privacy_keyboard(user_entity, "allow"),
        )

    @loader.command(
        ru_doc="<user> Добавить в запрещённые",
        en_doc="<user> Add to forbidden list",
    )
    async def disallowuser(self, message: types.Message) -> None:
        """Add user to privacy restrictions"""
        user_id = await self._get_user_id(message)
        if not user_id:
            return await utils.answer(message, self.strings["no_user"])

        if user_id == self._me.id:
            return await utils.answer(message, self.strings["u_silly"])

        try:
            user_entity = await self._client.get_entity(user_id)
        except Exception:
            return await utils.answer(message, self.strings["no_user"])

        await self.inline.form(
            message=message,
            text=self.strings["choose_type"],
            reply_markup=self._create_privacy_keyboard(user_entity, "disallow"),
        )

    async def _create_privacy_keyboard(
        self, user: types.User, action: str
    ) -> List[List[Dict]]:
        """Create inline keyboard for privacy type selection"""
        buttons = []

        for key, name in self.strings["privacy"].items():
            if key not in self._PRIVACY_TYPES:
                continue

            buttons.append(
                [
                    {
                        "text": name,
                        "callback": self._privacy_callback_handler,
                        "args": (user, key, action),
                    }
                ]
            )

        return [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
