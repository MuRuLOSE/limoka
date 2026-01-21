#         ______     ___  ___          _       _      
#    ____ | ___ \    |  \/  |         | |     | |     
#   / __ \| |_/ /   _| .  . | ___   __| |_   _| | ___ 
#  / / _` |  __/ | | | |\/| |/ _ \ / _` | | | | |/ _ \
# | | (_| | |  | |_| | |  | | (_) | (_| | |_| | |  __/
#  \ \__,_\_|   \__, \_|  |_/\___/ \__,_|\__,_|_|\___|
#   \____/       __/ |                                
#               |___/                                  

# На модуль распространяется лицензия "GNU General Public License v3.0"
# https://github.com/all-licenses/GNU-General-Public-License-v3.0

# meta developer: @pymodule
# meta fhsdesc: tool, tools, ai, username
# requires: aiohttp

import asyncio
import aiohttp
import logging
import re

from telethon import functions
from .. import loader, utils


@loader.tds
class AiUsernameGen(loader.Module):
    """AI-powered username generation and automatic creation of public channels with available usernames. (Before you begin, set up the config: .config AiUsernameGen)"""

    strings = {
        "name": "AiUsernameGen",
        "no_prompt": "🚫 <b>Specify a query to generate a username</b>",
        "checking": "🤖 <b>Generating and checking username availability...</b>",
        "created_many": "✅ <b>Public channels have been created:</b>\n{}",
        "available_many": "✅ <b>Available usernames found (no auto-creation):</b>\n{}",
        "no_free": "😔 <b>No available usernames found. Try a different search!</b>",
        "error_ai": "❌ <b>Error requesting AI. Check your configuration.</b>",
        "config_api_key": "Key API for AI (https://openrouter.ai/settings/keys)",
        "config_model": "Model AI for generation",
        "config_channel_title_prefix": "Prefix for channel title (use {username} to insert username)",
        "config_channel_about": "Channel description",
        "config_autocreate_channels": "Automatically create channels for available usernames (True/False)",
    }

    strings_ru = {
        "_cls_doc": "Генерация username с помощью AI и автоматическое создание публичных каналов с доступными юзернеймами. (Перед началом настройте модуль: .config AiUsernameGen)",
        "no_prompt": "🚫 <b>Укажите запрос для генерации username</b>",
        "checking": "🤖 <b>Генерация и проверка доступности username...</b>",
        "created_many": "✅ <b>Созданы публичные каналы:</b>\n{}",
        "available_many": "✅ <b>Доступные username найдены (автосоздание выключено):</b>\n{}",
        "no_free": "😔 <b>Свободных username не найдено. Попробуйте другой запрос!</b>",
        "error_ai": "❌ <b>Ошибка при запросе к AI. Проверьте конфигурацию.</b>",
        "config_api_key": "Ключ API для AI (https://openrouter.ai/settings/keys)",
        "config_model": "Модель AI для генерации",
        "config_channel_title_prefix": "Префикс для заголовка канала (используйте {username} для вставки username)",
        "config_channel_about": "Описание канала",
        "config_autocreate_channels": "Автоматически создавать каналы с доступными username (True/False)",
    }

    USERNAME_REGEX = re.compile(r'^[a-zA-Z][\w\d]{3,30}[a-zA-Z\d]$')

    SYSTEM_PROMPT = (
        "Ты без дополнительных слов будешь придумывать ровно 10 уникальных username. "
        "Не меньше, не больше! После каждого username делай перенос строки. "
        "Не используй символ @. Условие: username должен состоять из 5 или более символов "
        "и соответствовать паттерну [a-zA-Z][\\w\\d]{3,30}[a-zA-Z\\d]. "
        "Сделай их креативными и релевантными запросу."
    )

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "AI_KEY",
                "your_token_here",
                lambda: self.strings["config_api_key"],
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "MODEL",
                "deepseek/deepseek-r1-0528:free",
                lambda: self.strings["config_model"],
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "CHANNEL_TITLE_PREFIX",
                "Юзернейм: {username}",
                lambda: self.strings["config_channel_title_prefix"],
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "CHANNEL_ABOUT",
                "@pymodule",
                lambda: self.strings["config_channel_about"],
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "AUTOCREATE_CHANNELS",
                True,
                lambda: self.strings["config_autocreate_channels"],
                validator=loader.validators.Boolean()
            )
        )

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

    async def _query_ai(self, prompt: str) -> str | None:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                headers = {
                    "Authorization": f"Bearer {self.config['AI_KEY']}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": self.config["MODEL"],
                    "messages": [
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 150
                }
                async with session.post(self.api_url, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        self.logger.error(f"AI response status: {resp.status} - {await resp.text()}")
                        return None
                    res = await resp.json()
                    if "choices" not in res or not res["choices"]:
                        self.logger.error("Invalid AI response structure")
                        return None
                    return res["choices"][0]["message"]["content"].strip()
        except Exception as e:
            self.logger.error(f"AI request error: {e}")
            return None

    async def _is_username_available(self, username: str) -> bool:
        try:
            return await self.client(functions.account.CheckUsernameRequest(username=username))
        except Exception as e:
            self.logger.error(f"Error checking username '{username}': {e}")
            return False

    async def get_available(self, usernames: list[str]) -> list[str]:
        semaphore = asyncio.Semaphore(10)
        async def check_one(u: str):
            async with semaphore:
                return u if await self._is_username_available(u) else None

        tasks = [check_one(u) for u in usernames]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]

    async def create_channels(self, usernames: list[str]) -> list[str]:
        semaphore = asyncio.Semaphore(3)
        async def create_one(u: str):
            async with semaphore:
                return await self._create_channel_with_username(u)

        tasks = [create_one(u) for u in usernames]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]

    async def _create_channel_with_username(self, username: str) -> str | None:
        title = self.config["CHANNEL_TITLE_PREFIX"].format(username=username)
        about = self.config["CHANNEL_ABOUT"]

        try:
            if not await self._is_username_available(username):
                return None

            result = await self.client(functions.channels.CreateChannelRequest(
                title=title,
                about=about,
                broadcast=True
            ))
            channel = result.chats[0]

            await self.client(functions.channels.UpdateUsernameRequest(
                channel=channel,
                username=username
            ))

            self.logger.info(f"Successfully created channel with username: {username}")
            return username

        except Exception as e:
            self.logger.error(f"Error creating channel for '{username}': {e}")
            try:
                if 'channel' in locals():
                    await self.client(functions.channels.DeleteChannelRequest(channel=channel))
            except:
                pass
            return None

    def _filter_and_validate_usernames(self, ai_text: str) -> list[str]:
        lines = [u.strip() for u in ai_text.splitlines() if u.strip()]
        valid = []
        for u in lines[:10]:
            if len(u) >= 5 and self.USERNAME_REGEX.match(u):
                valid.append(u)
        return valid

    @loader.command(ru_doc="— <запрос> Генерирует username по запросу и (опционально) создаёт каналы")
    async def genusercmd(self, message):
        """— <request> Generates usernames and optionally creates channels"""
        user_query = utils.get_args_raw(message)
        if not user_query:
            return await utils.answer(message, self.strings["no_prompt"])

        msg = await utils.answer(message, self.strings["checking"])

        ai_text = await self._query_ai(user_query)
        if not ai_text:
            return await msg.edit(self.strings["error_ai"])

        usernames = self._filter_and_validate_usernames(ai_text)
        available = await self.get_available(usernames)

        autocreate = self.config["AUTOCREATE_CHANNELS"]
        created = []

        if autocreate and available:
            created = await self.create_channels(available)

        if (autocreate and not created) or (not autocreate and not available):
            retry_prompt = f"{user_query}. Придумай ещё 10 других уникальных username, строго по тем же правилам."
            ai_text_retry = await self._query_ai(retry_prompt)
            if ai_text_retry:
                usernames_retry = self._filter_and_validate_usernames(ai_text_retry)
                available_retry = await self.get_available(usernames_retry)

                if autocreate:
                    created = await self.create_channels(available_retry)
                else:
                    available = available_retry or available

        if autocreate:
            if created:
                channels_list = "\n".join(f"• <code>t.me/{u}</code>" for u in created)
                await msg.edit(self.strings["created_many"].format(channels_list))
            else:
                await msg.edit(self.strings["no_free"])
        else:
            if available:
                avail_list = "\n".join(f"• <code>t.me/{u}</code>" for u in available)
                await msg.edit(self.strings["available_many"].format(avail_list))
            else:
                await msg.edit(self.strings["no_free"])