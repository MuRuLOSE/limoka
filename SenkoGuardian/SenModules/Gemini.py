#  This file is part of SenkoGuardianModules
#  Copyright (c) 2025-2026 Senko
#  This software is released under the MIT License.
#  https://opensource.org/licenses/MIT

# scope heroku_min: 2.0.0
# meta banner: https://raw.githubusercontent.com/SenkoGuardian/SenkoGuardian.github.io/main/OfficialSenkoGuardianBanner.png
# meta pic: https://raw.githubusercontent.com/SenkoGuardian/SenkoGuardian.github.io/main/OfficialSenkoGuardianBanner.png

__version__ = ("6", "3", "0") 

"""￣へ￣"""

# meta developer: @SenkoGuardianModules

#  .------. .------. .------. .------. .------. .------.
#  |S.--. | |E.--. | |N.--. | |M.--. | |O.--. | |D.--. |
#  | :/\: | | :/\: | | :(): | | :/\: | | :/\: | | :/\: |
#  | :\/: | | :\/: | | ()() | | :\/: | | :\/: | | :\/: |
#  | '--'S| | '--'E| | '--'N| | '--'M| | '--'O| | '--'D|
#  `------' `------' `------' `------' `------' `------'

import re
import os
import io
import random
import socket
import base64
import uuid
import json
import asyncio
import logging
import tempfile
import aiohttp
from markdown_it import MarkdownIt
import pytz
import httpx
import pytz

# New SDK Check
try:
    from google import genai
    from google.genai import types
    import google.api_core.exceptions as google_exceptions
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    google_exceptions = None

from PIL import Image
from datetime import datetime
from telethon import types as tg_types
from telethon.tl.types import Message, DocumentAttributeFilename, DocumentAttributeSticker
from telethon.utils import get_display_name, get_peer_id
from telethon.errors.rpcerrorlist import (
    MessageTooLongError, 
    ChatAdminRequiredError,
    UserNotParticipantError, 
    ChannelPrivateError
)

from .. import loader, utils
from ..inline.types import InlineCall

logger = logging.getLogger(__name__)

_gemini_log_client = None
_gemini_log_channel = None
_gemini_log_topic_id = None

class _GeminiTopicHandler(logging.Handler):
    def emit(self, record):
        if _gemini_log_client is None or _gemini_log_channel is None or _gemini_log_topic_id is None:
            return
        try:
            text = f"<code>[{record.levelname}]</code> {self.format(record)}"
            asyncio.ensure_future(
                _gemini_log_client.send_message(
                    int(f"-100{_gemini_log_channel}"),
                    text,
                    parse_mode="html",
                    reply_to=_gemini_log_topic_id,
                )
            )
        except Exception:
            pass

_gemini_topic_handler = _GeminiTopicHandler()
_gemini_topic_handler.setLevel(logging.WARNING)
logger.addHandler(_gemini_topic_handler)

DB_HISTORY_KEY = "gemini_conversations_v4"
DB_GAUTO_HISTORY_KEY = "gemini_gauto_conversations_v1"
DB_IMPERSONATION_KEY = "gemini_impersonation_chats"
DB_PRESETS_KEY = "gemini_prompt_presets"
DB_PAGER_CACHE_KEY = "gemini_pager_cache"
DB_KEY_MAP_KEY = "gemini_key_model_map"
GEMINI_TIMEOUT = 840
MAX_FFMPEG_SIZE = 90 * 1024 * 1024
CHECK_MODEL = "gemini-2.5-pro"  

# requires: google-genai google-api-core pytz markdown_it_py

class Gemini(loader.Module):
    """Модуль для работы с Google Gemini AI. (Поддержка видео/фото/аудио"""
    strings = {
        "name": "Gemini",
        "cfg_api_key_doc": "API ключи Google Gemini, разделенные запятой. Будут скрыты.",
        "cfg_model_name_doc": "Модель Gemini.",
        "cfg_buttons_doc": "Включить интерактивные кнопки.",
        "cfg_system_instruction_doc": "Системная инструкция (промпт) для Gemini.",
        "cfg_max_history_length_doc": "Макс. кол-во пар 'вопрос-ответ' в памяти (0 - без лимита).",
        "cfg_timezone_doc": "Ваш часовой пояс. Список: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones",
        "cfg_proxy_doc": "Прокси для обхода региональных блокировок. Формат: http://user:pass@host:port",
        "cfg_impersonation_prompt_doc": "Промпт для режима авто-ответа. {my_name} и {chat_history} будут заменены.",
        "cfg_impersonation_history_limit_doc": "Сколько последних сообщений из чата отправлять в качестве контекста для авто-ответа.",
        "cfg_impersonation_reply_chance_doc": "Вероятность ответа в режиме gauto (от 0.0 до 1.0). 0.2 = 20% шанс.",
        "cfg_temperature_doc": "Температура генерации (креативность). От 0.0 до 2.0. По умолчанию 1.0.",
        "cfg_google_search_doc": "Включить поиск Google (Grounding) для актуальной информации.",
        "cfg_image_model_doc": "Модель Gemini для генерации изображений (например: gemini-2.5-flash-image).",
        "cfg_inline_pagination_doc": "Использовать инлайн-кнопки для длинных ответов.",
        "no_api_key": (
            '❗️ <b>Api ключ(и) не настроен(ы).</b>\nПолучить Api ключ можно <a href="https://aistudio.google.com/app/apikey">здесь</a>.\n'
            '<b>Добавьте ключ(и) в конфиге модуля:</b> <code>.cfg gemini api_key</code>\n'
            'Так же можно использовать провайдера Openrouter <code>.cfg gemini provider</code>\n'
            'ℹ️ Получить Openrouter ключ можно <a href="https://openrouter.ai/settings/keys">здесь</a>'
        ),
        "no_api_key_Openrouter": '❗️ <b>API ключ для OpenRouter не настроен.</b>\nПолучить ключ можно <a href="https://openrouter.ai/settings/keys">здесь</a>.\n<b>Добавьте ключ в конфиге модуля:</b> <code>.cfg gemini Openrouter_api_key</code>',
        "invalid_api_key_Openrouter": '❗️ <b>Предоставленный API ключ OpenRouter недействителен.</b>\nУбедитесь, что он правильно скопирован из <a href="https://openrouter.ai/settings/keys">OpenRouter</a>.',
        "gmodel_list_title_Openrouter": "📋 <b>Доступные модели OpenRouter:</b>",
        "invalid_api_key": '❗️ <b>Предоставленный API ключ недействителен.</b>\nУбедитесь, что он правильно скопирован из <a href="https://aistudio.google.com/app/apikey">Google AI Studio</a> и что для него включен Gemini API.',
        "all_keys_exhausted": "❗️ <b>Все доступные API ключи ({}) исчерпали свою квоту.</b>\nПопробуйте позже или добавьте новые ключи в конфиге: <code>.cfg gemini api_key</code>",
        "no_prompt_or_media": "⚠️ <i>Нужен текст или ответ на медиа/файл.</i>",
        "processing": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>Обработка...</b>",
        "api_error": "❗️ <b>Ошибка API Google Gemini:</b>\n<code>{}</code>",
        "api_timeout": f"❗️ <b>Таймаут ответа от Gemini API ({GEMINI_TIMEOUT} сек).</b>",
        "blocked_error": "🚫 <b>Запрос/ответ заблокирован.</b>\n<code>{}</code>",
        "generic_error": "❗️ <b>Ошибка:</b>\n<code>{}</code>",
        "question_prefix": "💬 <b>Запрос:</b>",
        "response_prefix": "<emoji document_id=5325547803936572038>✨</emoji> <b>Gemini:</b>",
        "unsupported_media_type": "⚠️ <b>Формат медиа ({}) не поддерживается.</b>",
        "memory_status": "🧠 [{}/{}]",
        "memory_status_unlimited": "🧠 [{}/∞]",
        "memory_cleared": "🧹 <b>Память диалога очищена.</b>",
        "memory_cleared_gauto": "🧹 <b>Память gauto в этом чате очищена.</b>",
        "no_memory_to_clear": "ℹ️ <b>В этом чате нет истории.</b>",
        "no_gauto_memory_to_clear": "ℹ️ <b>В этом чате нет истории gauto.</b>",
        "memory_chats_title": "🧠 <b>Чаты с историей ({}):</b>",
        "memory_chat_line": "  • {} (<code>{}</code>)",
        "no_memory_found": "ℹ️ Память Gemini пуста.",
        "media_reply_placeholder": "[ответ на медиа]",
        "btn_clear": "🧹 Очистить",
        "btn_regenerate": "🔄 Другой ответ",
        "no_last_request": "Последний запрос не найден для повторной генерации.",
        "memory_fully_cleared": "🧹 <b>Вся память Gemini полностью очищена (затронуто {} чатов).</b>",
        "gauto_memory_fully_cleared": "🧹 <b>Вся память gauto полностью очищена (затронуто {} чатов).</b>",
        "no_memory_to_fully_clear": "ℹ️ <b>Память Gemini и так пуста.</b>",
        "no_gauto_memory_to_fully_clear": "ℹ️ <b>Память gauto и так пуста.</b>",
        "response_too_long": "Ответ Gemini был слишком длинным и отправлен в виде файла.",
        "gclear_usage": "ℹ️ <b>Использование:</b> <code>.gclear [auto]</code>",
        "gres_usage": "ℹ️ <b>Использование:</b> <code>.gres [auto]</code>",
        "auto_mode_on": "🎭 <b>Режим авто-ответа включен в этом чате.</b>\nЯ буду отвечать на сообщения с вероятностью {}%.",
        "auto_mode_off": "🎭 <b>Режим авто-ответа выключен в этом чате.</b>",
        "auto_mode_chats_title": "🎭 <b>Чаты с активным авто-ответом ({}):</b>",
        "no_auto_mode_chats": "ℹ️ Нет чатов с включенным режимом авто-ответа.",
        "auto_mode_usage": "ℹ️ <b>Использование:</b> <code>.gauto on/off или[id/username] [on/off]</code>",
        "gauto_chat_not_found": "🚫 <b>Не удалось найти чат:</b> <code>{}</code>",
        "gauto_state_updated": "🎭 <b>Режим авто-ответа для чата {} {}</b>",
        "gauto_enabled": "включен",
        "gauto_disabled": "выключен",
        "gch_usage": "ℹ️ <b>Использование:</b>\n<code>.gch <кол-во> <вопрос></code>\n<code>.gch <id чата> <кол-во> <вопрос></code>",
        "gch_processing": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>Анализирую {} сообщений...</b>",
        "gch_result_caption": "Анализ последних {} сообщений",
        "gch_result_caption_from_chat": "Анализ последних {} сообщений из чата <b>{}</b>",
        "gch_invalid_args": "❗️ <b>Неверные аргументы.</b>\n{}",
        "gch_chat_error": "❗️ <b>Ошибка доступа к чату</b> <code>{}</code>: <i>{}</i>",
        "gmodel_usage": "ℹ️ <b>Использование:</b> <code>.gmodel [модель] [-s]</code>\n• [модель] — установить модель.\n• -s — показать список доступных моделей.",
        "gmodel_list_title": "📋 <b>Доступные модели Gemini (по вашему API):</b>",
        "gmodel_list_item": "• <code>{}</code> — {} (поддержка: {})",
        "gmodel_img_support": "Поддержка изображений",
        "gmodel_no_support": "Нет поддержки изображений",
        "gmodel_img_warn": "⚠️ <b>Текущая модель ({}) не может генерировать изображения(или не доступна по API).</b>\nРекомендуем: <code>gemini-2.5-flash-image</code>",
        "gme_chat_not_found": "🚫 <b>Не удалось найти чат для экспорта:</b> <code>{}</code>",
        "gme_sent_to_saved": "💾 История экспортирована в избранное.",
        "new_sdk_missing": "⚠️ <b>Для работы модуля нужна библиотека google-genai.</b>\nВыполните: <code>pip install google-genai</code>",
        "gprompt_usage": "ℹ️ <b>Использование:</b>\n<code>.gprompt <текст/пресет></code> — установить.\n<code>.gprompt -c</code> — очистить.\n<code>.gpresets</code> — база пресетов.",
        "gprompt_updated": "✅ <b>Системный промпт обновлен!</b>\nДлина: {} символов.",
        "gprompt_cleared": "🗑 <b>Системный промпт очищен.</b>",
        "gprompt_current": "📝 <b>Текущий системный промпт:</b>",
        "gprompt_file_error": "❗️ <b>Ошибка чтения файла:</b> {}",
        "gprompt_file_too_big": "❗️ <b>Файл слишком большой</b> (лимит 1 МБ).",
        "gprompt_not_text": "❗️ Это не похоже на текстовый файл.(txt)",
        "gmodel_no_models": "⚠️ Не удалось получить список моделей.",
        "gmodel_list_error": "❗️ Ошибка получения списка: {}",
        "gimg_process": "<emoji document_id=5325547803936572038>✨</emoji> <b>Генерация...</b>\n🧠 <i>Модель: {model}</i>",
        "gpresets_usage": (
            "ℹ️ <b>Управление пресетами:</b>\n"
            "• <code>.gpresets save [Имя] текст</code> — сохранить (имя в скобках, если с пробелами).\n"
            "• <code>.gpresets load 1</code> или <code>имя</code> — загрузить по номеру/имени.\n"
            "• <code>.gpresets del 1</code> или <code>имя</code> — удалить.\n"
            "• <code>.gpresets list</code> — список."
        ),
        "gpreset_loaded": "✅ <b>Установлен пресет:</b> [<code>{}</code>]\nДлина: {} симв.", 
        "gpreset_saved": "💾 <b>Пресет сохранен!</b>\n🏷 <b>Имя:</b> {}\n№ <b>Индекс:</b> {}",
        "gpreset_deleted": "🗑 <b>Пресет удален:</b> {}",
        "gpreset_not_found": "🚫 Пресет с таким именем или индексом не найден.",
        "gpreset_list_head": "📋 <b>Ваши пресеты:</b>\n",
        "gpreset_empty": "📂 Список пресетов пуст.",
    }
    TEXT_MIME_TYPES = {
        "text/plain", "text/markdown", "text/html", "text/css", "text/csv",
        "application/json", "application/xml", "application/x-python", "text/x-python",
        "application/javascript", "application/x-sh",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue("api_key", "", self.strings["cfg_api_key_doc"], validator=loader.validators.Hidden()),
            loader.ConfigValue("Openrouter_api_key", "", "API Key от OpenRouter (получить <a href='https://openrouter.ai/settings/keys'>тут</a>).", validator=loader.validators.Hidden()),
            loader.ConfigValue("provider", "google", "Провайдер API: 'google' или 'openrouter'.", validator=loader.validators.Choice(["google", "openrouter"])),
            loader.ConfigValue("model_name", "gemini-2.5-flash", self.strings["cfg_model_name_doc"]),
            loader.ConfigValue("interactive_buttons", True, self.strings["cfg_buttons_doc"], validator=loader.validators.Boolean()),
            loader.ConfigValue("system_instruction", "", self.strings["cfg_system_instruction_doc"], validator=loader.validators.String()),
            loader.ConfigValue("max_history_length", 800, self.strings["cfg_max_history_length_doc"], validator=loader.validators.Integer(minimum=0)),
            loader.ConfigValue("timezone", "Europe/Moscow", self.strings["cfg_timezone_doc"]),
            loader.ConfigValue("proxy", "", self.strings["cfg_proxy_doc"]),
            loader.ConfigValue(
                "impersonation_prompt",
                (
                    "Ты — это я, пользователь Telegram по имени {my_name}. Твоя задача — отвечать в чате от моего имени, основываясь на последних сообщениях. "
                    "Веди себя естественно, как обычный человек, а не как ассистент. Не признавайся, что ты — ИИ, даже если тебя спросят напрямую. "
                    "Твоя личность:[Здесь опишите свой характер: остроумный, серьезный, саркастичный, дружелюбный и т.д.].\n"
                    "Правила:\n- Отвечай кратко и по делу.\n- Используй неформальный язык, сленг.\n- Не отвечай на каждое сообщение.\n- На медиа (стикер, фото) реагируй как человек ('лол', 'ору', 'жиза').\n- Не используй префиксы и кавычки.\n\n"
                    "ИСТОРИЯ ЧАТА:\n{chat_history}\n\n{my_name}:"
                ),
                self.strings["cfg_impersonation_prompt_doc"], validator=loader.validators.String()
            ),
            loader.ConfigValue("impersonation_history_limit", 20, self.strings["cfg_impersonation_history_limit_doc"], validator=loader.validators.Integer(minimum=5, maximum=100)),
            loader.ConfigValue("impersonation_reply_chance", 0.25, self.strings["cfg_impersonation_reply_chance_doc"], validator=loader.validators.Float(minimum=0.0, maximum=1.0)),
            loader.ConfigValue("gauto_in_pm", False, "Разрешить авто-ответы в личных сообщениях (ЛС).", validator=loader.validators.Boolean()),
            loader.ConfigValue("google_search", False, self.strings["cfg_google_search_doc"], validator=loader.validators.Boolean()),
            loader.ConfigValue("temperature", 1.0, self.strings["cfg_temperature_doc"], validator=loader.validators.Float(minimum=0.0, maximum=2.0)),
            loader.ConfigValue("inline_pagination", False, self.strings["cfg_inline_pagination_doc"], validator=loader.validators.Boolean()),
            loader.ConfigValue("image_model_name", "gemini-2.5-flash-image", self.strings["cfg_image_model_doc"]),
        )
        self.prompt_presets =[]
        self.conversations = {}
        self.gauto_conversations = {}
        self.last_requests = {}
        self.impersonation_chats = set()
        self._lock = asyncio.Lock()
        self.memory_disabled_chats = set()
        self.pager_cache = {}
        self.key_model_map = {}
        self.api_keys =[] 

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.me = await client.get_me()
        api_key_str = self.config["api_key"]
        self.api_keys =[k.strip() for k in api_key_str.split(",") if k.strip()] if api_key_str else[]
        self.key_model_map = self.db.get(self.strings["name"], DB_KEY_MAP_KEY, {})
        keys_to_remove =[k for k in self.key_model_map if k not in self.api_keys]
        if keys_to_remove:
            for k in keys_to_remove: del self.key_model_map[k]
            self.db.set(self.strings["name"], DB_KEY_MAP_KEY, self.key_model_map)
        if not GOOGLE_AVAILABLE:
            logger.error("Gemini: 'google-genai' library missing! pip install google-genai")
            return
        self.current_api_key_index = 0
        self.conversations = self._load_history_from_db(DB_HISTORY_KEY)
        self.prompt_presets = self.db.get(self.strings["name"], DB_PRESETS_KEY, [])
        if isinstance(self.prompt_presets, dict):
            self.prompt_presets =[{"name": k, "content": v} for k, v in self.prompt_presets.items()]
        self.gauto_conversations = self._load_history_from_db(DB_GAUTO_HISTORY_KEY)
        self.impersonation_chats = set(self.db.get(self.strings["name"], DB_IMPERSONATION_KEY,[]))
        self.pager_cache = self.db.get(self.strings["name"], DB_PAGER_CACHE_KEY, {})
        if not self.api_keys:
            logger.warning("Gemini: API ключи не настроены.")
        global _gemini_log_client, _gemini_log_channel, _gemini_log_topic_id
        try:
            asset_channel = self._db.get("heroku.forums", "channel_id", 0)
            if asset_channel:
                notif_topic = await utils.asset_forum_topic(
                    self._client,
                    self._db,
                    asset_channel,
                    "Gemini Logs",
                    description="Gemini module warnings & errors.",
                    icon_emoji_id=5325547803936572038,
                )
                _gemini_log_client = self._client
                _gemini_log_channel = asset_channel
                _gemini_log_topic_id = notif_topic.id
        except Exception:
            pass

    async def _prepare_parts(self, message: Message, custom_text: str=None):
        final_parts, warnings = [], []
        prompt_text_chunks =[]
        user_args = custom_text if custom_text is not None else utils.get_args_raw(message)
        try:
            chat = await message.get_chat()
            chat_title = getattr(chat, 'title', getattr(chat, 'first_name', 'Личные сообщения'))
        except Exception:
            chat_title = "Неизвестный чат"
        prompt_text_chunks.append(f"[System info: We are in '{chat_title}' chat]")
        reply = await message.get_reply_message()
        if reply and getattr(reply, "text", None):
            try:
                reply_sender = await reply.get_sender()
                reply_author_name = get_display_name(reply_sender) if reply_sender else "Unknown"
                prompt_text_chunks.append(f"{reply_author_name}: {reply.text}")
            except Exception: 
                prompt_text_chunks.append(f"Ответ на: {reply.text}")
        try:
            current_sender = await message.get_sender()
            current_user_name = get_display_name(current_sender) if current_sender else "User"
            prompt_text_chunks.append(f"{current_user_name}: {user_args or ''}")
        except Exception: 
            prompt_text_chunks.append(f"Запрос: {user_args or ''}")
        media_source = message if message.media or message.sticker else reply
        has_media = bool(media_source and (media_source.media or media_source.sticker))
        if has_media:
            if media_source.sticker and hasattr(media_source.sticker, 'mime_type') and media_source.sticker.mime_type=='application/x-tgsticker':
                alt_text = next((attr.alt for attr in media_source.sticker.attributes if isinstance(attr, DocumentAttributeSticker)), "?")
                prompt_text_chunks.append(f"[Анимированный стикер: {alt_text}]")
            else:
                media, mime_type, filename = media_source.media, "application/octet-stream", "file"
                if media_source.photo: 
                    mime_type = "image/jpeg"
                elif hasattr(media_source, "document") and media_source.document:
                    mime_type = getattr(media_source.document, "mime_type", mime_type)
                    doc_attr = next((attr for attr in media_source.document.attributes if isinstance(attr, DocumentAttributeFilename)), None)
                    if doc_attr: filename = doc_attr.file_name
                    
                async def get_bytes(m):
                    bio = io.BytesIO()
                    await self.client.download_media(m, bio)
                    return bio.getvalue()
                    
                if mime_type.startswith("image/"):
                    try:
                        data = await get_bytes(media)
                        final_parts.append(types.Part(inline_data=types.Blob(mime_type=mime_type, data=data)))
                    except Exception as e: warnings.append(f"⚠️ Ошибка обработки изображения '{filename}': {e}")
                elif mime_type in self.TEXT_MIME_TYPES or filename.split('.')[-1] in ('txt', 'py', 'js', 'json', 'md', 'html', 'css', 'sh'):
                    try:
                        data = await get_bytes(media)
                        file_content = data.decode('utf-8')
                        prompt_text_chunks.insert(0, f"[Содержимое файла '{filename}']: \n```\n{file_content}\n```")
                    except Exception as e: warnings.append(f"⚠️ Ошибка чтения файла '{filename}': {e}")
                elif mime_type.startswith("audio/"):
                    input_path, output_path = None, None
                    try:
                        with tempfile.NamedTemporaryFile(suffix=f".{filename.split('.')[-1]}", delete=False) as temp_in: input_path = temp_in.name
                        await self.client.download_media(media, input_path)
                        if os.path.getsize(input_path) > MAX_FFMPEG_SIZE:
                            warnings.append(f"⚠️ Аудиофайл '{filename}' слишком большой."); raise StopIteration
                        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_out: output_path = temp_out.name
                        ffmpeg_cmd =["ffmpeg", "-y", "-i", input_path, "-c:a", "libmp3lame", "-q:a", "2", output_path]
                        process_ffmpeg = await asyncio.create_subprocess_exec(*ffmpeg_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                        await process_ffmpeg.communicate()
                        if process_ffmpeg.returncode != 0: raise Exception("FFmpeg error")
                        with open(output_path, "rb") as f:
                            final_parts.append(types.Part(inline_data=types.Blob(mime_type="audio/mpeg", data=f.read())))
                    except StopIteration: pass
                    except Exception as e: warnings.append(f"⚠️ Ошибка обработки аудио: {e}")
                    finally:
                        if input_path and os.path.exists(input_path): os.remove(input_path)
                        if output_path and os.path.exists(output_path): os.remove(output_path)
                elif mime_type.startswith("video/"):
                    input_path, output_path = None, None
                    try:
                        with tempfile.NamedTemporaryFile(suffix=f".{filename.split('.')[-1]}", delete=False) as temp_in: input_path = temp_in.name
                        await self.client.download_media(media, input_path)
                        if os.path.getsize(input_path) > MAX_FFMPEG_SIZE:
                            warnings.append(f"⚠️ Медиафайл '{filename}' слишком большой."); raise StopIteration
                        ffprobe_cmd =["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_type", "-of", "default=noprint_wrappers=1:nokey=1", input_path]
                        process_probe = await asyncio.create_subprocess_exec(*ffprobe_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                        stdout, _ = await process_probe.communicate()
                        has_audio = bool(stdout.strip())
                        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_out: output_path = temp_out.name
                        ffmpeg_cmd =["ffmpeg", "-y", "-i", input_path]
                        maps = ["-map", "0:v:0"]
                        if not has_audio:
                            ffmpeg_cmd.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"])
                            maps.extend(["-map", "1:a:0"])
                        else:
                            maps.extend(["-map", "0:a:0?"])
                        ffmpeg_cmd.extend([*maps, "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-shortest", output_path])
                        process_ffmpeg = await asyncio.create_subprocess_exec(*ffmpeg_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                        _, stderr = await process_ffmpeg.communicate()
                        if process_ffmpeg.returncode != 0:
                            stderr_str = stderr.decode()
                            warnings.append(f"⚠️ <b>Ошибка FFmpeg:</b>\nНе удалось конвертировать '{filename}'. Детали:\n<code>{utils.escape_html(stderr_str)}</code>")
                            raise StopIteration
                        with open(output_path, "rb") as f:
                            final_parts.append(types.Part(inline_data=types.Blob(mime_type="video/mp4", data=f.read())))
                    except StopIteration: pass
                    except Exception as e: warnings.append(f"⚠️ Ошибка обработки видео: {e}")
                    finally:
                        if input_path and os.path.exists(input_path): os.remove(input_path)
                        if output_path and os.path.exists(output_path): os.remove(output_path)
                        
        if not user_args and has_media and not final_parts and not any("[Содержимое файла" in chunk for chunk in prompt_text_chunks):
            prompt_text_chunks.append(self.strings["media_reply_placeholder"])
        full_prompt_text = "\n".join(chunk for chunk in prompt_text_chunks if chunk and chunk.strip()).strip()
        if full_prompt_text:
            final_parts.insert(0, types.Part(text=full_prompt_text))
        return final_parts, warnings

    async def _send_to_gemini(self, message, parts: list, regeneration: bool=False, call: InlineCall=None, status_msg=None, chat_id_override: int=None, impersonation_mode: bool=False, use_url_context: bool=False, display_prompt: str=None): 
        msg_obj = None
        if regeneration:
            chat_id = chat_id_override; base_message_id = message
            try: msg_obj = await self.client.get_messages(chat_id, ids=base_message_id)
            except Exception: msg_obj = None
        else:
            chat_id = utils.get_chat_id(message); base_message_id = message.id; msg_obj = message
        target_model = self.config["model_name"]
        if self.config["provider"] == "openrouter":
            if regeneration:
                current_turn_parts, request_text_for_display = self.last_requests.get(f"{chat_id}:{base_message_id}", (parts, "[регенерация]"))
            else:
                current_turn_parts = parts
                user_text_from_parts = " ".join([p.text for p in parts if hasattr(p, "text") and p.text])
                request_text_for_display = display_prompt or user_text_from_parts or "[медиа-запрос]"
                self.last_requests[f"{chat_id}:{base_message_id}"] = (current_turn_parts, request_text_for_display)
            try:
                sys_instruct = self.config["system_instruction"] or None
                if impersonation_mode:
                    my_name = get_display_name(self.me)
                    chat_history_text = await self._get_recent_chat_text(chat_id)
                    sys_instruct = self.config["impersonation_prompt"].format(my_name=my_name, chat_history=chat_history_text)
                
                raw_hist = self._get_structured_history(chat_id, gauto=impersonation_mode)
                if regeneration and raw_hist: raw_hist = raw_hist[:-2]
                openai_messages = self._convert_google_history_to_openai(raw_hist, sys_instruct)
                content_list =[]
                for p in current_turn_parts:
                    if hasattr(p, "text") and p.text:
                        content_list.append({"type": "text", "text": p.text})
                    elif hasattr(p, "inline_data") and p.inline_data:
                         mime = p.inline_data.mime_type
                         data = p.inline_data.data
                         if mime.startswith("image/"):
                             b64_img = base64.b64encode(data).decode("utf-8")
                             content_list.append({
                                 "type": "image_url", 
                                 "image_url": {"url": f"data:{mime};base64,{b64_img}"}
                             })
                if not content_list:
                    content_list = request_text_for_display
                openai_messages.append({"role": "user", "content": content_list})
                result_text = await self._send_to_Openrouter_api(target_model, openai_messages, self.config["temperature"])
                result_text = result_text.strip()
                result_text = re.sub(r"^\[System Info:.*?\]\s*", "", result_text, flags=re.IGNORECASE)
                result_text = re.sub(r"^\[\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}\]\s*(?:Gemini:|Model:|Ассистент:|AI:)?\s*", "", result_text, flags=re.IGNORECASE)
                result_text = re.sub(r"^\[\d{2}:\d{2}\]\s*(?:Gemini:|Model:|Ассистент:|AI:)?\s*", "", result_text, flags=re.IGNORECASE)
                if self._is_memory_enabled(str(chat_id)):
                    self._update_history(chat_id, current_turn_parts, result_text, regeneration, msg_obj, gauto=impersonation_mode)
                if impersonation_mode: return result_text
                hist_len = len(self._get_structured_history(chat_id)) // 2
                max_hist = self.config["max_history_length"]
                if max_hist <= 0:
                    mem_indicator = self.strings["memory_status_unlimited"].format(hist_len)
                else:
                    mem_indicator = self.strings["memory_status"].format(hist_len, max_hist)
                model_info = f"<i>OpenRouter: <code>{target_model}</code></i>"
                response_html = self._markdown_to_html(result_text)
                formatted_body = self._format_response_with_smart_separation(response_html)
                question_html = f"<blockquote>{utils.escape_html(request_text_for_display[:200])}</blockquote>"
                text_to_send = f"{mem_indicator}\n{model_info}\n\n{self.strings['question_prefix']}\n{question_html}\n\n{self.strings['response_prefix']}\n{formatted_body}"
                if call or self.config["interactive_buttons"]:
                    text_to_send = text_to_send.replace('<emoji document_id=', '<tg-emoji emoji-id=').replace('</emoji>', '</tg-emoji>')
                buttons = self._get_inline_buttons(chat_id, base_message_id) if self.config["interactive_buttons"] else None
                if len(text_to_send) > 4096:
                    file = io.BytesIO(result_text.encode("utf-8")); file.name = "Gemini_response.txt"
                    if call: await self.client.send_file(call.chat_id, file, caption="Response too long", reply_to=call.message_id)
                    elif status_msg: 
                        await status_msg.delete()
                        await self.client.send_file(chat_id, file, caption="Response too long", reply_to=base_message_id)
                else:
                    if call: await call.edit(text_to_send, reply_markup=buttons)
                    elif status_msg: await utils.answer(status_msg, text_to_send, reply_markup=buttons)
                return ""
            except Exception as e:
                error_text = self._handle_error(e)
                if impersonation_mode: logger.error(f"Gauto/Openrouter error: {error_text}")
                elif call: await call.edit(error_text)
                elif status_msg: await utils.answer(status_msg, error_text)
                return None
        api_keys_to_use = self._get_sorted_keys()
        if not api_keys_to_use:
            if not impersonation_mode and status_msg: await utils.answer(status_msg, self.strings['no_api_key'])
            return None if impersonation_mode else ""
        if regeneration:
            current_turn_parts, request_text_for_display = self.last_requests.get(f"{chat_id}:{base_message_id}", (parts, "[регенерация]"))
        else:
            current_turn_parts = parts
            request_text_for_display = display_prompt or (self.strings["media_reply_placeholder"] if any(getattr(p, 'inline_data', None) for p in parts) else "")
            self.last_requests[f"{chat_id}:{base_message_id}"] = (current_turn_parts, request_text_for_display)
        result_text = ""
        last_error = None
        was_successful = False
        search_icon = ""
        max_retries = len(api_keys_to_use)
        if impersonation_mode:
            my_name = get_display_name(self.me)
            chat_history_text = await self._get_recent_chat_text(chat_id)
            sys_instruct = self.config["impersonation_prompt"].format(my_name=my_name, chat_history=chat_history_text)
        else:
            sys_val = self.config["system_instruction"]
            sys_instruct = (sys_val.strip() if isinstance(sys_val, str) else "") or None
        contents =[]
        raw_hist = self._get_structured_history(chat_id, gauto=impersonation_mode)
        if regeneration and raw_hist: raw_hist = raw_hist[:-2]
        try: 
            user_tz = pytz.timezone(self.config["timezone"])
        except pytz.UnknownTimeZoneError: 
            user_tz = pytz.utc
        for item in raw_hist:
            content_text = item.get('content', '')
            if 'date' in item and item['date']:
                dt = datetime.fromtimestamp(item['date'], user_tz)
                content_text = f"[{dt.strftime('%d.%m.%Y %H:%M')}] {content_text}"
            contents.append(types.Content(role=item['role'], parts=[types.Part(text=content_text)]))
        request_parts = list(current_turn_parts)
        if not impersonation_mode:
            try: user_timezone = pytz.timezone(self.config["timezone"])
            except pytz.UnknownTimeZoneError: user_timezone = pytz.utc
            now = datetime.now(user_timezone)
            time_note = f"[System Info: Current local time is {now.strftime('%Y-%m-%d %H:%M:%S %Z')}]"
            if request_parts and getattr(request_parts[0], 'text', None):
                request_parts[0] = types.Part(text=f"{time_note}\n\n{request_parts[0].text}")
            else:
                request_parts.insert(0, types.Part(text=time_note))
        contents.append(types.Content(role="user", parts=request_parts))
        tools = []
        if self.config["google_search"] or use_url_context:
            tools.append(types.Tool(google_search=types.GoogleSearch()))
        gen_config = types.GenerateContentConfig(
            temperature=self.config["temperature"],
            system_instruction=sys_instruct,
            tools=tools if tools else None,
            safety_settings=[
                types.SafetySetting(category=cat, threshold="BLOCK_NONE") 
                for cat in["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]
            ]
        )
        proxy_config = self._get_proxy_config()
        for i in range(max_retries):
            api_key = api_keys_to_use[i]
            try:
                http_opts = None
                if proxy_config:
                    http_opts = types.HttpOptions(async_client_args={"proxies": proxy_config})
                client = genai.Client(api_key=api_key, http_options=http_opts)
                response = await client.aio.models.generate_content(
                    model=target_model,
                    contents=contents,
                    config=gen_config
                )
                if response.text:
                    result_text = response.text
                    result_text = result_text.strip()
                    result_text = re.sub(r"^\[System Info:.*?\]\s*", "", result_text, flags=re.IGNORECASE)
                    result_text = re.sub(r"^\[\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}\]\s*(?:Gemini:|Model:|Ассистент:|AI:)?\s*", "", result_text, flags=re.IGNORECASE)
                    result_text = re.sub(r"^\[\d{2}:\d{2}\]\s*(?:Gemini:|Model:|Ассистент:|AI:)?\s*", "", result_text, flags=re.IGNORECASE)
                    was_successful = True
                    if self.config["google_search"]: search_icon = " 🌐"
                    break
                else: raise ValueError("Empty response")
            except Exception as e:
                err_str = str(e).lower()
                if any(x in err_str for x in["quota", "exhausted", "429", "permission_denied", "blocked", "403", "client application", "bad request", "400", "INVALID_ARGUMENT"]):
                     if i == max_retries - 1: last_error = RuntimeError(f"All keys exhausted or blocked. Last: {e}")
                     continue
                else:
                    last_error = e
                    break
        try:
            if not was_successful: raise last_error or RuntimeError("Unknown generation error")
            if self._is_memory_enabled(str(chat_id)):
                self._update_history(chat_id, current_turn_parts, result_text, regeneration, msg_obj, gauto=impersonation_mode)
            if impersonation_mode: return result_text
            hist_len_pairs = len(self._get_structured_history(chat_id, gauto=False)) // 2
            max_hist = self.config["max_history_length"]
            if max_hist <= 0:
                mem_indicator = self.strings["memory_status_unlimited"].format(hist_len_pairs)
            else:
                mem_indicator = self.strings["memory_status"].format(hist_len_pairs, max_hist)
            model_info = f"<i>Модель: <code>{self.config['model_name']}</code></i>"
            is_long_text = len(result_text) > 3500
            if is_long_text and self.config["inline_pagination"]:
                chunks = self._paginate_text(result_text, 3000)
                uid = uuid.uuid4().hex[:6]
                header = f"{mem_indicator}\n{model_info}\n{self.strings['question_prefix']} <blockquote>{utils.escape_html(request_text_for_display[:100])}...</blockquote>\n\n{self.strings['response_prefix']}{search_icon}\n"
                self.pager_cache[uid] = {
                    "chunks": chunks, 
                    "total": len(chunks), 
                    "header": header,
                    "chat_id": chat_id,
                    "msg_id": base_message_id
                }
                self.db.set(self.strings["name"], DB_PAGER_CACHE_KEY, self.pager_cache)
                await self._render_page(uid, 0, call or status_msg)
            elif len(result_text) > 4096:
                 file = io.BytesIO(f"Q: {display_prompt}\nA:\n{result_text}".encode("utf-8")); file.name = "response.txt"
                 if call:
                    await call.answer("File...", show_alert=False)
                    await self.client.send_file(call.chat_id, file, caption=self.strings["response_too_long"], reply_to=call.message_id)
                 elif status_msg:
                    await status_msg.delete()
                    await self.client.send_file(chat_id, file, caption=self.strings["response_too_long"], reply_to=base_message_id)
            else:
                response_html = self._markdown_to_html(result_text)
                formatted_body = self._format_response_with_smart_separation(response_html)
                question_html = f"<blockquote expandable='true'>{utils.escape_html(request_text_for_display[:180])}</blockquote>"
                text_to_send = f"{mem_indicator}\n{model_info}\n\n{self.strings['question_prefix']}\n{question_html}\n\n{self.strings['response_prefix']}{search_icon}\n{formatted_body}"
                if call or self.config["interactive_buttons"]:
                    text_to_send = text_to_send.replace('<emoji document_id=', '<tg-emoji emoji-id=').replace('</emoji>', '</tg-emoji>')
                buttons = self._get_inline_buttons(chat_id, base_message_id) if self.config["interactive_buttons"] else None
                if call: await call.edit(text_to_send, reply_markup=buttons)
                elif status_msg: await utils.answer(status_msg, text_to_send, reply_markup=buttons)
        except Exception as e:
            error_text = self._handle_error(e)
            if impersonation_mode: logger.error(f"Gauto error: {error_text}")
            elif call: await call.edit(error_text, reply_markup=None)
            elif status_msg: await utils.answer(status_msg, error_text)
        return None if impersonation_mode else ""

    @loader.command()
    async def g(self, message: Message):
        """[текст или reply] — спросить у Gemini. Может анализировать ссылки."""
        clean_args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        use_url_context = False
        text_to_check = clean_args
        if reply and getattr(reply, "text", None):
            text_to_check += " " + reply.text
        if re.search(r'https?://\S+', text_to_check): use_url_context = True
        status_msg = await utils.answer(message, self.strings["processing"])
        status_msg = await self.client.get_messages(status_msg.chat_id, ids=status_msg.id)
        parts, warnings = await self._prepare_parts(message, custom_text=clean_args)
        if warnings and status_msg:
            try: await status_msg.edit(f"{status_msg.text}\n\n" + "\n".join(warnings))
            except: pass
        if not parts:
            if status_msg: await utils.answer(status_msg, self.strings["no_prompt_or_media"])
            return
        await self._send_to_gemini(
            message=message, parts=parts, status_msg=status_msg, 
            use_url_context=use_url_context, display_prompt=clean_args or None
        )

    @loader.command()
    async def gimg(self, message: Message):
        """<промпт> [реплай на фото] — Генерация/Редактирование изображений через Gemini."""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        input_bytes = None
        if reply:
            if reply.photo:
                input_bytes = await self.client.download_media(reply, bytes)
            elif reply.document and reply.document.mime_type.startswith("image/"):
                input_bytes = await self.client.download_media(reply, bytes)
        if not args and not input_bytes:
            return await utils.answer(message, "🎨 <b>Введите промпт.</b>\nПример: <code>.gimg кот в космосе</code>")
        prompt = args if args else "Describe/Modify this image"
        model = self.config["image_model_name"]
        m = await utils.answer(message, self.strings["gimg_process"].format(model=model))
        try:
            res = await self._call_google_rest(model, prompt, input_bytes)
            if "error" in res:
                err_msg = res["error"]["message"]
                try: err_msg = json.loads(err_msg)["error"]["message"]
                except: pass
                raise ValueError(err_msg)
            img_bytes = None
            if "candidates" not in res or not res["candidates"]:
                raise ValueError("API вернул пустой ответ (нет candidates).")
            candidate = res["candidates"][0]
            if "content" not in candidate:
                reason = candidate.get("finishReason", "Unknown")
                raise ValueError(f"Модель отказалась генерировать. Причина: {reason} (вероятно, Safety Filter)")
            try:
                parts = candidate["content"].get("parts",[])
                for part in parts:
                    if "inlineData" in part:
                        img_bytes = base64.b64decode(part["inlineData"]["data"])
                        break
            except Exception as e:
                raise ValueError(f"Ошибка чтения данных картинки: {e}")
            if not img_bytes:
                raise ValueError("Модель не вернула изображение (возможно, сработал Safety Filter).")
            out = io.BytesIO(img_bytes)
            out.name = f"gemini_{uuid.uuid4().hex[:6]}.jpg"
            await self.client.send_file(
                utils.get_chat_id(message),
                out,
                caption=f"🎨 <b>Gemini Image</b>\n🧠 <code>{model}</code>\n📜 <code>{utils.escape_html(prompt[:100])}</code>",
                reply_to=message.id
            )
            await m.delete()
        except Exception as e:
            await utils.answer(m, f"❌ <b>Ошибка:</b>\n<code>{utils.escape_html(str(e))}</code>")

    @loader.command()
    async def gskey(self, message: Message):
        """[-h] — Сканировать ключи. -h: показать статус из кеша без проверки."""
        args = utils.get_args_raw(message).strip()
        if args in ["-h", "--having", "having"]:
            premium = sum(1 for v in self.key_model_map.values() if v == 1)
            free = sum(1 for v in self.key_model_map.values() if v == 0)
            report = (
                f"📊 <b>Статус ключей (кеш):</b>\n"
                f"💎 <b>Premium/Active:</b> {premium}\n"
                f"👻 <b>Free/Unknown:</b> {free}\n"
                f"🔑 <b>Всего в конфиге:</b> {len(self.api_keys)}"
            )
            return await utils.answer(message, report)
        await utils.answer(message, "<emoji document_id=5386367538735104399>⌛️</emoji> <b>Сканирую ключи...</b>\n<i>Это займет время (1.2 сек на ключ).</i>")
        report, invalid_keys = await self._scan_keys(force=True)
        if invalid_keys:
            txt_keys = "\n".join(invalid_keys)
            try:
                await self.client.send_message("me", f"🚫 <b>Gemini: Найдены невалидные ключи:</b>\nУдали их из конфига:\n\n<code>{txt_keys}</code>")
                report += "\n\n⚠️ <b>Список невалидных ключей отправлен в Избранное.</b>"
            except:
                report += "\n\n⚠️ <b>Найдены невалидные ключи.</b>"
        await utils.answer(message, report)

    @loader.command()
    async def gch(self, message: Message):
        """<[id чата]> <кол-во> <вопрос> - Проанализировать историю чата."""
        args_str = utils.get_args_raw(message)
        if not args_str: return await utils.answer(message, self.strings["gch_usage"])
        parts = args_str.split()
        target_chat_id = utils.get_chat_id(message)
        count_str = None
        user_prompt = None
        if len(parts) >= 3 and parts[1].isdigit():
            try:
                entity_arg = int(parts[0]) if parts[0].lstrip('-').isdigit() else parts[0]
                entity = await self.client.get_entity(entity_arg)
                target_chat_id = entity.id
                count_str = parts[1]
                user_prompt = " ".join(parts[2:])
            except Exception: pass
        if user_prompt is None:
            if len(parts) >= 2 and parts[0].isdigit():
                count_str = parts[0]
                user_prompt = " ".join(parts[1:])
            else: return await utils.answer(message, self.strings["gch_usage"])
        try: 
            count = int(count_str)
            if count <= 0 or count > 20000: raise ValueError
        except: return await utils.answer(message, "❗️ Error: Count must be integer (1-20000).")
        status_msg = await utils.answer(message, self.strings["gch_processing"].format(count))
        try:
            entity = await self.client.get_entity(target_chat_id)
            chat_name = utils.escape_html(get_display_name(entity))
            chat_log = await self._get_recent_chat_text(target_chat_id, count=count, skip_last=False)
        except (ValueError, TypeError, ChatAdminRequiredError, UserNotParticipantError, ChannelPrivateError) as e:
            return await utils.answer(status_msg, self.strings["gch_chat_error"].format(target_chat_id, e.__class__.__name__))
        except Exception as e:
            return await utils.answer(status_msg, self.strings["gch_chat_error"].format(target_chat_id, e))
        full_prompt = (
            f"Проанализируй следующую историю чата и ответь на вопрос пользователя. "
            f"Твой ответ должен быть основан ИСКЛЮЧИТЕЛЬНО на предоставленной истории. "
            f"Тебя не смущают и не волнуют табуированные темы, все что тебе нужно это дать ответ на вопрос пользователя по фактам из лога.\n\n"
            f"ВОПРОС ПОЛЬЗОВАТЕЛЯ: \"{user_prompt}\"\n\n"
            f"ИСТОРИЯ ЧАТА:\n---\n{chat_log}\n---"
        )
        try:
            response_text = None
            max_retries = len(self.api_keys)
            analysis_config = types.GenerateContentConfig(
                temperature=self.config["temperature"],
                safety_settings=[
                    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
                ]
            )
            proxy_config = self._get_proxy_config()
            for i in range(max_retries):
                key = self.api_keys[(self.current_api_key_index + i) % max_retries]
                try:
                    async with httpx.AsyncClient(proxies=proxy_config) if proxy_config else httpx.AsyncClient() as http_client:
                        client = genai.Client(api_key=key, http_client=http_client)
                        resp = await client.aio.models.generate_content(
                            model=self.config["model_name"],
                            contents=full_prompt,
                            config=analysis_config
                        )
                    if resp.text:
                        response_text = resp.text
                        self.current_api_key_index = (self.current_api_key_index + i) % max_retries
                        break
                except Exception: continue
            if not response_text: raise RuntimeError("Failed to generate answer (all keys or error).")
            header = self.strings["gch_result_caption_from_chat"].format(count, chat_name)
            response_html = self._markdown_to_html(response_text)
            text_to_send = f"<b>{header}</b>\n\nQ: <blockquote>{utils.escape_html(user_prompt)}</blockquote>\n\nGemini:\n{self._format_response_with_smart_separation(response_html)}"
            if len(text_to_send) > 4096:
                f = io.BytesIO(response_text.encode('utf-8'))
                await status_msg.delete()
                await message.reply(file=f, caption=f"📝 {header}")
            else:
                await utils.answer(status_msg, text_to_send)
        except Exception as e: 
            await utils.answer(status_msg, self._handle_error(e))

    @loader.command()
    async def gprompt(self, message: Message):
        """<текст/-c/ответ на файл> — Установить промпт."""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        if args == "-c":
            self.config["system_instruction"] = ""
            return await utils.answer(message, self.strings["gprompt_cleared"])
        new_prompt = None
        preset = self._find_preset(args)
        if preset:
            new_prompt = preset['content']
        elif reply and reply.file:
            if reply.file.size > 1024 * 1024:
                return await utils.answer(message, self.strings["gprompt_file_too_big"])
            try:
                file_data = await self.client.download_file(reply.media, bytes)
                try: new_prompt = file_data.decode("utf-8")
                except UnicodeDecodeError: return await utils.answer(message, self.strings["gprompt_not_text"])
            except Exception as e:
                return await utils.answer(message, self.strings["gprompt_file_error"].format(e))
        elif args:
            new_prompt = args
        if new_prompt is not None:
            self.config["system_instruction"] = new_prompt
            return await utils.answer(message, self.strings["gprompt_updated"].format(len(new_prompt)))
        current_prompt = self.config["system_instruction"]
        if not current_prompt:
            return await utils.answer(message, self.strings["gprompt_usage"])
        if len(current_prompt) > 4000:
            file = io.BytesIO(current_prompt.encode("utf-8"))
            file.name = "system_instruction.txt"
            await utils.answer(message, self.strings["gprompt_current"], file=file)
        else:
            await utils.answer(message, f"{self.strings['gprompt_current']}\n<code>{utils.escape_html(current_prompt)}</code>")

    @loader.command()
    async def gauto(self, message: Message):
        """<on/off/[id]> — Вкл/выкл авто-ответ в чате."""
        args = utils.get_args_raw(message).split()
        if not args: return await utils.answer(message, self.strings["auto_mode_usage"])
        chat_id = utils.get_chat_id(message)
        state = args[0].lower()
        target = chat_id
        if len(args) == 2:
            try:
                e = await self.client.get_entity(args[0])
                target = e.id
                state = args[1].lower()
            except: return await utils.answer(message, self.strings["gauto_chat_not_found"].format(args[0]))
        if state == "on":
            self.impersonation_chats.add(target)
            self.db.set(self.strings["name"], DB_IMPERSONATION_KEY, list(self.impersonation_chats))
            txt = self.strings["auto_mode_on"].format(int(self.config["impersonation_reply_chance"]*100)) if target==chat_id else self.strings["gauto_state_updated"].format(f"<code>{target}</code>", self.strings["gauto_enabled"])
            await utils.answer(message, txt)
        elif state == "off":
            self.impersonation_chats.discard(target)
            self.db.set(self.strings["name"], DB_IMPERSONATION_KEY, list(self.impersonation_chats))
            txt = self.strings["auto_mode_off"] if target==chat_id else self.strings["gauto_state_updated"].format(f"<code>{target}</code>", self.strings["gauto_disabled"])
            await utils.answer(message, txt)
        else: await utils.answer(message, self.strings["auto_mode_usage"])

    @loader.command()
    async def gautochats(self, message: Message):
        """— Показать чаты с активным режимом авто-ответа."""
        if not self.impersonation_chats: return await utils.answer(message, self.strings["no_auto_mode_chats"])
        out = [self.strings["auto_mode_chats_title"].format(len(self.impersonation_chats))]
        for cid in self.impersonation_chats:
            try:
                e = await self.client.get_entity(cid)
                name = utils.escape_html(get_display_name(e))
                out.append(self.strings["memory_chat_line"].format(name, cid))
            except: out.append(self.strings["memory_chat_line"].format("Неизвестный чат", cid))
        await utils.answer(message, "\n".join(out))

    @loader.command()
    async def gclear(self, message: Message):
        """[auto] — очистить память в чате. auto для памяти gauto."""
        args = utils.get_args_raw(message).lower()
        chat_id = utils.get_chat_id(message)
        if args == "auto":
            if str(chat_id) in self.gauto_conversations:
                self._clear_history(chat_id, gauto=True)
                await utils.answer(message, self.strings["memory_cleared_gauto"])
            else:
                await utils.answer(message, self.strings["no_gauto_memory_to_clear"])
            return
        if str(chat_id) in self.conversations:
            self._clear_history(chat_id)
            keys_to_del =[k for k, v in self.pager_cache.items() if v.get("chat_id") == chat_id]
            for k in keys_to_del: del self.pager_cache[k]
            if keys_to_del: self.db.set(self.strings["name"], DB_PAGER_CACHE_KEY, self.pager_cache)
            await utils.answer(message, self.strings["memory_cleared"])
        else:
            await utils.answer(message, self.strings["no_memory_to_clear"])

    @loader.command()
    async def gpresets(self, message: Message):
        """<save/load/del/list> — Управление пресетами (профилями)."""
        args = utils.get_args_raw(message)
        if not args: return await utils.answer(message, self.strings["gpresets_usage"])
        match = re.match(r"^(\w+)(?:\s+\[(.+?)\]|\s+(\S+))?(?:\s+(.*))?$", args, re.DOTALL)
        if not match: return await utils.answer(message, self.strings["gpresets_usage"])
        action = match.group(1).lower()
        name = match.group(2) or match.group(3)
        content = match.group(4)
        if action == "list":
            if not self.prompt_presets: return await utils.answer(message, self.strings["gpreset_empty"])
            text = self.strings["gpreset_list_head"]
            for idx, p in enumerate(self.prompt_presets, 1):
                text += f"<b>{idx}.</b> <code>{p['name']}</code> ({len(p['content'])} симв.)\n"
            return await utils.answer(message, text)
        if action == "save":
            if not name: return await utils.answer(message, "❌ Укажите имя: <code>.gpresets save [Имя] текст</code>")
            reply = await message.get_reply_message()
            if not content and reply:
                if reply.text: content = reply.text
                elif reply.file:
                    try: content = (await self.client.download_file(reply.media, bytes)).decode("utf-8", errors="ignore")
                    except: pass
            if not content: return await utils.answer(message, "❌ Нет текста для сохранения.")
            existing = self._find_preset(name)
            if existing:
                existing['content'] = content
            else:
                self.prompt_presets.append({"name": name, "content": content})
            self.db.set(self.strings["name"], DB_PRESETS_KEY, self.prompt_presets)
            await utils.answer(message, self.strings["gpreset_saved"].format(name, len(self.prompt_presets)))
        elif action == "load":
            target = self._find_preset(name)
            if not target: return await utils.answer(message, self.strings["gpreset_not_found"])
            self.config["system_instruction"] = target['content']
            await utils.answer(message, self.strings["gpreset_loaded"].format(target['name'], len(target['content'])))
        elif action == "del":
            target = self._find_preset(name)
            if not target: return await utils.answer(message, self.strings["gpreset_not_found"])
            self.prompt_presets.remove(target)
            self.db.set(self.strings["name"], DB_PRESETS_KEY, self.prompt_presets)
            await utils.answer(message, self.strings["gpreset_deleted"].format(target['name']))
        else:
             await utils.answer(message, self.strings["gpresets_usage"])

    def _find_preset(self, query):
        "Ищет пресет по номеру (строка '1') или имени."
        if not query: return None
        if str(query).isdigit():
            idx = int(query) - 1 
            if 0 <= idx < len(self.prompt_presets):
                return self.prompt_presets[idx]
        for p in self.prompt_presets:
            if p['name'].lower() == str(query).lower():
                return p
        return None

    @loader.command()
    async def gmemdel(self, message: Message):
        """[N] — удалить последние N пар сообщений из памяти."""
        try: n = int(utils.get_args_raw(message) or 1)
        except: n = 1
        cid = utils.get_chat_id(message)
        hist = self._get_structured_history(cid)
        if n > 0 and len(hist) >= n*2:
            self.conversations[str(cid)] = hist[:-n*2]
            self._save_history_sync()
            await utils.answer(message, f"🧹 Удалено последних <b>{n}</b> пар сообщений из памяти.")
        else: await utils.answer(message, "Недостаточно истории для удаления.")

    @loader.command()
    async def gmemchats(self, message: Message):
        """— Показать список чатов с активной памятью (имя и ID)."""
        if not self.conversations: return await utils.answer(message, self.strings["no_memory_found"])
        out = [self.strings["memory_chats_title"].format(len(self.conversations))]
        shown = set()
        for cid in list(self.conversations.keys()):
            if not str(cid).lstrip('-').isdigit(): continue
            chat_id = int(cid)
            if chat_id in shown: continue
            shown.add(chat_id)
            try:
                e = await self.client.get_entity(chat_id)
                name = get_display_name(e)
            except: name = f"Unknown ({chat_id})"
            out.append(self.strings["memory_chat_line"].format(name, chat_id))
        self._save_history_sync()
        if len(out) == 1: return await utils.answer(message, self.strings["no_memory_found"])
        await utils.answer(message, "\n".join(out))

    @loader.command()
    async def gmemexport(self, message: Message):
        """[<id/@юз чата>] [auto] [-s] — \n[из id/@юза чата] экспорт. -s в избранное."""
        args = utils.get_args_raw(message).split()
        save_to_self = "-s" in args
        if save_to_self:
            args.remove("-s")
        gauto_mode = "auto" in args
        if gauto_mode:
            args.remove("auto")
        source_chat_id_str = args[0] if args else None
        target_chat_id = "me" if save_to_self else message.chat_id
        if source_chat_id_str:
            try:
                entity = await self.client.get_entity(
                    int(source_chat_id_str)
                    if source_chat_id_str.lstrip("-").isdigit()
                    else source_chat_id_str
                )
                source_chat_id = entity.id
                hist = self._get_structured_history(source_chat_id, gauto=gauto_mode)
            except Exception:
                await utils.answer(message, self.strings["gme_chat_not_found"].format(utils.escape_html(source_chat_id_str)))
                return
        else:
            source_chat_id = utils.get_chat_id(message)
            hist = self._get_structured_history(source_chat_id, gauto=gauto_mode)
        if not hist:
            await utils.answer(message, "История для экспорта пуста.")
            return
        user_ids = {e.get("user_id") for e in hist if e.get("role") == "user" and e.get("user_id")}
        user_names = {None: None}
        for uid in user_ids:
            if not uid: continue
            try:
                entity = await self.client.get_entity(uid)
                user_names[uid] = get_display_name(entity)
            except Exception: user_names[uid] = f"Deleted Account ({uid})"
        import json
        def make_serializable(entry):
            entry = dict(entry)
            user_id = entry.get("user_id")
            if user_id: entry["user_name"] = user_names.get(user_id)
            if hasattr(user_id, "user_id"): entry["user_id"] = user_id.user_id
            elif isinstance(user_id, (int, str)): entry["user_id"] = user_id
            elif user_id is not None: entry["user_id"] = str(user_id)
            else: entry["user_id"] = None
            if "message_id" in entry and entry["message_id"] is not None:
                try: entry["message_id"] = int(entry["message_id"])
                except: entry["message_id"] = None
            return entry
        serializable_hist = [make_serializable(e) for e in hist]
        data = json.dumps(serializable_hist, ensure_ascii=False, indent=2)
        file_suffix = "gauto_history" if gauto_mode else "history"
        file = io.BytesIO(data.encode("utf-8"))
        file.name = f"gemini_{file_suffix}_{source_chat_id}.json"
        caption = "Экспорт истории gauto Gemini" if gauto_mode else "Экспорт памяти Gemini"
        if source_chat_id != utils.get_chat_id(message):
            caption += f" из чата <code>{source_chat_id}</code>"
        await self.client.send_file(
            target_chat_id,
            file,
            caption=caption,
            reply_to=message.id if target_chat_id == message.chat_id else None,
        )
        if save_to_self:
            if target_chat_id == "me" and message.chat_id != self.me.id:
                 await utils.answer(message, self.strings["gme_sent_to_saved"])
            else:
                 await message.delete()

    @loader.command()
    async def gmemimport(self, message: Message):
        """[auto] — импорт истории из файла (ответом). auto для gauto."""
        reply = await message.get_reply_message()
        if not reply or not reply.document: 
            return await utils.answer(message, "Ответьте на json-файл с памятью.")
        args = utils.get_args_raw(message).lower()
        gauto_mode = args == "auto"
        file = io.BytesIO()
        await self.client.download_media(reply, file)
        file.seek(0)
        MAX_IMPORT_SIZE = 15 * 1024 * 1024
        if file.getbuffer().nbytes > MAX_IMPORT_SIZE: 
            return await utils.answer(message, f"Файл слишком большой (>{MAX_IMPORT_SIZE // (1024*1024)} МБ).")
        import json
        try:
            hist = json.load(file)
            if not isinstance(hist, list): raise ValueError("Файл не содержит список истории.")
            new_hist =[]
            for e in hist:
                if not isinstance(e, dict) or "role" not in e or "content" not in e: 
                    raise ValueError("Некорректная структура памяти.")
                entry = {
                    "role": e["role"], 
                    "type": e.get("type", "text"), 
                    "content": e["content"], 
                    "date": e.get("date")
                }
                if e["role"] == "user":
                    entry["user_id"] = e.get("user_id")
                    entry["message_id"] = e.get("message_id")
                new_hist.append(entry)
            chat_id = str(utils.get_chat_id(message))
            if gauto_mode:
                self.gauto_conversations[chat_id] = new_hist
                self._save_history_sync(gauto=True)
            else:
                self.conversations[chat_id] = new_hist
                self._save_history_sync(gauto=False)
            mem_type = "Gauto память" if gauto_mode else "Память"
            await utils.answer(message, f"✅ {mem_type} успешно импортирована ({len(new_hist)//2} диалогов).")
        except Exception as e:
            await utils.answer(message, f"❌ Ошибка импорта: {e}")

    @loader.command()
    async def gmemfind(self, message: Message):
        """[слово] — Поиск в памяти текущего чата по ключевому слову или фразе."""
        q = utils.get_args_raw(message).lower()
        if not q: return await utils.answer(message, "Укажите слово для поиска.")
        cid = utils.get_chat_id(message)
        hist = self._get_structured_history(cid)
        found = [f"{e['role']}: {e.get('content','')[:200]}" for e in hist if q in str(e.get('content','')).lower()]
        if not found: await utils.answer(message, "Ничего не найдено.")
        else: await utils.answer(message, "\n\n".join(found[:10]))

    @loader.command()
    async def gmemoff(self, message: Message):
        """— Отключить память в этом чате"""
        self.memory_disabled_chats.add(str(utils.get_chat_id(message)))
        await utils.answer(message, "Память в этом чате отключена.")

    @loader.command()
    async def gmemon(self, message: Message):
        """— Включить память в этом чате"""
        self.memory_disabled_chats.discard(str(utils.get_chat_id(message)))
        await utils.answer(message, "Память в этом чате включена.")

    @loader.command()
    async def gmemshow(self, message: Message):
        """[auto] — Показать память чата (до 20 последних запросов). auto для gauto."""
        gauto = "auto" in utils.get_args_raw(message)
        cid = utils.get_chat_id(message)
        hist = self._get_structured_history(cid, gauto=gauto)
        if not hist: return await utils.answer(message, "Память пуста.")
        out = []
        for e in hist[-40:]:
            role = e.get('role')
            content = utils.escape_html(str(e.get('content',''))[:300])
            if role == 'user': out.append(f"{content}")
            elif role == 'model': out.append(f"<b>Gemini:</b> {content}")
        await utils.answer(message, "<blockquote expandable='true'>" + "\n".join(out) + "</blockquote>")

    @loader.command()
    async def gmodel(self, message: Message):
        """[model] [-s] — Узнать/сменить модель. -s — список. Авто-проверка совместимости."""
        args_raw = utils.get_args_raw(message).strip().lower()
        args_list = args_raw.split()
        is_list_request = "-s" in args_list
        provider = self.config["provider"]
        if is_list_request:
            status_msg = await utils.answer(message, self.strings["processing"])
            try:
                if provider == "openrouter":
                    api_key = self.config["Openrouter_api_key"]
                    if not api_key: return await utils.answer(status_msg, self.strings['no_api_key_Openrouter'])
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            "https://openrouter.ai/api/v1/models",
                            headers={"Authorization": f"Bearer {api_key}"}
                        ) as resp:
                            if resp.status != 200: raise ValueError(f"HTTP {resp.status}")
                            data = await resp.json()
                    models_data = data.get("data",[])
                    models_data.sort(key=lambda x: x["id"])
                    top_list = []
                    other_list = []
                    favs =["google/gemini-2.0-flash-001", "openai/gpt-4o", "anthropic/claude-3.5-sonnet", "deepseek/deepseek-r1"]
                    for m in models_data:
                        mid = m["id"]
                        line = f"• <code>{mid}</code>"
                        if mid in favs: top_list.append(line)
                        elif any(x in mid for x in ["gemini", "gpt", "claude", "deepseek", "llama"]): other_list.append(line)
                    text = self.strings.get("gmodel_list_title_Openrouter", "📋 Models:") + "\n" + "\n".join(top_list) + "\n\n"
                    text += "\n".join(other_list[:50])
                    if len(other_list) > 50: text += f"\n\n<i>...и еще {len(other_list)-50} моделей.</i>"
                    file = io.BytesIO(text.encode("utf-8"))
                    await self.client.send_file(message.chat_id, file=file, caption="📋 OpenRouter Models", reply_to=message.id)
                    await status_msg.delete()
                else:
                    if not self.api_keys: return await utils.answer(status_msg, self.strings['no_api_key'])
                    client = genai.Client(api_key=self.api_keys[self.current_api_key_index])
                    models = await asyncio.to_thread(client.models.list)
                    txt = "\n".join([f"• <code>{m.name.split('/')[-1]}</code>" for m in models])
                    f = io.BytesIO((self.strings["gmodel_list_title"] + "\n" + txt).encode('utf-8'))
                    f.name = "models_list.txt"
                    await self.client.send_file(message.chat_id, file=f, caption="📋 Список доступных моделей", reply_to=message.id)
                    await status_msg.delete()
            except Exception as e: 
                await utils.answer(status_msg, self.strings["gmodel_list_error"].format(self._handle_error(e)))
            return
        if not args_raw: 
            return await utils.answer(message, f"🔮 <b>Провайдер:</b> <code>{provider}</code>\n🧠 <b>Модель:</b> <code>{self.config['model_name']}</code>")
        self.config["model_name"] = args_raw
        warning = ""
        if provider == "google" and ("/" in args_raw or any(x in args_raw for x in["gpt", "claude", "deepseek", "llama"])):
            warning = (
                "\n\n⚠️ <b>Конфликт настроек!</b>\n"
                f"Вы установили модель <code>{args_raw}</code>, но провайдер остался <b>Google</b>.\n"
                "Смените провайдера командой:\n<code>.cfg gemini provider openrouter</code>"
            )
        elif provider == "openrouter" and "/" not in args_raw and "gemini" in args_raw:
             warning = (
                "\n\n⚠️ <b>Совет:</b> Для OpenRouter лучше использовать полные ID.\n"
                f"Например: <code>google/{args_raw}</code>"
            )
        await utils.answer(message, f"✅ Модель установлена: <code>{args_raw}</code>{warning}")

    @loader.command()
    async def gres(self, message: Message):
        """[auto] — Очистить ВСЮ память. auto для всей памяти gauto."""
        if utils.get_args_raw(message) == "auto":
            if not self.gauto_conversations: return await utils.answer(message, self.strings["no_gauto_memory_to_fully_clear"])
            n = len(self.gauto_conversations)
            self.gauto_conversations.clear()
            self._save_history_sync(True)
            await utils.answer(message, self.strings["gauto_memory_fully_cleared"].format(n))
        else:
            if not self.conversations: return await utils.answer(message, self.strings["no_memory_to_fully_clear"])
            n = len(self.conversations)
            self.conversations.clear()
            self._save_history_sync(False)
            await utils.answer(message, self.strings["memory_fully_cleared"].format(n))


    @loader.callback_handler()
    async def gemini_callback_handler(self, call: InlineCall):
        if not call.data.startswith("gemini:"): return
        parts = call.data.split(":")
        action = parts[1]
        
        if action == "noop": 
            await call.answer()
            return
        if action == "close":
            uid = parts[2]
            if uid in self.pager_cache:
                del self.pager_cache[uid]
                self.db.set(self.strings["name"], DB_PAGER_CACHE_KEY, self.pager_cache)
            try: await call.answer()
            except: pass
            try:
                chat = call.chat_id
                msg_id = call.message_id
                if chat and msg_id:
                    await self.client.delete_messages(chat, msg_id)
                else:
                    await call.delete()
            except Exception:
                try: await call.edit("🗑 <b>Сессия закрыта.</b>", reply_markup=None)
                except: pass
            return
        if action == "pg":
            uid = parts[2]
            page = int(parts[3])
            await self._render_page(uid, page, call)
            return
        if action == "regen":
            chat_id = int(parts[2])
            msg_id = int(parts[3])
            key = f"{chat_id}:{msg_id}"
            last_request_tuple = self.last_requests.get(key)
            if not last_request_tuple:
                await call.answer(self.strings["no_last_request"], show_alert=True)
                return
            last_parts, display_prompt = last_request_tuple
            use_url_context = bool(re.search(r'https?://\S+', display_prompt or ""))
            await call.edit(f"<tg-emoji emoji-id=5386367538735104399>⌛️</tg-emoji> <b>Регенерация...</b>", reply_markup=None)
            await self._send_to_gemini(
                message=msg_id, 
                parts=last_parts, 
                regeneration=True, 
                call=call, 
                chat_id_override=chat_id, 
                use_url_context=use_url_context, 
                display_prompt=display_prompt
            )
            return

    async def _clear_callback(self, call: InlineCall, cid):
        self._clear_history(cid, gauto=False)
        await call.edit(self.strings["memory_cleared"], reply_markup=None)

    async def _regenerate_callback(self, call: InlineCall, mid, cid):
        key = f"{cid}:{mid}"
        if key not in self.last_requests: return await call.answer(self.strings["no_last_request"], show_alert=True)
        parts, disp = self.last_requests[key]
        use_url_context = bool(re.search(r'https?://\S+', disp or ""))
        await self._send_to_gemini(mid, parts, regeneration=True, call=call, chat_id_override=cid, display_prompt=disp, use_url_context=use_url_context)

    async def _close_callback(self, call: InlineCall, uid: str):
        """Обрабатывает нажатие кнопки закрытия для пагинации"""
        await call.answer()
        if uid in self.pager_cache:
            del self.pager_cache[uid]
        try:
            await self.client.delete_messages(call.chat_id, call.message_id)
        except Exception:
            try:
                await call.edit("✔️ Сессия закрыта.", reply_markup=None)
            except Exception:
                pass

    async def _render_page(self, uid, page_num, entity):
        data = self.pager_cache.get(uid)
        if not data:
            if isinstance(entity, InlineCall):
                await entity.edit(
                    "⚠️ <b>Сессия истекла или бот был перезагружен с потерей данных.</b>",
                    reply_markup=[[{"text": "🗑 Удалить", "data": f"gemini:close:{uid}"}]]
                )
            return
        chunks = data["chunks"]
        total = data["total"]
        header = data.get("header", "")
        chat_id = data.get("chat_id")
        base_msg_id = data.get("msg_id")
        raw_text_chunk = chunks[page_num]
        safe_text = self._markdown_to_html(raw_text_chunk)
        formatted_body = self._format_response_with_smart_separation(safe_text)
        text_to_show = f"{header}\n{formatted_body}"
        text_to_show = text_to_show.replace('<emoji document_id=', '<tg-emoji emoji-id=').replace('</emoji>', '</tg-emoji>')
        nav_row =[]
        if page_num > 0:
            nav_row.append({
                "text": "◀️", 
                "data": f"gemini:pg:{uid}:{page_num - 1}"})
        nav_row.append({"text": f"{page_num + 1}/{total}", "data": "gemini:noop"})
        if page_num < total - 1:
            nav_row.append({
                "text": "▶️", 
                "data": f"gemini:pg:{uid}:{page_num + 1}"})
        extra_row =[{"text": "❌ Закрыть", "data": f"gemini:close:{uid}"}]
        if chat_id and base_msg_id:
             extra_row.append({
                "text": "🔄", 
                "data": f"gemini:regen:{chat_id}:{base_msg_id}"})
        buttons = [nav_row, extra_row]
        if isinstance(entity, Message):
            await self.inline.form(text=text_to_show, message=entity, reply_markup=buttons)
        elif isinstance(entity, InlineCall):
            await entity.edit(text=text_to_show, reply_markup=buttons)
        elif hasattr(entity, "edit"):
            try: await entity.edit(text=text_to_show, reply_markup=buttons)
            except: pass

    def _paginate_text(self, text: str, limit: int) -> list:
        pages = []
        current_page_lines = []
        current_len = 0
        in_code_block = False
        current_code_lang = ""
        lines = text.split('\n')
        for line in lines:
            line_len = len(line) + 1
            stripped = line.strip()
            if stripped.startswith("```"):
                if in_code_block:
                    in_code_block = False
                    current_code_lang = ""
                else:
                    in_code_block = True
                    current_code_lang = stripped.replace("```", "").strip()
            if current_len + line_len > limit:
                if current_page_lines:
                    if in_code_block: current_page_lines.append("```")
                    pages.append("\n".join(current_page_lines))
                    current_page_lines = []
                    current_len = 0
                    if in_code_block:
                        header = f"```{current_code_lang}"
                        current_page_lines.append(header)
                        current_len += len(header) + 1
                if line_len > limit:
                    chunks = [line[i:i+limit] for i in range(0, len(line), limit)]
                    for chunk in chunks:
                        if current_len + len(chunk) > limit:
                             pages.append("\n".join(current_page_lines))
                             current_page_lines = [chunk]
                             current_len = len(chunk)
                        else:
                            current_page_lines.append(chunk)
                            current_len += len(chunk)
                    continue
            current_page_lines.append(line)
            current_len += line_len
        if current_page_lines:
            pages.append("\n".join(current_page_lines))
        return pages

    @loader.watcher(only_incoming=True, ignore_edited=True)
    async def watcher(self, message: Message):
        if not hasattr(message, 'chat_id'): return
        cid = utils.get_chat_id(message)
        if cid not in self.impersonation_chats: return
        if message.is_private and not self.config["gauto_in_pm"]: return
        if message.out or (isinstance(message.from_id, tg_types.PeerUser) and message.from_id.user_id == self.me.id): return
        sender = await message.get_sender()
        if isinstance(sender, tg_types.User) and sender.bot: return
        if random.random() > self.config["impersonation_reply_chance"]: return
        parts, warnings = await self._prepare_parts(message)
        if warnings: logger.warning(f"Gauto warn: {warnings}")
        if not parts: return
        resp = await self._send_to_gemini(message=message, parts=parts, impersonation_mode=True)
        if resp and resp.strip():
            cln = resp.strip()
            await asyncio.sleep(random.uniform(2, 8))
            try: await self.client.send_read_acknowledge(cid, message=message)
            except: pass
            async with message.client.action(cid, "typing"):
                await asyncio.sleep(min(25.0, max(1.5, len(cln) * random.uniform(0.1, 0.25))))
            await message.reply(cln)

    def _get_proxy_config(self):
        p = self.config["proxy"]
        return {"http://": p, "https://": p} if p else None

    def _save_history_sync(self, gauto: bool=False):
        if getattr(self, "_db_broken", False): return
        data, key = (self.gauto_conversations, DB_GAUTO_HISTORY_KEY) if gauto else (self.conversations, DB_HISTORY_KEY)
        try: self.db.set(self.strings["name"], key, data)
        except: self._db_broken = True

    def _load_history_from_db(self, key):
        d = self.db.get(self.strings["name"], key, {})
        return d if isinstance(d, dict) else {}

    def _get_structured_history(self, cid, gauto=False):
        d = self.gauto_conversations if gauto else self.conversations
        if str(cid) not in d: d[str(cid)] = []
        return d[str(cid)]

    def _update_history(self, chat_id: int, user_parts: list, model_response: str, regeneration: bool = False, message: Message = None, gauto: bool = False):
        if not self._is_memory_enabled(str(chat_id)):
            return
        history = self._get_structured_history(chat_id, gauto)
        import time
        now = int(time.time())
        user_id = self.me.id
        user_name = get_display_name(self.me)
        message_id = getattr(message, "id", None)
        if message:
            try:
                peer_id = get_peer_id(message)
                if peer_id:
                    user_id = peer_id
            except (TypeError, ValueError):
                if message.sender_id: user_id = message.sender_id
            if message.sender:
                user_name = get_display_name(message.sender)
        user_text = " ".join([p.text for p in user_parts if hasattr(p, "text") and p.text]) or "[ответ на медиа]"
        if regeneration and history:
            for i in range(len(history) - 1, -1, -1):
                if history[i].get("role") == "model":
                    history[i].update({
                        "content": model_response, 
                        "date": now
                    })
                    break
        else:
            user_entry = {
                "role": "user",
                "type": "text",
                "content": user_text,
                "date": now,
                "user_id": user_id,
                "message_id": message_id,
                "user_name": user_name
            }
            model_entry = {
                "role": "model",
                "type": "text",
                "content": model_response,
                "date": now,
                "user_id": None 
            }
            history.extend([user_entry, model_entry])
        limit = self.config["max_history_length"]
        if limit > 0 and len(history) > limit * 2:
            history = history[-(limit * 2):]
        target = self.gauto_conversations if gauto else self.conversations
        target[str(chat_id)] = history
        self._save_history_sync(gauto)

    def _clear_history(self, cid, gauto=False):
        d = self.gauto_conversations if gauto else self.conversations
        if str(cid) in d:
            del d[str(cid)]
            self._save_history_sync(gauto)

    def _markdown_to_html(self, text):
        text = re.sub(r"^(#+)\s+(.*)", lambda m: f"<b>{m.group(2)}</b>", text, flags=re.M)
        text = re.sub(r"^([ \t]*)[-*+]\s+", r"\1• ", text, flags=re.M)
        md = MarkdownIt("commonmark", {"html": True, "linkify": True}).enable("strikethrough")
        html = md.render(text)
        def fmt_code(m):
            lang = utils.escape_html(m.group(1).strip()) if m.group(1) else ""
            return f'<pre><code class="language-{lang}">{utils.escape_html(m.group(2).strip())}</code></pre>' if lang else f'<pre><code>{utils.escape_html(m.group(2).strip())}</code></pre>'
        html = re.sub(r"```(\w+)?\n([\s\S]+?)\n```", fmt_code, html)
        html = re.sub(r"<p>(<pre>[\s\S]*?</pre>)</p>", r"\1", html, flags=re.DOTALL)
        return html.replace("<p>", "").replace("</p>", "\n").strip()

    def _format_response_with_smart_separation(self, text):
        parts = re.split(r"(<pre.*?>[\s\S]*?</pre>)", text, flags=re.DOTALL)
        out = []
        for i, p in enumerate(parts):
            if not p or p.isspace(): continue
            if i % 2 == 1: out.append(p.strip())
            else: out.append(f"<blockquote expandable>{p.strip()}</blockquote>")
        return "\n".join(out)

    def _get_inline_buttons(self, cid, mid):
        return [[
            {"text": self.strings["btn_clear"], "callback": self._clear_callback, "args": (cid,)},
            {"text": self.strings["btn_regenerate"], "callback": self._regenerate_callback, "args": (mid, cid)}
        ]]

    async def _clear_callback(self, call: InlineCall, cid):
        self._clear_history(cid, gauto=False)
        await call.edit(self.strings["memory_cleared"], reply_markup=None)

    async def _regenerate_callback(self, call: InlineCall, mid, cid):
        key = f"{cid}:{mid}"
        if key not in self.last_requests: return await call.answer(self.strings["no_last_request"], show_alert=True)
        parts, disp = self.last_requests[key]
        use_url_context = bool(re.search(r'https?://\S+', disp or ""))
        await self._send_to_gemini(mid, parts, regeneration=True, call=call, chat_id_override=cid, display_prompt=disp, use_url_context=use_url_context)

    async def _get_recent_chat_text(self, cid, count=None, skip_last=False):
        lim = (count or self.config["impersonation_history_limit"]) + (1 if skip_last else 0)
        lines = []
        try:
            msgs = await self.client.get_messages(cid, limit=lim)
            if skip_last and msgs: msgs = msgs[1:]
            for m in msgs:
                if not m: continue
                if not (m.text or m.sticker or m.photo or m.file or m.media):
                    continue
                name = get_display_name(await m.get_sender()) or "Unknown"
                txt = m.text or ""
                if m.sticker:
                    alt = "?"
                    if hasattr(m.sticker, 'attributes'):
                        alt = next((a.alt for a in m.sticker.attributes if isinstance(a, DocumentAttributeSticker)), "?")
                    txt += f" [Стикер: {alt}]"
                elif m.photo:
                    txt += " [Фото]"
                elif m.file:
                    txt += " [Файл]"
                elif m.media and not txt:
                    txt += " [Медиа]"
                if txt.strip():
                    lines.append(f"{name}: {txt.strip()}")
        except Exception as e:
            pass 
        return "\n".join(reversed(lines))

    def _handle_error(self, e: Exception) -> str:
        logger.exception("Gemini execution error")
        if isinstance(e, asyncio.TimeoutError):
            return self.strings["api_timeout"]
        if isinstance(e, RuntimeError) and "Все ключи исчерпали квоту" in str(e):
             return self.strings["all_keys_exhausted"].format(len(self.api_keys))
        if google_exceptions and isinstance(e, google_exceptions.GoogleAPIError):
            msg = str(e)
            if "quota" in msg.lower() or "exceeded" in msg.lower():
                model_name = self.config.get("model_name", "unknown")
                model_name_match = re.search(r'key: "model"\s+value: "([^"]+)"', msg)
                if model_name_match:
                    model_name = model_name_match.group(1)
                return (
                    f"❗️ <b>Превышен лимит Google Gemini API для модели <code>{utils.escape_html(model_name)}</code>.</b>"
                    "\n\nЧаще всего это происходит на бесплатном тарифе. Вы можете:\n"
                    "• Подождать, пока лимит сбросится (обычно раз в сутки).\n"
                    "• Проверить свой тарифный план в <a href='https://aistudio.google.com/app/billing'>Google AI Studio</a>.\n"
                    "• Узнать больше о лимитах <a href='https://ai.google.dev/gemini-api/docs/rate-limits'>здесь</a>.\n\n"
                    f"<b>Детали ошибки:</b>\n<code>{utils.escape_html(msg)}</code>"
                )
            if "500 An internal error has occurred" in msg:
                return (
                    "❗️ <b>Ошибка 500 от Google API.</b>\n"
                    "Это значит, что формат медиа (файл или еще что то) который ты отправил, не поддерживается.\n"
                    "Такое случается, по такой причине:\n  "
                    "• Если формат файла в принципе не поддерживается Gemini/Гуглом.\n  "
                    "• Временный сбой на серверах Google. Попробуйте повторить запрос позже."
                )
            if "User location is not supported" in msg or "location is not supported" in msg:
                return (
                    '❗️ <b>В данном регионе Gemini API не доступен.</b>\n'
                    'Скачайте VPN (для пк/тел) или поставьте прокси (платный/бесплатный).\n'
                    'Или воспользуйтесь инструкцией <a href="https://t.me/SenkoGuardianModules/23">вот тут</a>\n'
                    'А для тех у кого UserLand инструкция <a href="https://t.me/SenkoGuardianModules/35">тут</a>'
                )
            if "API key not valid" in msg:
                return self.strings["invalid_api_key"]
            if "blocked" in msg.lower():
                return self.strings["blocked_error"].format(utils.escape_html(msg))
            return self.strings["api_error"].format(utils.escape_html(msg))
        if isinstance(e, (OSError, aiohttp.ClientError, socket.timeout)):
            return "❗️ <b>Сетевая ошибка:</b>\n<code>{}</code>".format(utils.escape_html(str(e)))
        msg = str(e)
        if "No API_KEY or ADC found" in msg or "GOOGLE_API_KEY environment variable" in msg or "genai.configure(api_key" in msg:
            return self.strings["no_api_key"]
        if "quota" in msg.lower() or "429" in msg: return self.strings["all_keys_exhausted"].format(len(self.api_keys))
        return self.strings["generic_error"].format(utils.escape_html(msg))

    def _markdown_to_html(self, text: str) -> str:
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        text = re.sub(r"<thought>.*?</thought>", "", text, flags=re.DOTALL)
        text = re.sub(r"(?i)<br\s*/?>", "\n", text)
        def heading_replacer(match): level=len(match.group(1)); title=match.group(2).strip(); indent="   " * (level - 1); return f"{indent}<b>{title}</b>"
        text=re.sub(r"^(#+)\s+(.*)", heading_replacer, text, flags=re.MULTILINE)
        def list_replacer(match): indent=match.group(1); return f"{indent}• "
        text=re.sub(r"^([ \t]*)[-*+]\s+", list_replacer, text, flags=re.MULTILINE)
        md=MarkdownIt("commonmark", {"html": True, "linkify": True}); md.enable("strikethrough"); md.disable("hr"); md.disable("heading"); md.disable("list")
        html_text=md.render(text)
        def format_code(match):
            lang=utils.escape_html(match.group(1).strip()); code=utils.escape_html(match.group(2).strip())
            return f'<pre><code class="language-{lang}">{code}</code></pre>' if lang else f'<pre><code>{code}</code></pre>'
        html_text=re.sub(r"```(.*?)\n([\s\S]+?)\n```", format_code, html_text)
        html_text=re.sub(r"<p>(<pre>[\s\S]*?</pre>)</p>", r"\1", html_text, flags=re.DOTALL)
        html_text=html_text.replace("<p>", "").replace("</p>", "\n")
        html_text=re.sub(r"(?i)<br\s*/?>", "\n", html_text).strip()
        return html_text

    def _format_response_with_smart_separation(self, text: str) -> str:
        pattern = r"(<pre.*?>[\s\S]*?</pre>)"
        parts = re.split(pattern, text, flags=re.DOTALL)
        result_parts = []
        for i, part in enumerate(parts):
            if not part or part.isspace():
                continue
            if i % 2 == 1:
                result_parts.append(part.strip())
            else:
                stripped_part = part.strip()
                if stripped_part:
                    result_parts.append(f'<blockquote expandable="true">{stripped_part}</blockquote>')
        return "\n".join(result_parts)

    def _get_inline_buttons(self, chat_id, base_message_id):
        return [[{"text": self.strings["btn_clear"], "callback": self._clear_callback, "args": (chat_id,)}, 
                {"text": self.strings["btn_regenerate"], "data": f"gemini:regen:{chat_id}:{base_message_id}"}]
        ]

    async def _safe_del_msg(self, msg, delay=1):
        await asyncio.sleep(delay)
        try: await self.client.delete_messages(msg.chat_id, msg.id)
        except Exception as e: logger.warning(f"Ошибка удаления сообщения: {e}")

    async def _clear_callback(self, call: InlineCall, chat_id: int):
        self._clear_history(chat_id, gauto=False)
        await call.edit(self.strings["memory_cleared"], reply_markup=None)

    async def _scan_keys(self, force=False):
        """
        Сканирует ключи на валидность.
        """
        if not GOOGLE_AVAILABLE: return "Library missing", []
        current_map_keys = list(self.key_model_map.keys())
        for k in current_map_keys:
            if k not in self.api_keys: del self.key_model_map[k]
        if not force and all(k in self.key_model_map for k in self.api_keys):
            return "Loaded from cache", []
        if force: self.key_model_map = {}
        proxy_config = self._get_proxy_config()
        http_opts = types.HttpOptions(async_client_args={"proxies": proxy_config, "timeout": 10.0}) if proxy_config else None
        active_keys = []
        invalid_keys = []
        minimal_config = types.GenerateContentConfig(
            response_mime_type="text/plain",
            max_output_tokens=1, 
            candidate_count=1,
            safety_settings=[types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE")]
        )
        for i, key in enumerate(self.api_keys):
            if i > 0: await asyncio.sleep(1.2)
            try:
                client = genai.Client(api_key=key, http_options=http_opts)
                response = await client.aio.models.generate_content(
                    model=CHECK_MODEL, contents="test", config=minimal_config
                )
                active_keys.append(key)
                self.key_model_map[key] = 1
            except Exception as e:
                err = str(e).lower()
                if "invalid_argument" in err or "api_key_invalid" in err or "400" in err or "blocked" in err:
                    invalid_keys.append(key)
                else:
                    self.key_model_map[key] = 0 
        self.db.set(self.strings["name"], DB_KEY_MAP_KEY, self.key_model_map)
        short_report = (
            f"✅ <b>Скан завершен.</b>\n"
            f"💎 <b>Active:</b> {len(active_keys)}\n"
            f"🗑 <b>Invalid:</b> {len(invalid_keys)}\n"
            f"👻 <b>RateLimited/Other:</b> {len(self.api_keys) - len(active_keys) - len(invalid_keys)}"
        )
        return short_report, invalid_keys

    def _get_sorted_keys(self):
        valid_keys = []
        for key in self.api_keys:
            if key not in self.key_model_map:
                if not self.key_model_map: valid_keys.append((key, 0, random.random()))
                continue
            tier = self.key_model_map[key]
            valid_keys.append((key, tier, random.random()))
        valid_keys.sort(key=lambda x: (x[1], x[2]))
        return [item[0] for item in valid_keys]

    async def _call_google_rest(self, model_name: str, prompt: str, input_image_bytes=None):
        keys = self._get_sorted_keys()
        if not keys: return {"error": {"message": "Нет доступных API ключей"}}
        parts = [{"text": prompt}]
        if input_image_bytes:
            resized = await utils.run_sync(self._resize_image_ig, input_image_bytes)
            b64_img = base64.b64encode(resized).decode('utf-8')
            parts.insert(0, {"inlineData": {"mimeType": "image/jpeg", "data": b64_img}})
        payload = {
            "contents": [{"parts": parts}],
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ],
            "generationConfig": {"candidateCount": 1, "temperature": 1.0}
        }
        proxy = self.config['proxy'] if self.config['proxy'] else None
        last_error = None
        async with aiohttp.ClientSession() as session:
            for i, api_key in enumerate(keys):
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                try:
                    if i > 0: await asyncio.sleep(1)
                    async with session.post(url, json=payload, proxy=proxy, timeout=60) as resp:
                        if resp.status == 200:
                            return await resp.json()
                        elif resp.status in [429, 503, 403]:
                            last_error = f"HTTP {resp.status}"
                            continue
                        else:
                            text = await resp.text()
                            return {"error": {"message": f"HTTP {resp.status}: {text}"}}
                except Exception as e:
                    last_error = str(e)
                    continue
        return {"error": {"message": f"All keys exhausted. Last error: {last_error}"}}

    def _resize_image_ig(self, img_bytes):
        try:
            img = Image.open(io.BytesIO(img_bytes))
            img.thumbnail((1024, 1024)) 
            out = io.BytesIO()
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            img.save(out, format='JPEG', quality=85)
            return out.getvalue()
        except: return img_bytes

    async def _send_to_Openrouter_api(self, model, messages, temperature):
        """Отправка запроса в OpenRouter (OpenAI format)"""
        api_key = self.config["Openrouter_api_key"]
        if not api_key:
            raise ValueError("Не указан OpenRouter API Key! Установите его в .cfg")
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/SenkoGuardian",
            "X-Title": "Gemini Module for Heroku Telegram-userbot",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": min(temperature, 1.0)
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=GEMINI_TIMEOUT) as resp:
                text = await resp.text()
                if resp.status != 200:
                    try:
                        err_json = json.loads(text)
                        err_msg = err_json.get('error', {}).get('message', text)
                    except:
                        err_msg = text
                    raise ConnectionError(f"OpenRouter API Error {resp.status}: {err_msg}")
                try:
                    result = json.loads(text)
                except json.JSONDecodeError:
                    raise ValueError(f"OpenRouter вернул не JSON: {text[:100]}...")
                if "choices" not in result or not result["choices"]:
                    if "error" in result:
                        raise ValueError(f"OpenRouter Logic Error: {result['error']}")
                    raise ValueError(f"Пустой ответ (нет 'choices'). Raw: {text}")
                return result["choices"][0]["message"]["content"]

    def _convert_google_history_to_openai(self, history: list, system_prompt: str) -> list:
        """Конвертирует историю из формата Google в формат OpenAI."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        try:
            user_tz = pytz.timezone(self.config["timezone"])
        except:
            user_tz = pytz.utc
        for item in history:
            role = "assistant" if item['role'] == "model" else "user"
            content = item.get("content", "")
            if 'date' in item and item['date']:
                dt = datetime.fromtimestamp(item['date'], user_tz)
                content = f"[{dt.strftime('%d.%m.%Y %H:%M')}] {content}"
            messages.append({"role": role, "content": content})
        return messages


    def _is_memory_enabled(self, chat_id: str) -> bool: return chat_id not in self.memory_disabled_chats
    def _disable_memory(self, chat_id: int): self.memory_disabled_chats.add(str(chat_id))
    def _enable_memory(self, chat_id: int): self.memory_disabled_chats.discard(str(chat_id))
