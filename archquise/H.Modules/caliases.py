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
# Name: CAliases
# Description: Module for custom aliases
# Author: @hikka_mods
# ---------------------------------------------------------------------------------
# meta developer: @hikka_mods
# scope: CAliases
# scope: CAliases 0.0.1
# ---------------------------------------------------------------------------------

import logging
from typing import Dict, Optional

from telethon import types

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class CustomAliasesMod(loader.Module):
    """Module for custom aliases"""

    strings = {
        "name": "CAliases",
        "c404": "<emoji document_id=5312526098750252863>❌</emoji> <b>Command <code>{}</code> not found!</b>",
        "a404": "<emoji document_id=5312526098750252863>❌</emoji> <b>Custom alias <code>{}</code> not found!</b>",
        "no_args": "<emoji document_id=5312526098750252863>❌</emoji> <b>You must specify two args: alias name and command</b>",
        "added": (
            "<emoji document_id=5314250708508220914>✅</emoji> <b>Custom alias <i>{alias}</i> for command "
            "<code>{prefix}{cmd}</code> successfully added!</b>\n<b>Use it like:</b> <code>{prefix}{alias}{args}</code>"
        ),
        "argsopt": " [args (optional)]",
        "deleted": "<emoji document_id=5314250708508220914>✅</emoji> <b>Custom alias <code>{}</code> successfully deleted</b>",
        "list": "<emoji document_id=5974492756494519709>🔗</emoji> <b>Custom aliases ({len}):</b>\n",
        "no_aliases": "<emoji document_id=5312526098750252863>❌</emoji> <b>You have no custom aliases!</b>",
    }

    strings_ru = {
        "c404": "<emoji document_id=5312526098750252863>❌</emoji> <b>Команда <code>{}</code> не найдена!</b>",
        "a404": "<emoji document_id=5312526098750252863>❌</emoji> <b>Кастомный алиас <code>{}</code> не найден!</b>",
        "no_args": "<emoji document_id=5312526098750252863>❌</emoji> <b>Вы должны указать как минимум два аргумента: имя алиаса и команду</b>",
        "added": (
            "<emoji document_id=5314250708508220914>✅</emoji> <b>Успешно добавил алиас с названием <i>{alias}</i> "
            "для команды <code>{prefix}{cmd}</code></b>\n<b>Используй его так:</b> <code>{prefix}{alias}{args}</code>"
        ),
        "argsopt": " [аргументы (необязательно)]",
        "deleted": "<emoji document_id=5314250708508220914>✅</emoji> <b>Кастомный алиас <code>{}</code> успешно удалён</b>",
        "list": "<emoji document_id=5974492756494519709>🔗</emoji> <b>Кастомные алиасы (всего {len}):</b>\n",
        "no_aliases": "<emoji document_id=5312526098750252863>❌</emoji> <b>У вас нет кастомных алиасов!</b>",
    }

    def __init__(self):
        self._aliases_cache: Optional[Dict[str, Dict[str, str]]] = None
        self._prefix_cache: Optional[str] = None

    def _get_aliases(self) -> Dict[str, Dict[str, str]]:
        if self._aliases_cache is None:
            self._aliases_cache = self.get("aliases", {})
        return self._aliases_cache

    def _save_aliases(self, aliases: Dict[str, Dict[str, str]]) -> None:
        self.set("aliases", aliases)
        self._aliases_cache = aliases

    def _get_prefix(self) -> str:
        if self._prefix_cache is None:
            self._prefix_cache = self.get_prefix()
        return self._prefix_cache

    def _format_alias_list(self) -> str:
        """Format aliases list for display"""
        aliases = self._get_aliases()
        if not aliases:
            return self.strings["no_aliases"]

        lines = [self.strings["list"].format(len=len(aliases))]

        for alias_name, alias_data in aliases.items():
            cmd = alias_data["command"]
            if alias_data.get("args"):
                cmd += f" {alias_data['args']}"

            lines.append(
                f"  <emoji document_id=5280726938279749656>▪️</emoji> <code>{alias_name}</code> "
                f"<emoji document_id=5960671702059848143>👈</emoji> <code>{cmd}</code>"
            )

        return "\n".join(lines)

    def _validate_command(self, cmd: str) -> bool:
        """Check if command exists"""
        return cmd in self.allmodules.commands

    def _parse_alias_args(self, message: types.Message) -> tuple:
        """Parse alias command arguments"""
        raw_args = utils.get_args_raw(message)
        if not raw_args:
            return None, None, None

        parts = raw_args.split(" ", 2)
        if len(parts) < 2:
            return None, None, None

        alias_name = parts[0]
        command = parts[1]
        cmd_args = parts[2] if len(parts) > 2 else ""

        return alias_name, command, cmd_args

    @loader.command(
        ru_doc="Получить список всех алиасов",
        en_doc=" Get list of all aliases"
    )
    async def caliasescmd(self, message: types.Message):
        """Get all aliases"""
        await utils.answer(message, self._format_alias_list())

    @loader.command(
        ru_doc="<имя> Удалить алиас",
        en_doc="<name> Remove alias"
    )
    async def rmcaliascmd(self, message: types.Message):
        """Remove alias"""
        args = utils.get_args(message)
        if not args:
            return await utils.answer(message, self.strings["no_args"])

        alias_name = args[0]
        aliases = self._get_aliases()

        if alias_name not in aliases:
            return await utils.answer(message, self.strings["a404"].format(alias_name))

        del aliases[alias_name]
        self._save_aliases(aliases)
        await utils.answer(message, self.strings["deleted"].format(alias_name))

    @loader.command(
        ru_doc="<имя> <команда> [аргументы] Добавить новый алиас (может содержать ключевое слово {args})",
        en_doc="<name> <command> [arguments] Add new alias (may contain {args} keyword)",
    )
    async def caliascmd(self, message: types.Message):
        """Add new alias (may contain {args} keyword)"""
        alias_name, command, cmd_args = self._parse_alias_args(message)

        if not alias_name or not command:
            return await utils.answer(message, self.strings["no_args"])

        if not self._validate_command(command):
            return await utils.answer(message, self.strings["c404"].format(command))

        aliases = self._get_aliases()
        aliases[alias_name] = {"command": command, "args": cmd_args}
        self._save_aliases(aliases)

        prefix = self._get_prefix()
        full_cmd = f"{command} {cmd_args}" if cmd_args else command
        args_display = self.strings["argsopt"] if "{args}" in cmd_args else ""

        await utils.answer(
            message,
            self.strings["added"].format(
                alias=alias_name,
                prefix=prefix,
                cmd=full_cmd,
                args=args_display,
            ),
        )

    @loader.tag(only_messages=True, no_media=True, no_inline=True, out=True)
    async def watcher(self, message: types.Message):
        """Handle alias execution"""
        if not message.raw_text:
            return

        aliases = self._get_aliases()
        prefix = self._get_prefix()
        text = message.raw_text
        first_word = text.split()[0].lower()

        if not first_word.startswith(prefix):
            return

        alias_name = first_word[len(prefix) :]
        if alias_name not in aliases:
            return

        alias_data = aliases[alias_name]
        command = alias_data["command"]
        template_args = alias_data.get("args", "")

        user_args = utils.get_args_raw(message)
        if user_args and template_args:
            final_command = f"{command} {template_args}".format(args=user_args)
        else:
            final_command = f"{command} {template_args}" if template_args else command

        try:
            await self.allmodules.commands[command](
                await utils.answer(message, f"{prefix}{final_command}")
            )
        except Exception as e:
            logger.error(f"Error executing alias '{alias_name}': {e}")
