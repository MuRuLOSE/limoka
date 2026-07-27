#  This file is part of SenkoGuardianModules
#  Copyright (c) 2025-2026 Senko
#  This software is released under the MIT License.
#  https://opensource.org/licenses/MIT

# scope heroku_min: 2.0.0
# meta banner: https://raw.githubusercontent.com/SenkoGuardian/SenkoGuardian.github.io/main/OfficialSenkoGuardianBanner.png
# meta pic: https://raw.githubusercontent.com/SenkoGuardian/SenkoGuardian.github.io/main/OfficialSenkoGuardianBanner.png

__version__ = ("1", "7", "0") # в этот раз комменты свои добавил что бы было понятно кратко, что да как и где что работает.
"""￣へ￣"""

# meta developer: @SenkoGuardianModules

#  .------. .------. .------. .------. .------. .------.
#  |S.--. | |E.--. | |N.--. | |M.--. | |O.--. | |D.--. |
#  | :/\: | | :/\: | | :(): | | :/\: | | :/\: | | :/\: |
#  | :\/: | | :\/: | | ()() | | :\/: | | :\/: | | :\/: |
#  | '--'S| | '--'E| | '--'N| | '--'M| | '--'O| | '--'D|
#  `------' `------' `------' `------' `------' `------'


import asyncio
import logging
import re
import traceback
import random
import time
import copy
import shlex
import os
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
MSK = timezone(timedelta(hours=3), name="MSK")
from telethon import functions, errors, types, utils as tl_utils
from telethon.tl.types import Message, Channel
from .. import loader, utils

BYPASS_SKIP_OVER_MB = 4096      # медиа крупнее скип
BYPASS_MIN_FREE_DISK_MB = 800   

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_cc_client = None
_cc_log_channel = None
_cc_log_topic_id = None

class _CCTopicHandler(logging.Handler):

    def emit(self, record):
        if _cc_client is None or _cc_log_channel is None or _cc_log_topic_id is None:
            return
        try:
            text = f"<code>[{record.levelname}]</code> {self.format(record)}"
            chat_id = int(_cc_log_channel)
            if chat_id > 0:
                chat_id = int(f"-100{chat_id}")
            asyncio.ensure_future(
                _cc_client.send_message(
                    chat_id,
                    text,
                    parse_mode="html",
                    reply_to=_cc_log_topic_id,
                )
            )
        except Exception:
            pass

_cc_topic_handler = _CCTopicHandler()
_cc_topic_handler.setLevel(logging.INFO)  # INFO чтобы видеть прогресс пересылки
_cc_topic_handler.setFormatter(logging.Formatter("%(message)s"))
_cc_topic_handler._chatcopy_topic_handler = True
if not any(getattr(handler, "_chatcopy_topic_handler", False) for handler in logger.handlers):
    logger.addHandler(_cc_topic_handler)

FILTER_ALL = "all"
FILTER_MEDIA = "media"
FILTER_PHOTO_VIDEO = "photo_video"
FILTER_DOCS = "docs"
FILTER_TEXT = "text"
FILTER_NO_AD = "no_ad"

@loader.tds
class ChatCopy(loader.Module):
    """Модуль для копирования чатов с поддержкой топиков (форумов), фото, видео, файлов (документов)."""
    strings = {
        "name": "ChatCopy",
        "cfg_batch": "Размер пачки сообщений (1-100)",
        "cfg_delay": "Задержка ОТПРАВКИ между пачками (сек)",
        "cfg_flood_buffer": "Дополнительное время к FloodWait (сек)",
        "cfg_timezone": "Часовой пояс для времени в статусах (UTC offset, например 3 для MSK)",
        "copy_start": (
            '<emoji document_id=5372917041193828849>🚀</emoji><b> ChatCopy: Запуск копирования</b>\n\n'
            "<b>Источник:</b> {src}\n"
            '<emoji document_id=5116204921766544244>⏬</emoji><emoji document_id=5116204921766544244>⏬</emoji><emoji document_id=5116204921766544244>⏬</emoji><emoji document_id=5116204921766544244>⏬</emoji>\n'
            "<b>Цель:</b> {dest}\n\n"
            '<emoji document_id=5258096772776991776>⚙️</emoji> <b>Режим:</b> {mode}\n'
            '<emoji document_id=5226513232549664618>🔢</emoji> <b>Старт с ID:</b> {start_id}\n'
            '<emoji document_id=6035191085452497972>👤</emoji> <b>Без автора:</b> {no_auth}\n'
            '<emoji document_id=6028504027531055196>💬</emoji> <b>Без подписей:</b> {no_capt}\n'
            '📎 <b>Фильтр:</b> {filter_type}\n'
            '🚫 <b>Игнор топиков:</b> {ignored_topics}\n'
            '<emoji document_id=6030550768426159669>🛡</emoji> <b>Обход:</b> {bypass}\n'
            '📦 <b>Всего сообщений:</b> {total_msgs}\n'
            '⏱ <b>Оценка времени:</b> {estimated_time}\n\n'
            "<i>Задача добавлена в очередь. Позиция: {position}</i>"
        ),
        "status_none": "<emoji document_id=5440708164787081930>ℹ️</emoji> Сейчас нет активных копирований.",
        "status_header": "<emoji document_id=5258096772776991776>📊</emoji> <b>Статус ChatCopy</b> (активных: {n})\n",
        "status_item": (
            "\n<blockquote><b>{src}</b> → <b>{dest}</b>\n"
            "├ Статус: <code>{status}</code>\n"
            "├ Прогресс: <code>{current}/{total}</code> ({progress}%)\n"
            "├ Скорость: <code>{speed}/мин</code>\n"
            "├ ETA: <code>{eta}</code>\n"
            "├ Пересылка: <code>{fwd}</code>\n"
            "├ Скачка: <code>{bypass}</code>\n"
            "├ Сейчас: <code>{working}</code>\n"
            "└ FloodWait'ов: <code>{floods}</code> (всего ~{flood_time})</blockquote>"
        ),
        "copy_done_detailed": (
            '<emoji document_id=5208422125924275090>✅</emoji> <b>Задача выполнена</b>\n'
            "<blockquote>{src} → {dest}\n"
            "Без автора: {no_auth}\n"
            "Без подписей: {no_capt}\n"
            "Старт с ID: {start_id}\n"
            "Режим: {mode}\n"
            "Фильтр: {filter_type}</blockquote>\n"
            '<emoji document_id=5123248930124989216>✅</emoji> <b>Перенесено сообщений: {count}</b> <emoji document_id=5123248930124989216>✅</emoji>\n'
            '⏱  <b>Длительность:</b> {duration}\n'
            '⚡ <b>Средняя скорость:</b> {avg_speed} сообщений/мин'
            "{flood_info}"
        ),
        "flood_wait_notice": (
            "<emoji document_id=5386761726538570473>⏸</emoji> <b>FloodWait</b>\n"
            "🛑 <b>На FloodWait:</b> <code>{flood_path}</code>\n"
            "🔁 <b>Сейчас:</b> <code>{working}</code>\n"
            "<emoji document_id=5983150113483134607>🕐</emoji> <b>Задержка:</b> <code>{minutes}m {seconds}s</code>\n"
            "<emoji document_id=5983150113483134607>🕐</emoji> <b>Возобновление:</b> <code>{resume_time}</code>\n"
            "<emoji document_id=5411563083908797492>📨</emoji> <b>Переслано:</b> <code>{count}</code> сообщений\n"
            "<emoji document_id=5316575093269214796>⏳</emoji> <b>Осталось:</b> <code>{remaining}</code> сообщений\n"
            "<emoji document_id=5877613700344450910>⚡</emoji> <b>Скорость:</b> <code>{speed}</code> сообщений/мин"
        ),
        "panel_summary": "<b><emoji document_id=5231200819986047254>📊</emoji> ChatCopy Status</b>\n\n<b><emoji document_id=5249019346512008974>🔄</emoji> Активная:</b> {active}\n<b><emoji document_id=5316575093269214796>⏳</emoji> В очереди:</b> {queue_len}\n<b><emoji document_id=5220070652756635426>👀</emoji> Слежка:</b> {watching_count}\n<b><emoji document_id=5983150113483134607>⏱</emoji> Последний FW:</b> {last_flood}",
        "panel_task_running": "{name}\n├ <a href='tg://emoji?id=6030474915008745842'>📦</a> {count}/{total} сообщений\n├ <a href='tg://emoji?id=5190418524962570367'>⚡️</a> {speed}/мин | 📊 {progress}%\n├ ⏱ Прошло: {elapsed} | Осталось: {eta}\n└ 🕐 Начало: {start_time} | Окончание: {end_time}",
        "panel_task_paused": "{name}\n├ ⏸ На паузе (FW: {flood_time})\n├ 📦 {count}/{total} сообщений\n├ <a href='tg://emoji?id=5190418524962570367'>⚡️</a> {speed}/мин\n└ 🕐 Продолжение: {resume_time}",
        "btn_stop": "🛑 Стоп",
        "btn_pause": "⏸ Пауза",
        "btn_resume": "▶️ Продолжить",
        "btn_back": "🔙 Назад",
        "btn_tasks": "📋 Очередь задач",
        "btn_watch": "👀 Слежка",
        "btn_settings": "⚙️ Настройки",
        "btn_stats": "📊 Статистика",
        "btn_profiles": "📋 Профили",
        "profiles_title": "<b><a href='tg://emoji?id=5203910550542631009'>📋</a> Профили копирования</b>\n\n",
        "profiles_empty": "<i>Нет сохранённых профилей. Нажми «➕ Создать» чтобы добавить.</i>",
        "profiles_item": "{num}. {flags} {src} → {dst}{details}\n",
        "profiles_flags": "{filter}{auth}{capt}",
        "profiles_flag_filter_all": "📄",
        "profiles_flag_filter_media": "📎",
        "profiles_flag_filter_photo_video": "<a href='tg://emoji?id=5257974976094412956'>📷</a>",
        "profiles_flag_filter_docs": "💼",
        "profiles_flag_filter_text": "📝",
        "profiles_flag_noauth": "<a href='tg://emoji?id=5879770735999717115'>👤</a><a href='tg://emoji?id=5888558080173545731'>❌</a>",
        "profiles_flag_auth": "<a href='tg://emoji?id=5879770735999717115'>👤</a><a href='tg://emoji?id=5886277285035644362'>✅</a>",
        "profiles_flag_nocapt": "💬<a href='tg://emoji?id=5888558080173545731'>❌</a>",
        "profiles_flag_capt": "💬<a href='tg://emoji?id=5886277285035644362'>✅</a>",
        "profiles_btn_create": "➕ Создать",
        "profiles_btn_delete": "🗑 Удалить",
        "profiles_btn_reset": "🔄 Сбросить",
        "profiles_wizard_title": "<b>🛠 Создание профиля</b>\n\n",
        "profiles_wizard_ask_src": "<b>📥 Шаг 1/4:</b> Отправь ссылку, юзернейм или ID чата-<b>источника</b>.\n\nЕсли отправишь ссылку на сообщение, стартовый ID подтянется автоматически.\nПримеры: <code>@channel</code>, <code>-1001234567890</code>, <code>https://t.me/c/1234567890/12345</code>",
        "profiles_wizard_ask_dst": "<b>📤 Шаг 2/4:</b> Теперь отправь чат-<b>назначения</b>.\n\nМожно отправить ссылку на топик: <code>https://t.me/c/1234567890/1234</code>\nЕсли это ссылка на сообщение в топике, например <code>.../1234/123456</code>, назначением станет топик <code>6365</code>.",
        "profiles_wizard_ask_start": "<b>🔢 Шаг 3/4:</b> Откуда начинать копирование?\n\nИсточник: <b>{src}</b>\nНайдено из ссылки: <code>{detected}</code>\nСейчас выбрано: <code>{current}</code>\n\nОтправь ID сообщения/ссылку на сообщение или нажми кнопку ниже.",
        "profiles_wizard_ask_flags": "<b>⚙️ Шаг 4/4:</b> Проверь профиль и настрой флаги:\n\n📥 <b>Источник:</b> {src}\n📤 <b>Назначение:</b> {dst}\n🔢 <b>Старт:</b> {start}\n🧵 <b>Топик назначения:</b> {dest_topic}\n\n📎 <b>Фильтр:</b> {filter}\n👤 <b>Автор:</b> {auth}\n💬 <b>Подписи медиа:</b> {capt}\n🚫 <b>Игнор топиков:</b> {ignored}\n\n<i>Можно изменить любой шаг или сохранить профиль.</i>",
        "profiles_created": "✅ <b>Профиль #{num} сохранён!</b>\n{src} → {dst}\nСтарт: <code>{start}</code>\nКонец: <code>{end}</code>\nТопик назначения: <code>{dest_topic}</code>\nФлаги: {flags}",
        "profiles_updated": "✅ <b>Профиль #{num} обновлён!</b>\n{src} → {dst}\nСтарт: <code>{start}</code>\nКонец: <code>{end}</code>\nТопик назначения: <code>{dest_topic}</code>\nФлаги: {flags}",
        "profiles_detail": "<b>📋 Профиль #{num}</b>\n\n📥 <b>Источник:</b> {src}\n📤 <b>Назначение:</b> {dst}\n🔢 <b>Старт:</b> <code>{start}</code>\n➡️ <b>Следующий ID:</b> {next}\n🏁 <b>Конец:</b> <code>{end}</code>\n🧵 <b>Топик источника:</b> {src_topic}\n🧵 <b>Топик назначения:</b> {dest_topic}\n📎 <b>Фильтр:</b> {filter}\n👤 <b>Автор:</b> {auth}\n💬 <b>Подписи:</b> {capt}",
        "profiles_range_settings": "<b>🔢 Диапазон профиля #{num}</b>\n\nСтартовая точка: <code>{start}</code>\nСледующий запуск: {next}\nКонечный ID: <code>{end}</code>\n\nСтарт нужен как базовая точка и для сброса. После запуска профиль сам запоминает последний обработанный ID и продолжает дальше.",
        "profiles_range_ask_start": "<b>🔢 Новый стартовый ID для профиля #{num}</b>\n\nОтправь ID сообщения или ссылку на сообщение.\n<code>0</code> или <code>с начала</code> — сбросить старт.",
        "profiles_range_ask_end": "<b>🏁 Конечный ID для профиля #{num}</b>\n\nОтправь ID сообщения или ссылку на сообщение.\n<code>0</code> или <code>нет</code> — убрать ограничение.",
        "profiles_run_confirm": "<b>▶️ Подтвердить запуск профиля #{num}?</b>\n\n{src} → {dst}\nСледующий ID: {next}\nКонец: <code>{end}</code>\nТопик назначения: {dest_topic}",
        "profiles_deleted": "🗑 Профиль #{num} удалён.",
        "profiles_reset": "🔄 Профиль #{num} сброшен к стартовой точке.",
        "profiles_not_found": "❌ Профиль #{num} не найден.",
        "profiles_run_started": "▶️ <b>Запущен профиль #{num}</b>\n{src} → {dst}\nТопик назначения: <code>{dest_topic}</code>\nНачинаю поиск новых сообщений...",
        "profiles_run_done": "✅ <b>Профиль #{num} завершён</b>\nПереслано: {count} сообщений{flood_info}",
        "profiles_run_stopped": "🛑 <b>Профиль #{num} остановлен</b>\nПереслано: {count} сообщений",
        "profiles_wizard_cancelled": "❌ Создание профиля отменено.",
        "profiles_wizard_bad_entity": "❌ Не удалось найти чат. Попробуй другую ссылку или ID.",
        "profiles_btn_cancel_wizard": "❌ Отмена",
        "profiles_btn_next": "▶️ Далее",
        "profiles_btn_back_wizard": "◀️ Назад",
        "profiles_btn_from_start": "⏮ С начала",
        "profiles_btn_use_detected": "🔢 Использовать {id}",
        "profiles_btn_change_src": "✏️ Источник",
        "profiles_btn_change_dst": "✏️ Куда",
        "profiles_btn_change_start": "✏️ Старт",
        "profiles_btn_run": "▶️ Запустить",
        "profiles_btn_confirm_run": "✅ Да, запустить",
        "profiles_btn_edit": "✏️ Изменить",
        "profiles_btn_range": "🔢 Диапазон",
        "profiles_btn_set_start": "🔢 Старт",
        "profiles_btn_set_end": "🏁 Конец",
        "profiles_btn_clear_end": "♾ Без конца",
        "profiles_btn_toggle_filter": "📎 Фильтр: {val}",
        "profiles_btn_toggle_auth": "👤 Автор: {val}",
        "profiles_btn_toggle_capt": "💬 Подписи: {val}",
        "profiles_btn_save": "✅ Сохранить",
        "profile_run_header": "<b>▶️ Профиль #{num}</b>\n<b>{src}</b> → <b>{dst}</b>\n├ 📦 {count}/{total} сообщений\n├ ⚡ {speed}/мин | 📊 {progress}%\n├ ⏱ Прошло: {elapsed} | Осталось: {eta}\n└ 🕐 Начало: {start_time} | Окончание: {end_time}",
        "profiles_btn_run_all": "▶️ Запустить все",
        "forum_enabled": "✅ Топики включены в {chat}",
        "forum_enable_failed": "❌ Не удалось включить топики в {chat}. Нужны права администратора.",
        "forum_not_channel": "❌ {chat} не является каналом/группой",
        "err_ent": "❌ Ошибка: Чат не найден или нет доступа.",
        "args_err": "❌ Синтаксис: .chatcopy <src> <dest> [start_id:final_id] [-n] [-dmc] [--now] [--noflood] [--itopic 1|\"Имя\"] [-theme123] [--media|--photo_video|--docs|--text]\n.ccwatch <src> <dest> [start_id|last] [-n] [-dmc] [--itopic 1|\"Имя\"] [фильтр]",
        "watch_added": "<b>👀 Наблюдение активировано</b>\nID: <code>{src_id}</code>\n{src} -> {dest}\nРежим топиков: {topics}\nБез подписей: {no_capt}\nФильтр: {filter_type}\nИгнор топиков: {ignored}",
        "copy_restricted": "❌ <b>Источник защищён запретом копирования/пересылки Telegram.</b>\n\nМодуль остановлен до добавления в очередь: скрытый обход этой защиты не выполняется. Используй источник, где копирование разрешено, или отключи защиту в своём чате.",
        "queue_wait": "⏳ <b>Задача в очереди...</b> ({pos})",
        "topic_created": "📂 Создан топик: <b>{title}</b>",
        "topic_error": "❌ Ошибка создания топика: {error}",
        "task_stopped": "🛑 Задача остановлена\nПереслано: {count} сообщений{flood_info}",
        "stats_title": "<b>📊 Статистика ChatCopy</b>\n\n",
        "stats_total": "Всего задач: {total}\nЗавершено: {completed}\nОстановлено: {stopped}\nFloodWait'ов: {floods}",
        "task_list_header": "<b>📋 Очередь задач ({total})</b>\n\n<i>Нажми на номер для подробностей</i>\n\n",
        "task_item_compact_running": "▶️{num}. <b>{src}</b> → <b>{dest}</b> ({progress}%)",
        "task_item_compact_queued": "⏳{num}. <b>{src}</b> → <b>{dest}</b> (через {wait})",
        "task_item_compact_paused": "⚠️{num}. <b>{src}</b> → <b>{dest}</b> (FW)",
        "task_item_compact_completed": "✅{num}. <b>{src}</b> → <b>{dest}</b>",
        "task_item_compact_stopped": "🛑{num}. <b>{src}</b> → <b>{dest}</b> (останавливается)",
        "task_item_compact_error": "❌{num}. <b>{src}</b> → <b>{dest}</b>",
        "task_detail_running": "<b>▶️ Задача #{num}</b>\n\n<b>{src}</b> → <b>{dest}</b>\n├ Статус: <code>Выполняется</code>\n├ Прогресс: <code>{current}/{total}</code> ({progress}%)\n├ Скорость: <code>{speed}/мин</code>\n├ Прошло: <code>{elapsed}</code>\n├ Осталось: <code>{eta_left}</code>\n├ Начато: <code>{start_time}</code>\n├ Окончание: <code>{end_time}</code>\n└ Позиция: <code>{position}</code>",
        "task_detail_queued": "<b>⏳ Задача #{num}</b>\n\n<b>{src}</b> → <b>{dest}</b>\n├ Статус: <code>В очереди</code>\n├ Позиция: <code>{position}</code>\n├ Сообщений: <code>~{total}</code>\n├ Ожидание старта: <code>{eta_start}</code>\n└ Примерное время работы: <code>{estimated_duration}</code>",
        "task_detail_paused": "<b>⚠️ Задача #{num}</b>\n\n<b>{src}</b> → <b>{dest}</b>\n├ Статус: <code>Пауза (FloodWait)</code>\n├ Прогресс: <code>{current}/{total}</code> ({progress}%)\n├ FloodWait'ов: <code>{flood_count}</code>\n├ Время ожидания: <code>{flood_time}</code>\n├ Продолжение: <code>{resume_time}</code>\n├ Скорость до паузы: <code>{speed}/мин</code>\n└ Осталось сообщений: <code>{remaining}</code>",
        "task_detail_completed": "<b>✅ Задача #{num}</b>\n\n<b>{src}</b> → <b>{dest}</b>\n├ Статус: <code>Завершена</code>\n├ Переслано: <code>{count}</code> сообщений\n├ Длительность: <code>{duration}</code>\n├ Средняя скорость: <code>{avg_speed}/мин</code>\n├ Завершено: <code>{end_time}</code>\n└ FloodWait'ов: <code>{floods}</code>",
        "task_detail_error": "<b>❌ Задача #{num}</b>\n\n<b>{src}</b> → <b>{dest}</b>\n├ Статус: <code>Ошибка</code>\n└ Попробуйте перезапустить",
        "no_tasks": "<i>Нет активных задач</i>",
        "preparing": "<emoji document_id=5208722554591659638>💫</emoji> <b>Подготовка к копированию. Подсчитываем (да, вручную!) кол-во медиа, это может занять время...</b>",
    }

    def __init__(self):
        self._tasks = []
        self.config = loader.ModuleConfig(
            loader.ConfigValue("batch_size", 100, lambda: self.strings["cfg_batch"], validator=loader.validators.Integer(minimum=1, maximum=100)),
            loader.ConfigValue("delay", 10, lambda: self.strings["cfg_delay"], validator=loader.validators.Integer(minimum=1)),
            loader.ConfigValue("flood_buffer", 5, lambda: self.strings["cfg_flood_buffer"], validator=loader.validators.Integer(minimum=0, maximum=60)),
            loader.ConfigValue("timezone_offset", 3, lambda: self.strings["cfg_timezone"], validator=loader.validators.Integer(minimum=-12, maximum=14)),
        )
        self.queue = asyncio.Queue()
        self.dump_queue = asyncio.Queue()
        self.watcher_buffer = {}
        self.watcher_flush_tasks = {}
        self.watchlist = {}
        self.active_dumps = {}
        self._restricted_srcs = set()  # источники с запретом пересылки - обходим скачкой (bypass)
        self.last_watched = {}
        self.last_processed_ids = {}
        self.current_dump_task = None
        self.is_premium = False
        self.topic_mapping = {}
        self.topic_info_cache = {}
        self.task_stats = {}
        self.last_flood_info = {"time": None, "duration": 0, "task": None, "resume_at": None}
        self.task_queue = []
        self.task_history = []
        self.current_task_index = 0
        self.is_processing_queue = False
        self.task_progress_cache = {}
        self.global_speed_history = [] 
        self.avg_speed_history = []
        self._queue_lock = asyncio.Lock()
        self._send_lock = asyncio.Lock()
        self._task_counter = 0
        self.profiles = {}
        self._wizard_state = {}
        self._last_panel_cid = 0

    async def client_ready(self, client, db):
        global _cc_client, _cc_log_channel, _cc_log_topic_id
        self.client = client
        self.db = db
        self.watchlist = self.db.get("ChatCopy", "watchlist", {})
        self.last_processed_ids = self.db.get("ChatCopy", "last_processed_ids", {})
        self.topic_mapping = self.db.get("ChatCopy", "topic_mapping", {})
        self.task_stats = self.db.get("ChatCopy", "task_stats", {})
        self.task_queue = self.db.get("ChatCopy", "persistent_queue", [])
        self.profiles = self.db.get("ChatCopy", "profiles", {})
        self._cleanup_bypass_tmp()
        for task in self.task_queue:
            task['status'] = 'queued'
        me = await client.get_me()
        self.is_premium = getattr(me, 'premium', False)
        try:
            asset_channel = (
                self.db.get("heroku.forums", "channel_id", 0)
                or self.db.get("heroku.forums", "forum_id", 0)
            )
            if asset_channel:
                notif_topic = await utils.asset_forum_topic(
                    self.client,
                    self.db,
                    asset_channel,
                    "ChatCopy Logs",
                    description="ChatCopy module activity logs (warnings & errors).",
                    icon_emoji_id=5372917041193828849,
                )
                _cc_client = self.client
                _cc_log_channel = asset_channel
                _cc_log_topic_id = notif_topic.id
                logger.info("ChatCopy log topic ready (id=%s)", _cc_log_topic_id)
        except Exception as _e:
            logger.debug("ChatCopy log topic setup skipped: %s", _e)
        self._tasks.extend([
            asyncio.create_task(self.worker()),
            asyncio.create_task(self.dump_worker()),
            asyncio.create_task(self._catch_up_on_restart())
        ])
        if not self.task_queue:
            return
        logger.info(f"Возобновление {len(self.task_queue)} задач из очереди после перезапуска.")
        for task in self.task_queue:
            try:
                src = await self.client.get_entity(task['src_id'])
                dest = await self.client.get_entity(task['dest_id'])
                class FakeMsg:
                    id = None
                    chat_id = task.get('status_chat_id')
                    async def edit(self, *args, **kwargs): pass
                await self.dump_queue.put({
                    "status_msg": FakeMsg(),
                    "src": src, "dest": dest,
                    "no_auth": task['no_author'], "no_captions": task['no_captions'],
                    "map_t": task.get('map_t', False), "f_src_t": task.get('f_src_t'),
                    "f_dest_t": task.get('f_dest_t'), "tid": task['tid'],
                    "min_id": task.get('last_processed_id', task.get('start_id', 0)),
                    "max_id": task.get('final_id', 0),
                    "filter_type": task['filter_type'], "src_name": task['src'],
                    "total_msgs": task['total_msgs'],
                    "restored_count": task.get('current', 0),
                    "ignored_topics": task.get('ignored_topics', []),
                })
            except Exception as e:
                logger.error(f"Не удалось возобновить задачу {task.get('tid')}: {e}")

    def _tz(self):
        offset = self.config.get("timezone_offset", 3)
        try:
            offset = int(offset)
        except (TypeError, ValueError):
            offset = 3
        offset = max(-12, min(14, offset))
        sign = "+" if offset >= 0 else "-"
        name = "MSK" if offset == 3 else f"UTC{sign}{abs(offset):02d}:00"
        return timezone(timedelta(hours=offset), name=name)

    def _now(self):
        return datetime.now(self._tz())

    def _time_from_ts(self, timestamp):
        return datetime.fromtimestamp(timestamp, self._tz())

    def _format_clock(self, value=None):
        if value is None:
            value = self._now()
        if isinstance(value, (int, float)):
            value = self._time_from_ts(value)
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=MSK).astimezone(self._tz())
            else:
                value = value.astimezone(self._tz())
            return value.strftime("%H:%M:%S")
        return str(value)

    def _inline_html(self, text):
        """Converts normal premium emoji HTML to inline-compatible tg-emoji tags."""
        if text is None:
            return text
        return re.sub(
            r'<emoji\s+document_id=["\']?(\d+)["\']?>(.*?)</emoji>',
            r'<tg-emoji emoji-id=\1>\2</tg-emoji>',
            str(text),
            flags=re.DOTALL,
        )

    def _default_html(self, text):
        """Always uses premium emoji, no fallback stripping."""
        return text

    async def _inline_edit(self, call, text, **kwargs):
        """Edits inline panels; change inline text in strings, this adapts emoji tags."""
        return await call.edit(self._inline_html(text), **kwargs)

    def _default_text_key(self, key):
        """Always returns premium key, no fallback."""
        return key

    def _split_args(self, message):
        raw = utils.get_args_raw(message)
        try:
            return shlex.split(raw)
        except ValueError:
            return raw.split()

    def _normalize_topic_selector(self, value):
        value = str(value).strip().strip("\"'").strip()
        value = value.strip("{}")
        return value.lower()

    def _format_ignored_topics(self, ignored_topics):
        return ", ".join(ignored_topics) if ignored_topics else "Нет"

    def _topic_id_from_message(self, msg):
        topic_id = None
        if hasattr(msg, 'reply_to') and msg.reply_to:
            topic_id = getattr(msg.reply_to, 'reply_to_top_id', None) or getattr(msg.reply_to, 'reply_to_msg_id', None)
        if not topic_id and hasattr(msg, 'topic_id') and msg.topic_id:
            topic_id = msg.topic_id
        return topic_id

    def _topic_is_ignored(self, topic_id, title=None, ignored_topics=None):
        if not ignored_topics:
            return False
        topic_id = topic_id if topic_id not in (None, "no_topic") else 1
        checks = {str(topic_id).lower()}
        if title:
            checks.add(str(title).strip().lower())
        return any(item in ignored_topics for item in checks)

    def _is_copy_restricted_error(self, exc):
        name = exc.__class__.__name__.lower()
        text = str(exc).lower()
        return (
            "forwardsrestricted" in name
            or "noforwards" in text
            or "content is protected" in text
            or "forwards restricted" in text
            or "forbidden to forward" in text
        )

    async def _source_has_copy_restriction(self, entity):
        if getattr(entity, 'noforwards', False):
            return True
        try:
            async for msg in self.client.iter_messages(entity, limit=5):
                if getattr(msg, 'noforwards', False):
                    return True
        except Exception as e:
            logger.debug("Не удалось проверить запрет копирования: %s", e)
        return False

    async def _report_copy_restricted(self, status_msg, tid=None):
        if tid and tid in self.active_dumps:
            self.active_dumps[tid]["status"] = "error"
            self.active_dumps[tid]["protected_error"] = True
        try:
            await utils.answer(status_msg, self.strings["copy_restricted"])
        except Exception:
            try:
                chat_id = getattr(status_msg, "chat_id", None)
                if chat_id:
                    await self.client.send_message(chat_id, self.strings["copy_restricted"])
            except Exception:
                pass

    async def _get_forum_topics(self, chat_entity, max_pages=50):
        topics = []
        seen = set()
        offset_date = None
        offset_id = 0
        offset_topic = 0
        for _ in range(max_pages):
            try:
                result = await self.client(functions.messages.GetForumTopicsRequest(
                    peer=chat_entity,
                    offset_date=offset_date,
                    offset_id=offset_id,
                    offset_topic=offset_topic,
                    limit=100,
                ))
            except errors.FloodWaitError as e:
                await asyncio.sleep(e.seconds + self.config["flood_buffer"])
                continue
            except Exception as e:
                logger.debug("GetForumTopics failed: %s", e)
                break
            page = getattr(result, 'topics', None) or []
            if not page:
                break
            added = 0
            for topic in page:
                topic_id = getattr(topic, 'id', None)
                if topic_id in seen:
                    continue
                seen.add(topic_id)
                topics.append(topic)
                added += 1
            if added == 0 or len(page) < 100:
                break
            last = page[-1]
            offset_topic = getattr(last, 'id', 0) or offset_topic
            offset_id = getattr(last, 'top_message', 0) or offset_id
            offset_date = getattr(last, 'date', 0) or offset_date
        return topics

    async def _precreate_topics(self, src_entity, dest_entity, ignored_topics=None, selected_topic=None, tid=None):
        if not src_entity or not dest_entity or not self._is_forum(src_entity) or not self._is_forum(dest_entity):
            return 0
        topics = await self._get_forum_topics(src_entity)
        created = 0
        for topic in topics:
            topic_id = getattr(topic, 'id', None)
            title = getattr(topic, 'title', None) or f"Topic {topic_id}"
            if selected_topic and topic_id != selected_topic:
                continue
            if self._topic_is_ignored(topic_id, title, ignored_topics):
                logger.info("[%s] Топик пропущен по игнору: %s (%s)", tid, title, topic_id)
                continue
            if topic_id == 1:
                continue
            mapped = await self._ensure_topic_mapping(src_entity, dest_entity, topic_id)
            if mapped:
                created += 1
                logger.info("[%s] Топик готов: %s (%s → %s)", tid, title, topic_id, mapped)
            await asyncio.sleep(0.4)
        if created:
            logger.info("[%s] Подготовлено топиков: %d", tid, created)
        return created

    async def _resolve_arg(self, arg):  # все виды (ну почти) ссылок как дадут id и прочее, 
                                        # работает если копировать сообщение в топике и в аргумент типа куда отправлять вставить.
        extra = {}
        entity = None
        arg = str(arg).strip()
        regex = r"(?:t\.me/|tg://resolve\?domain=|tg://openmessage\?user_id=)(?:c/)?([\w\d_]+)(?:/(\d+))?(?:/(\d+))?"
        match = re.search(regex, arg)
        if match:
            identifier = match.group(1)
            num1 = int(match.group(2)) if match.group(2) else None
            num2 = int(match.group(3)) if match.group(3) else None
            if identifier.isdigit():
                for potential_id in [int(identifier), int(f"-100{identifier}")]:
                    try:
                        entity = await self.client.get_entity(potential_id)
                        if entity: break
                    except Exception:
                        continue
            else:
                try:
                    entity = await self.client.get_entity(identifier)
                except Exception:
                    pass
            is_forum_target = self._is_forum(entity) if entity else False
            if num1 is not None and num2 is not None:
                extra['topic'] = num1
                extra['msg'] = num2
            elif num1 is not None:
                if is_forum_target:
                    extra['topic'] = num1
                else:
                    extra['msg'] = num1
        else:
            try:
                if arg.lstrip("-").isdigit():
                    entity = await self.client.get_entity(int(arg))
                else:
                    entity = await self.client.get_entity(arg)
            except Exception:
                pass
        return entity, extra

    def _get_normalized_id(self, entity): # что бы получать норм айди а не нечто, что бы копировка шла хорошо.
        if not entity:
            return "0"
        try:
            return str(tl_utils.get_peer_id(entity))
        except Exception:
            pass
        try:
            return str(utils.get_chat_id(entity))
        except Exception:
            if hasattr(entity, 'id') and entity.id:
                eid = str(entity.id)
                if isinstance(entity, Channel) and not eid.startswith("-100") and len(eid) > 9: 
                     return f"-100{eid}"
                if isinstance(entity, Channel) and not eid.startswith("-"):
                     return f"-100{eid}"
                return eid
            return "0"

    def _is_forum(self, entity): # да, не спрашивайте.
        if not isinstance(entity, Channel):
            return False
        if hasattr(entity, 'forum') and entity.forum:
            return True
        if hasattr(entity, 'flags') and entity.flags is not None:
            return bool(entity.flags & (1 << 30))
        return False

    async def _ensure_forum_enabled(self, entity): # проверяет режим топиков у чата и пытается включить его, если он отключен (требуются права админа).
        if not isinstance(entity, Channel):
            return False
        if self._is_forum(entity):
            return True
        try:
            result = await self.client(functions.channels.ToggleForumRequest(channel=entity, enabled=True))
            if result:
                updated_entity = await self.client.get_entity(entity.id)
                return self._is_forum(updated_entity)
            return False
        except errors.FloodWaitError as e:
            await asyncio.sleep(e.seconds + self.config["flood_buffer"])
            return await self._ensure_forum_enabled(entity)
        except errors.ChatAdminRequiredError:
            return False
        except Exception:
            return False

    async def _get_topic_info(self, chat_entity, topic_id): #получаем инфо о топике для копирования
        if not topic_id:
            return None, None, None
        cache_key = f"{chat_entity.id}_{topic_id}"
        if cache_key in self.topic_info_cache:
            return self.topic_info_cache[cache_key]
        title, icon_emoji_id, icon_color = None, None, None
        for attempt in range(3):
            try:
                result = await self.client(functions.messages.GetForumTopicsByIDRequest(peer=chat_entity, topics=[topic_id]))
                if result and hasattr(result, 'topics') and result.topics:
                    for topic in result.topics:
                        if hasattr(topic, 'id') and topic.id == topic_id:
                            title = getattr(topic, 'title', None)
                            icon_emoji_id = getattr(topic, 'icon_emoji_id', None)
                            icon_color = getattr(topic, 'icon_color', None)
                            break
                if title:
                    break
            except errors.FloodWaitError as e:
                await asyncio.sleep(e.seconds + self.config["flood_buffer"])
            except Exception:
                pass
        if not title:
            try:
                result = await self.client(functions.messages.GetForumTopicsRequest(peer=chat_entity, offset_date=None, offset_id=0, offset_topic=0, limit=100))
                if result and hasattr(result, 'topics'):
                    for topic in result.topics:
                        if hasattr(topic, 'id') and topic.id == topic_id:
                            title = getattr(topic, 'title', None)
                            icon_emoji_id = getattr(topic, 'icon_emoji_id', None)
                            icon_color = getattr(topic, 'icon_color', None)
                            break
            except Exception:
                pass
        if not title:
            try:
                async for msg in self.client.iter_messages(chat_entity, limit=1, reply_to=topic_id):
                    if msg and hasattr(msg, 'reply_to') and msg.reply_to:
                        title = getattr(msg.reply_to, 'forum_topic_title', None)
                    if not title and msg:
                        title = msg.text[:50] if msg.text else f"Topic {topic_id}"
                    break
            except Exception:
                pass
        if not title:
            title = f"Topic {topic_id}"
        info = (title, icon_emoji_id, icon_color)
        self.topic_info_cache[cache_key] = info
        return info

    async def _create_topic(self, dest_entity, title, src_topic_id=None, icon_emoji_id=None, icon_color=None): # создает топик 
        if not isinstance(dest_entity, Channel) or not self._is_forum(dest_entity):
            return None
        try:
            random_id = random.randint(1, 2**63 - 1)
            if icon_emoji_id and not self.is_premium:
                logger.debug("Сбрасываем premium icon_emoji_id для топика %s: аккаунт без Premium", title)
                icon_emoji_id = None
            kwargs = {
                "peer": dest_entity,
                "title": title[:128] if len(title) > 128 else title,
                "random_id": random_id
            }
            if icon_emoji_id:
                kwargs["icon_emoji_id"] = icon_emoji_id
            elif icon_color:
                kwargs["icon_color"] = icon_color
            else:
                kwargs["icon_color"] = 0x6FB9F0
            result = await self.client(functions.messages.CreateForumTopicRequest(**kwargs))
            new_topic_id = None
            if result:
                if hasattr(result, 'updates'):
                    for update in result.updates:
                        if hasattr(update, 'message'):
                            msg = update.message
                            if hasattr(msg, 'action') and hasattr(msg.action, 'topic_id'):
                                new_topic_id = msg.action.topic_id
                            if hasattr(msg, 'reply_to') and msg.reply_to:
                                new_topic_id = getattr(msg.reply_to, 'reply_to_top_id', None) or getattr(msg.reply_to, 'reply_to_msg_id', None)
                                if new_topic_id:
                                    break
                if not new_topic_id and hasattr(result, 'messages') and result.messages:
                    for msg in result.messages:
                        if hasattr(msg, 'reply_to') and msg.reply_to:
                            new_topic_id = getattr(msg.reply_to, 'reply_to_top_id', None)
                            if new_topic_id:
                                break
                if not new_topic_id:
                    await asyncio.sleep(1)
                    topics_result = await self.client(functions.messages.GetForumTopicsRequest(peer=dest_entity, offset_date=None, offset_id=0, offset_topic=0, limit=20))
                    if topics_result and hasattr(topics_result, 'topics'):
                        for topic in topics_result.topics:
                            if getattr(topic, 'title', '') == title:
                                new_topic_id = topic.id
                                break
            return new_topic_id
        except errors.FloodWaitError as e:
            await asyncio.sleep(e.seconds + self.config["flood_buffer"])
            return await self._create_topic(dest_entity, title, src_topic_id, icon_emoji_id, icon_color)
        except errors.TopicDeletedError:
            return None
        except Exception:
            return None

    async def _ensure_topic_mapping(self, src_entity, dest_entity, src_topic_id): # копирует точ в точ топик.
        if not src_topic_id:
            return None
        mapping_key = f"{src_entity.id}_{dest_entity.id}_{src_topic_id}"
        if mapping_key in self.topic_mapping:
            cached_id = self.topic_mapping[mapping_key]
            try:
                await self.client(functions.messages.GetForumTopicsByIDRequest(peer=dest_entity, topics=[cached_id]))
                return cached_id
            except Exception:
                pass
        title, icon_emoji_id, icon_color = await self._get_topic_info(src_entity, src_topic_id)
        if not title:
            title = f"Topic {src_topic_id}"
        if icon_emoji_id and not self.is_premium:
            icon_emoji_id = None
        try:
            offset_date = None
            offset_id = 0
            offset_topic = 0
            found_topic_id = None
            for _ in range(5): 
                topics_result = await self.client(functions.messages.GetForumTopicsRequest(
                    peer=dest_entity, offset_date=offset_date, offset_id=offset_id, offset_topic=offset_topic, limit=100
                ))
                if not topics_result or not hasattr(topics_result, 'topics') or not topics_result.topics:
                    break
                for topic in topics_result.topics:
                    if getattr(topic, 'title', '') == title:
                        if icon_emoji_id:
                            if getattr(topic, 'icon_emoji_id', None) == icon_emoji_id:
                                found_topic_id = topic.id
                                break
                        else:
                            found_topic_id = topic.id
                            break
                if found_topic_id:
                    break
                offset_topic = topics_result.topics[-1].id
            if found_topic_id:
                self.topic_mapping[mapping_key] = found_topic_id
                self.db.set("ChatCopy", "topic_mapping", self.topic_mapping)
                return found_topic_id
        except Exception as e:
            logger.error(f"Error checking existing topics: {e}")
        for attempt in range(3):
            new_topic_id = await self._create_topic(dest_entity, title, src_topic_id, icon_emoji_id, icon_color)
            if new_topic_id:
                self.topic_mapping[mapping_key] = new_topic_id
                self.db.set("ChatCopy", "topic_mapping", self.topic_mapping)
                return new_topic_id
            await asyncio.sleep(5)
        return None

    async def on_unload(self):
        """Остановка всех задач при выгрузке модуля"""
        for task in self._tasks:
            if not task.done(): task.cancel()
        for tid in list(self.active_dumps.keys()):
            self.active_dumps[tid]["status"] = "stopped"
            if "cancel" in self.active_dumps[tid]: self.active_dumps[tid]["cancel"].set()
        for t in self.watcher_flush_tasks.values(): t.cancel()

    def _should_include_message(self, msg, filter_type): # handler типов сообщений. медиа, документ и прочее.
        if filter_type == FILTER_ALL:
            return True
        has_photo = bool(msg.photo)
        has_video = bool(msg.video)
        has_video_note = bool(msg.video_note)
        has_document = bool(msg.document)
        has_voice = bool(msg.voice)
        has_audio = bool(msg.audio)
        has_sticker = bool(msg.sticker)
        has_text = bool(msg.text and not msg.media)
        is_gif = False
        if has_document and not has_sticker and hasattr(msg.document, 'attributes'):
            for attr in msg.document.attributes:
                if isinstance(attr, types.DocumentAttributeAnimated):
                    is_gif = True
                    break
        is_file_document = has_document and not (has_video or has_video_note or has_audio or has_voice or has_sticker or is_gif or has_photo)
        if has_video and has_sticker:
            has_video = False
        if has_document and not has_photo and not has_sticker:
            doc = msg.document
            if hasattr(doc, 'mime_type'):
                mime = doc.mime_type or ''
                if mime.startswith('image/'):
                    has_photo = True
                    is_file_document = False
                elif mime.startswith('video/') and not is_gif:
                    has_video = True
                    is_file_document = False
        if filter_type == FILTER_MEDIA:
            return has_photo or has_video or is_file_document
        elif filter_type == FILTER_PHOTO_VIDEO:
            return (has_photo or has_video) and not (has_sticker or is_gif)
        elif filter_type == FILTER_DOCS:
            return is_file_document
        elif filter_type == FILTER_TEXT:
            return has_text and not (has_photo or has_video or has_video_note or has_document or has_sticker or has_voice or has_audio or is_gif)
        return True

    async def _send_flood_notice(self, chat_id, seconds, count, 
    task_id, total_msgs=0, speed=0, path="пересылка"): # ниже этой функции, функция обработки флудвейта, он просто отправляет примерное время когда продолжит работать.
        minutes = seconds // 60
        secs = seconds % 60
        resume_time = (self._now() + timedelta(seconds=seconds + self.config["flood_buffer"])).strftime("%H:%M:%S")
        remaining = max(0, total_msgs - count)
        _ad = self.active_dumps.get(task_id, {})
        _fwd_left, _alt_left = self._flood_state(task_id)
        flood_path = path
        if _ad.get("noflood"):
            if _fwd_left <= 0:
                working = "пересылка"
            elif _alt_left <= 0:
                working = "скачка"
            else:
                working = "ожидание (оба пути на FloodWait)"
        else:
            working = "ожидание возобновления"
        _sig = f"{flood_path}|{working}"
        if _ad.get("_flood_notice_sig") == _sig:
            return
        _ad["_flood_notice_sig"] = _sig
        self.last_flood_info = {
            "time": self._format_clock(),
            "duration": seconds,
            "task": task_id,
            "resume_at": resume_time
        }
        try:
            await self.client.send_message(
                chat_id,
                self.strings["flood_wait_notice"].format(
                    minutes=minutes,
                    seconds=secs,
                    resume_time=resume_time,
                    count=count,
                    remaining=remaining,
                    speed=round(speed, 1),
                    flood_path=flood_path,
                    working=working
                )
            )
        except Exception:
            pass

    def _format_flood_stats(self, task_data): # формирует красивую строку со статистикой FloodWait для вывода в итоговом сообщении.
        floods = task_data.get('flood_count', 0)
        total_seconds = task_data.get('flood_total_seconds', 0)
        if floods == 0:
            return ""
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        if hours > 0:
            time_str = f"{hours}h {minutes}m"
        else:
            time_str = f"{minutes}m"
        return f"\n⏱ <b>{floods} FloodWait (~{time_str})</b>"

    def _format_duration(self, seconds): # описание ниже
        """Форматирует длительность в читаемый вид"""
        if seconds < 60:
            return f"{int(seconds)}с"
        elif seconds < 3600:
            return f"{int(seconds // 60)}м {int(seconds % 60)}с"
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            return f"{hours}ч {mins}м"

    async def _process_batch(self, messages, dest_id, no_author, 
    no_captions=False, fixed_dest_topic=None, map_topics=False, dest_entity=None, 
    src_entity=None, filter_type=FILTER_ALL, status_msg=None, tid=None, ignored_topics=None): 
        if not messages: 
            return 0
        if tid and tid in self.active_dumps:
            await self.active_dumps[tid].get("cancel", asyncio.Event()).wait()
            if self.active_dumps[tid].get("status") in ("stopped", "error"):
                return 0
        filtered_messages = [msg for msg in messages if self._should_include_message(msg, filter_type)]
        if not filtered_messages:
            return 0
        if map_topics and (not dest_entity or isinstance(dest_entity, (int, str))):
            try:
                dest_entity = await self.client.get_entity(dest_id)
            except Exception:
                map_topics = False
        if map_topics and not src_entity:
            try:
                src_entity = await self.client.get_entity(filtered_messages[0].chat_id)
            except Exception:
                pass
        msg_groups = {}
        for msg in filtered_messages:
            src_topic_id = None
            if map_topics and src_entity and dest_entity:
                src_topic_id = self._topic_id_from_message(msg)
            key = src_topic_id if src_topic_id else "no_topic"
            msg_groups.setdefault(key, []).append(msg)
        total_sent = 0
        delay = self.config["delay"]
        if not isinstance(delay, int):
            delay = 10
        for src_topic_id, msgs in msg_groups.items():
            if ignored_topics:
                topic_title = None
                if src_topic_id != "no_topic" and src_entity:
                    topic_title, _, _ = await self._get_topic_info(src_entity, src_topic_id)
                if self._topic_is_ignored(src_topic_id, topic_title, ignored_topics):
                    logger.info("[%s] Пропуск топика по игнору: %s (%s)", tid, topic_title or "General", src_topic_id)
                    continue
            if tid and tid in self.active_dumps:
                await self.active_dumps[tid].get("cancel", asyncio.Event()).wait()
                if self.active_dumps[tid].get("status") in ("stopped", "error"):
                    break
            target_topic = fixed_dest_topic
            if map_topics and src_topic_id != "no_topic" and int(src_topic_id) != 1:
                target_topic = await self._ensure_topic_mapping(src_entity, dest_entity, src_topic_id)
                if not target_topic:
                    logger.error("[%s] Не удалось создать/найти топик назначения для source topic %s", tid, src_topic_id)
                    if tid and tid in self.active_dumps:
                        self.active_dumps[tid]["status"] = "error"
                    break
            if tid and tid in self.active_dumps:
                last_send = self.active_dumps[tid].get("last_successful_send", 0)
                time_since_last = time.time() - last_send
                min_interval = 3
                if time_since_last < min_interval:
                    extra_wait = min_interval - time_since_last
                    logger.debug(f"[{tid}] Дополнительная задержка для соблюдения интервала: {extra_wait:.1f}с")
                    await asyncio.sleep(extra_wait)
            success = await self._raw_sender(msgs, dest_id, no_author, no_captions, target_topic, status_msg, tid)
            if success:
                total_sent += len(msgs)
                if tid and tid in self.active_dumps:
                    self.active_dumps[tid]["last_successful_send"] = time.time()
            elif tid and tid in self.active_dumps and self.active_dumps[tid].get("status") in ("stopped", "error"):
                break
            else:
                logger.error("[%s] Отправка пачки не удалась, останавливаю задачу без продвижения last_processed_id", tid)
                if tid and tid in self.active_dumps:
                    self.active_dumps[tid]["status"] = "error"
                break
            await asyncio.sleep(delay)
        return total_sent

    async def worker(self): # воркер для Watcher'а
        while True:
            item = await self.queue.get()
            try:
                watch_cid = item.pop("watch_cid", None)
                if watch_cid and watch_cid not in self.watchlist:
                    logger.debug(f"Игнорируем сообщение для {watch_cid}, слежка была остановлена")
                    continue
                messages = item.get("messages") or []
                result = await self._process_batch(**item)
                if watch_cid and messages:
                    if result >= len(messages):
                        last_msg = max(messages, key=lambda msg: msg.id)
                        self.last_processed_ids[watch_cid] = last_msg.id
                        self.db.set("ChatCopy", "last_processed_ids", self.last_processed_ids)
                    else:
                        logger.warning(
                            "Watcher batch for %s was not fully sent (%s/%s), last_processed_id not advanced",
                            watch_cid, result, len(messages)
                        )
            except Exception as e:
                logger.error(f"Worker error: {e}")
            finally:
                self.queue.task_done()

    async def dump_worker(self):
        """worker очереди, с последовательным выполнением задач""" # он типа очень умни и если добавить последовательно несколько чатов,
                                                                   # то он не переключится а просто в очередь добавит
        while True:
            task_data = await self.dump_queue.get()
            tid = task_data.get('tid')
            update_task = None
            try:
                async with self._queue_lock:
                    self.is_processing_queue = True
                    self.current_dump_task = tid
                    self._update_queue_positions()
                    idx = next((i for i, t in enumerate(self.task_queue) if t.get('tid') == tid), None)
                    if idx is not None:
                        self.task_queue[idx]['status'] = 'running'
                        self.task_queue[idx]['start_time'] = time.time()
                        self.current_task_index = idx
                    if tid:
                        self.active_dumps[tid] = {
                            "current": task_data.get('restored_count', 0),
                            "cancel": asyncio.Event(),
                            "name": task_data.get('src_name', 'Unknown'),
                            "src": task_data.get('src_name', 'Unknown'),
                            "dest": getattr(task_data.get('dest'), 'title', task_data.get('dest', 'Unknown')),
                            "status": "running",
                            "start_time": time.time(),
                            "flood_count": 0,
                            "flood_total_seconds": 0,
                            "noflood": bool(task_data.get('noflood')),
                            "fwd_until": 0,
                            "bypass_until": 0,
                            "last_flood_path": None,
                            "status_msg_id": task_data.get('status_msg').id if task_data.get('status_msg') else None,
                            "status_chat_id": task_data.get('status_msg').chat_id if task_data.get('status_msg') else None,
                            "total_estimated": task_data.get('total_msgs', 0),
                            "last_update_time": time.time(),
                            "last_update_count": 0,
                            "last_successful_send": time.time(),
                            "consecutive_floods": 0,
                            "speed_samples": [],
                            "current_speed": 0,
                        }
                        self.active_dumps[tid]["cancel"].set()
                    self._save_tasks()
                update_task = asyncio.create_task(self._auto_update_status(tid, task_data.get('status_msg')))
                logger.info("[%s] Задача запущена: %s → %s | Всего: %d сообщений",
                            tid, task_data.get('src_name', '?'),
                            getattr(task_data.get('dest'), 'title', '?'),
                            task_data.get('total_msgs', 0))
                await self._history_dumper(**task_data)
            except Exception as e:
                logger.error(f"Dump Worker Error: {e}", exc_info=True)
                if tid and tid in self.active_dumps:
                    self.active_dumps[tid]["status"] = "error"
            finally:
                if update_task:
                    update_task.cancel()
                last_task = None
                sent_count = 0
                async with self._queue_lock:
                    if tid in self.active_dumps:
                        completed_task = self.active_dumps[tid].copy()
                        completed_task['tid'] = tid
                        completed_task['end_time'] = self._now()
                        sent_count = completed_task.get('current', 0)
                        self.task_history.append(completed_task)
                        self.task_queue = [t for t in self.task_queue if t['tid'] != tid]
                        duration = time.time() - completed_task.get('start_time', time.time())
                        active_duration = duration - completed_task.get('flood_total_seconds', 0)
                        if active_duration <= 0:
                            active_duration = 1
                        avg_spd = (sent_count / active_duration) * 60
                        self.task_stats[tid] = {
                            'completed_at': time.time() if completed_task.get('status') == 'completed' else None,
                            'flood_count': completed_task.get('flood_count', 0),
                            'flood_time': completed_task.get('flood_total_seconds', 0),
                            'avg_speed': avg_spd
                        }
                        self.db.set("ChatCopy", "task_stats", self.task_stats)
                        self.active_dumps.pop(tid, None)
                        last_task = completed_task
                    self.current_dump_task = None
                    self.is_processing_queue = False
                    self._save_tasks()
                    self.dump_queue.task_done()
                logger.info("[%s] Задача завершена. Переслано: %d", tid, sent_count)
                if last_task and last_task.get('flood_count', 0) > 0:
                    final_wait = min(60 * last_task['flood_count'], 300)
                    logger.info(f"Финальная задержка после задачи с FloodWait'ами: {final_wait}с")
                    await asyncio.sleep(final_wait)

    def _update_queue_positions(self): # описание ниже
        """Обновляет позиции задач в очереди"""
        queued_tasks = [t for t in self.task_queue if t['status'] == 'queued']
        for i, task in enumerate(queued_tasks, 1):
            task['position'] = i

    async def _auto_update_status(self, tid, status_msg): # описание ниже
        """Обновляет только внутренний кэш скорости без редактирования сообщения"""
        while True:
            try:
                await asyncio.sleep(5)
                if tid not in self.active_dumps:
                    break
                task = self.active_dumps[tid]
                status = task.get('status', 'unknown')
                if status not in ['running', 'paused']:
                    continue
                current = task.get('current', 0)
                total = task.get('total_estimated', 0)
                start_time = task.get('start_time', time.time())
                elapsed = time.time() - start_time
                now = time.time()
                last_calc_time = task.get('_last_calc_time', now - 5)
                last_calc_count = task.get('_last_calc_count', current)
                delta_t = now - last_calc_time
                delta_c = current - last_calc_count
                if status == 'running':
                    if delta_t > 0:
                        inst_speed = (delta_c / delta_t) * 60
                        task['speed_samples'].append(inst_speed)
                        if len(task['speed_samples']) > 12:
                            task['speed_samples'].pop(0)
                    task['_last_calc_time'] = now
                    task['_last_calc_count'] = current
                avg_speed = sum(task['speed_samples']) / len(task['speed_samples']) if task['speed_samples'] else 0
                task['current_speed'] = avg_speed
                if avg_speed > 0:
                    self.global_speed_history.append(avg_speed)
                    if len(self.global_speed_history) > 50:
                        self.global_speed_history.pop(0)
                self.task_progress_cache[tid] = {
                    'current': current,
                    'speed': round(avg_speed, 1),
                    'eta': self._calculate_eta(current, total, avg_speed),
                    'progress': round((current / total * 100), 1) if total > 0 else 0,
                    'elapsed': elapsed,
                    'status': status
                }
                # прогресс идёт в логи через logger.info
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Auto update error: {e}")

    def _get_avg_speed(self): # описание ниже
        """Получает среднюю скорость из глобальной истории"""
        if not self.global_speed_history:
            return 100
        return sum(self.global_speed_history) / len(self.global_speed_history)

    def _calculate_eta(self, current, total, speed_per_min): # описание ниже
        """Расчёт оставшегося времени"""
        if speed_per_min <= 0 or total <= 0:
            return "∞"
        remaining = total - current
        minutes = remaining / speed_per_min
        return self._format_duration(minutes * 60)

    def _calculate_task_wait_time(self, target_position): # описание ниже
        """Расчёт времени ожидания для задачи в очереди"""
        avg_speed = self._get_avg_speed()
        total_seconds = 0
        for task in self.task_queue:
            if task['position'] < target_position and task['status'] not in ['completed', 'stopped', 'error']:
                remaining = task.get('total_msgs', 0) - task.get('current', 0)
                if remaining > 0:
                    task_seconds = (remaining / avg_speed) * 60 if avg_speed > 0 else 3600
                    total_seconds += task_seconds
        return self._format_duration(total_seconds)

    def _estimate_duration(self, total_msgs): # описание ниже
        """Оценка длительности задачи"""
        avg_speed = self._get_avg_speed()
        if avg_speed <= 0 or total_msgs <= 0:
            return "∞"
        minutes = total_msgs / avg_speed
        return self._format_duration(minutes * 60)

    def _calculate_end_time(self, start_time, total_msgs, speed_per_min=None): # описание ниже
        """Расчёт времени окончания задачи"""
        if speed_per_min is None:
            speed_per_min = self._get_avg_speed()
        if speed_per_min <= 0 or total_msgs <= 0:
            return "∞"
        minutes = total_msgs / speed_per_min
        end_time = start_time + timedelta(minutes=minutes)
        return end_time.strftime("%H:%M:%S")

    async def _raw_sender(self, messages, dest_id, no_author, no_captions, topic_id, status_msg=None, tid=None): # описание ниже
        """Единая точка отправки: один аккаунт не должен слать пачки параллельно."""
        async with self._send_lock:
            return await self._raw_sender_unlocked(
                messages, dest_id, no_author, no_captions, topic_id, status_msg, tid
            )

    async def _raw_sender_unlocked(self, messages, dest_id, no_author, no_captions, topic_id, status_msg=None, tid=None):
        """Улучшенный sender с умной обработкой FloodWait."""
        _src = messages[0].chat_id if messages else None
        if _src is not None and _src in self._restricted_srcs:
            return await self._bypass_sender(messages, dest_id, no_author, no_captions, topic_id, status_msg, tid)
        _ad = self.active_dumps.get(tid, {}) if tid else {}
        if _ad.get("noflood") and tid:
            fwd_left, bypass_left = self._flood_state(tid)
            if fwd_left > 0:
                if bypass_left <= 0:
                    return await self._bypass_sender(messages, dest_id, no_author, no_captions, topic_id, status_msg, tid)
                await self._flood_sleep(tid, min(fwd_left, bypass_left), "оба пути")
                if self.active_dumps.get(tid, {}).get("status") == "stopped":
                    return False
                return await self._raw_sender_unlocked(messages, dest_id, no_author, no_captions, topic_id, status_msg, tid)
        try:
            dest_peer = await self.client.get_input_entity(dest_id)
            src_peer = await self.client.get_input_entity(messages[0].chat_id)
            await self.client(functions.messages.ForwardMessagesRequest(
                from_peer=src_peer, id=[m.id for m in messages],
                to_peer=dest_peer, drop_author=no_author, top_msg_id=topic_id,
                with_my_score=False, drop_media_captions=no_captions
            ))
            if tid and tid in self.active_dumps:
                self.active_dumps[tid]["last_successful_send"] = time.time()
                self.active_dumps[tid]["consecutive_floods"] = 0
                if self.active_dumps[tid].get("fwd_until"):
                    self.active_dumps[tid]["fwd_until"] = 0
                    await self._notify_flood_end(tid, "пересылка")
            return True
        except errors.FloodWaitError as e:
            wait_time = e.seconds if e.seconds is not None else 60
            if tid and self.active_dumps.get(tid, {}).get("noflood"):
                self._register_flood(tid, "пересылка", wait_time)
                fwd_left, bypass_left = self._flood_state(tid)
                if bypass_left <= 0:
                    await self._notify_flood_hit(tid, "пересылка", wait_time, alt="скачку")
                    return await self._bypass_sender(messages, dest_id, no_author, no_captions, topic_id, status_msg, tid)
                await self._flood_sleep(tid, min(fwd_left, bypass_left), "оба пути")
                if self.active_dumps.get(tid, {}).get("status") == "stopped":
                    return False
                return await self._raw_sender_unlocked(messages, dest_id, no_author, no_captions, topic_id, status_msg, tid)
            if tid and tid in self.active_dumps:
                task = self.active_dumps[tid]
                task["consecutive_floods"] = task.get("consecutive_floods", 0) + 1
                task["flood_count"] = task.get("flood_count", 0) + 1
                task["flood_total_seconds"] = task.get("flood_total_seconds", 0) + wait_time
                task["current_flood_wait"] = wait_time
                task["status"] = "paused"
                task["flood_wait_until"] = time.time() + wait_time + self.config["flood_buffer"]
                task["fwd_until"] = task["flood_wait_until"]
                task["last_flood_path"] = "пересылка"
                current_speed = task.get('current_speed', 0)
                total_msgs = task.get('total_estimated', 0)
                current_count = task.get('current', 0)
                status_chat = task.get("status_chat_id")
                if status_chat:
                    await self._send_flood_notice(status_chat, wait_time, current_count, tid, total_msgs, current_speed)
                logger.warning(f"[{tid}] FloodWait: ждём {wait_time}с (запрошено Telegram) + {self.config['flood_buffer']}с буфер")
                total_wait = wait_time + self.config["flood_buffer"]
                waited = 0
                check_interval = 5
                while waited < total_wait:
                    if tid in self.active_dumps:
                        if self.active_dumps[tid].get("status") == "stopped":
                            logger.info(f"[{tid}] Задача остановлена во время ожидания FloodWait")
                            return False
                    await asyncio.sleep(min(check_interval, total_wait - waited))
                    waited += check_interval
                if tid in self.active_dumps:
                    self.active_dumps[tid]["status"] = "running"
                    self.active_dumps[tid]["last_successful_send"] = time.time()
                    self.active_dumps[tid]["fwd_until"] = 0
                    await self._notify_flood_end(tid, "пересылка")
                try:
                    await self.client(functions.messages.ForwardMessagesRequest(
                        from_peer=src_peer, id=[m.id for m in messages],
                        to_peer=dest_peer, drop_author=no_author, top_msg_id=topic_id,
                        with_my_score=False, drop_media_captions=no_captions
                    ))
                    if tid and tid in self.active_dumps:
                        self.active_dumps[tid]["last_successful_send"] = time.time()
                        self.active_dumps[tid]["consecutive_floods"] = 0
                    return True
                except errors.FloodWaitError as e2:
                    logger.warning(f"[{tid}] Повторный FloodWait: ждём ещё {e2.seconds}с")
                    await asyncio.sleep(e2.seconds + self.config["flood_buffer"])
                    return False
            return False
        except Exception as e:
            if self._is_copy_restricted_error(e):
                logger.warning("[%s] Источник защищён запретом копирования/пересылки Telegram", tid)
                await self._report_copy_restricted(status_msg, tid)
                return False
            logger.error(f"[{tid}] Send Error: {e}")
            return False

    def _bypass_tmp_dir(self):
        d = os.path.join(tempfile.gettempdir(), "chatcopy_bypass")
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            d = tempfile.gettempdir()
        return d

    def _cleanup_bypass_tmp(self):
        try:
            d = os.path.join(tempfile.gettempdir(), "chatcopy_bypass")
            if os.path.isdir(d):
                for n in os.listdir(d):
                    try:
                        os.remove(os.path.join(d, n))
                    except Exception:
                        pass
        except Exception:
            pass

    @staticmethod
    def _media_size(m):
        f = getattr(m, "file", None)
        return (getattr(f, "size", 0) or 0) if f else 0

    def _has_free_disk(self, size):
        try:
            free = shutil.disk_usage(tempfile.gettempdir()).free
            return free > size + BYPASS_MIN_FREE_DISK_MB * 1024 * 1024
        except Exception:
            return True

    @staticmethod
    def _bypass_attrs(m):
        kw = {}
        doc = getattr(getattr(m, "media", None), "document", None)
        attrs = (getattr(doc, "attributes", None) or []) if doc else []
        if attrs:
            kw["attributes"] = list(attrs)
            for a in attrs:
                c = a.__class__.__name__
                if c == "DocumentAttributeAudio" and getattr(a, "voice", False):
                    kw["voice_note"] = True
                if c == "DocumentAttributeVideo" and getattr(a, "round_message", False):
                    kw["video_note"] = True
        return kw

    def _flood_state(self, tid):
        """(сек до конца ФВ по пересылке, по скачке). 0 = путь свободен."""
        ad = self.active_dumps.get(tid, {}) if tid else {}
        now = time.time()
        return (max(0, ad.get("fwd_until", 0) - now), max(0, ad.get("bypass_until", 0) - now))

    def _register_flood(self, tid, path, seconds):
        """Ставит таймер пути + счётчики. path: 'пересылка' | 'скачка'."""
        ad = self.active_dumps.get(tid) if tid else None
        if not ad:
            return
        ad["fwd_until" if path == "пересылка" else "bypass_until"] = time.time() + seconds + self.config["flood_buffer"]
        ad["flood_count"] = ad.get("flood_count", 0) + 1
        ad["flood_total_seconds"] = ad.get("flood_total_seconds", 0) + seconds
        ad["current_flood_wait"] = seconds
        ad["last_flood_path"] = path
        logger.warning("[%s] FloodWait %sс на пути «%s»", tid, seconds, path)

    def _fmt_left(self, seconds):
        seconds = int(max(0, seconds))
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h: return f"{h}ч {m}м {s}с"
        if m: return f"{m}м {s}с"
        return f"{s}с"

    async def _flood_sleep(self, tid, seconds, path):
        """Сон с проверкой стопа (когда оба пути во флуде). Статус 'пауза'."""
        ad = self.active_dumps.get(tid) if tid else None
        if ad is not None:
            ad["status"] = "paused"
        total, waited = max(0, seconds), 0
        while waited < total:
            cur = self.active_dumps.get(tid) if tid else None
            if cur is not None and cur.get("status") == "stopped":
                return
            await asyncio.sleep(min(5, total - waited))
            waited += 5
        cur = self.active_dumps.get(tid) if tid else None
        if cur is not None and cur.get("status") != "stopped":
            cur["status"] = "running"

    async def _notify_flood_hit(self, tid, path, seconds, alt=None):
        # только в логи: в чат не спамим (для статуса есть .chatcopy -status)
        if alt:
            logger.info("[%s] FloodWait «%s» ~%sс → перехожу на %s", tid, path, int(seconds), alt)

    async def _notify_flood_end(self, tid, path):
        logger.info("[%s] FloodWait «%s» закончился — продолжаю", tid, path)
        self.active_dumps.get(tid, {}).pop("_flood_notice_sig", None)

    async def _flood_chat_notice(self, tid, path, seconds):
        _t = next((t for t in self.task_queue if t.get("tid") == tid), {})
        _sc = _t.get("status_chat_id")
        if not _sc:
            return
        await self._send_flood_notice(_sc, seconds, _t.get("current", 0), tid, _t.get("total_estimated", 0), _t.get("current_speed", 0), path=path)

    async def _bypass_sender(self, messages, dest_id, no_author, no_captions, topic_id, status_msg=None, tid=None):
        """Обход запрета/флуда. Для каждой группы выбирает путь: пересылка (если свободна и не запрещена)
        или скачка→заливка. Кто из путей раньше выйдет из FloodWait — тем и шлём. Медиа на диске по одному альбому."""
        _src = messages[0].chat_id if messages else None
        allow_forward = not (_src is not None and _src in self._restricted_srcs)
        try:
            dest_peer = await self.client.get_input_entity(dest_id)
            src_peer = await self.client.get_input_entity(_src) if _src is not None else None
        except Exception:
            dest_peer = src_peer = None
        if src_peer is None:
            allow_forward = False
        groups, cur, gid0 = [], [], None
        for m in messages:
            g = getattr(m, "grouped_id", None)
            if cur and g is not None and g == gid0:
                cur.append(m)
            else:
                if cur:
                    groups.append(cur)
                cur, gid0 = [m], g
        if cur:
            groups.append(cur)
        ok = False
        for grp in groups:
            if tid and self.active_dumps.get(tid, {}).get("status") == "stopped":
                break
            sent, allow_forward = await self._send_group_smart(
                grp, src_peer, dest_peer, dest_id, no_author, no_captions, topic_id, tid, allow_forward)
            ok = ok or sent
        if ok and tid and tid in self.active_dumps:
            self.active_dumps[tid]["last_successful_send"] = time.time()
        return ok

    async def _send_group_smart(self, grp, src_peer, dest_peer, dest_id, no_author, no_captions, topic_id, tid, allow_forward):
        """Отправка одной группы лучшим доступным путём. Lossless: повторяет до успеха/стопа.
        Возвращает (успех, allow_forward)."""
        while True:
            if tid and self.active_dumps.get(tid, {}).get("status") == "stopped":
                return False, allow_forward
            fwd_left, bypass_left = self._flood_state(tid) if tid else (0, 0)
            # 1) пересылка свободна и разрешена -> пересылаем без скачки
            if allow_forward and fwd_left <= 0:
                try:
                    await self.client(functions.messages.ForwardMessagesRequest(
                        from_peer=src_peer, id=[m.id for m in grp], to_peer=dest_peer,
                        drop_author=no_author, top_msg_id=topic_id, with_my_score=False,
                        drop_media_captions=no_captions))
                    if tid and self.active_dumps.get(tid, {}).get("fwd_until"):
                        self.active_dumps[tid]["fwd_until"] = 0
                        await self._notify_flood_end(tid, "пересылка")
                    return True, allow_forward
                except errors.FloodWaitError as e:
                    self._register_flood(tid, "пересылка", e.seconds or 60)
                    await self._notify_flood_hit(tid, "пересылка", e.seconds or 60, alt="скачку")
                    await self._flood_chat_notice(tid, "пересылка", e.seconds or 60)
                    continue
                except (errors.ChatForwardsRestrictedError, errors.ChatSendMediaForbiddenError):
                    if grp and getattr(grp[0], "chat_id", None) is not None:
                        self._restricted_srcs.add(grp[0].chat_id)
                    allow_forward = False
                    continue
                except Exception as e:
                    logger.error("[%s] bypass forward error: %s — перехожу на скачку", tid, e)
                    allow_forward = False
                    continue
            # 2) скачка свободна -> качаем+заливаем
            if bypass_left <= 0:
                res = await self._bypass_upload_group(grp, dest_id, no_author, no_captions, topic_id, tid)
                if res == "flood":
                    await self._notify_flood_hit(tid, "скачка",
                        self.active_dumps.get(tid, {}).get("current_flood_wait", 0),
                        alt=("пересылку" if allow_forward else None))
                    await self._flood_chat_notice(tid, "скачка", self.active_dumps.get(tid, {}).get("current_flood_wait", 0))
                    continue
                return bool(res), allow_forward
            # 3) оба пути во флуде -> ждём того, кто освободится первым
            wait = min(fwd_left, bypass_left) if allow_forward else bypass_left
            await self._flood_sleep(tid, wait, "оба sdoxli")

    async def _bypass_upload_group(self, grp, dest_id, no_author, no_captions, topic_id, tid):
        """Скачивает медиа группы на диск -> заливает -> удаляет. Возвращает True/False/'flood'."""
        paths, files, first = [], [], None
        try:
            for m in grp:
                media = getattr(m, "media", None)
                if not media or isinstance(media, (types.MessageMediaPoll, types.MessageMediaWebPage)):
                    continue
                sz = self._media_size(m)
                if sz and sz > BYPASS_SKIP_OVER_MB * 1024 * 1024:
                    logger.warning("[%s] bypass: пропуск msg=%s (>%sМБ)", tid, m.id, BYPASS_SKIP_OVER_MB)
                    continue
                if not self._has_free_disk(sz):
                    logger.warning("[%s] bypass: мало места — пропуск msg=%s", tid, m.id)
                    continue
                dst = os.path.join(self._bypass_tmp_dir(), f"cc_{tid}_{m.id}")
                try:
                    p = await self.client.download_media(m, file=dst)
                except Exception as de:
                    logger.error("[%s] bypass download msg=%s: %s", tid, m.id, de)
                    p = None
                if p:
                    paths.append(p)
                    files.append(p)
                    if first is None:
                        first = m
            head = grp[0]
            cap = "" if no_captions else (getattr(head, "message", "") or "")
            ents = None if no_captions else getattr(head, "entities", None)
            try:
                if files:
                    kw = self._bypass_attrs(first) if len(files) == 1 else {}
                    await self.client.send_file(
                        dest_id, files if len(files) > 1 else files[0],
                        caption=cap, formatting_entities=ents, reply_to=topic_id, **kw)
                    if tid and self.active_dumps.get(tid, {}).get("bypass_until"):
                        self.active_dumps[tid]["bypass_until"] = 0
                        await self._notify_flood_end(tid, "скачка")
                    return True
                sent_any = False
                for m in grp:
                    t = getattr(m, "message", "") or ""
                    if t.strip():
                        await self.client.send_message(
                            dest_id, t,
                            formatting_entities=(None if no_captions else getattr(m, "entities", None)),
                            reply_to=topic_id)
                        sent_any = True
                return sent_any
            except errors.FloodWaitError as e:
                self._register_flood(tid, "скачка", e.seconds or 5)
                return "flood"
        except Exception as e:
            logger.error("[%s] bypass upload error: %s", tid, e)
            return False
        finally:
            for p in paths:
                try:
                    if p and os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass

    def _parse_filter_and_ignored(self, args): # все аргументы нужные цепляет
        filter_type = FILTER_ALL
        ignored_topics = []
        clean_args = []
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--media":
                filter_type = FILTER_MEDIA
            elif arg == "--photo_video":
                filter_type = FILTER_PHOTO_VIDEO
            elif arg == "--docs":
                filter_type = FILTER_DOCS
            elif arg == "--text":
                filter_type = FILTER_TEXT
            elif arg in ("--itopic", "--ignore-topic", "--theme", "-theme"):
                if i + 1 < len(args):
                    ignored_topics.append(self._normalize_topic_selector(args[i + 1]))
                    i += 1
            elif arg.startswith("--itopic=") or arg.startswith("--theme="):
                ignored_topics.append(self._normalize_topic_selector(arg.split("=", 1)[1]))
            elif arg.startswith("-theme") and len(arg) > len("-theme"):
                ignored_topics.append(self._normalize_topic_selector(arg[len("-theme"):].lstrip("=:")))
            else:
                clean_args.append(arg)
            i += 1
        ignored_topics = [item for item in dict.fromkeys(ignored_topics) if item]
        return filter_type, ignored_topics, clean_args

    def _parse_filter(self, args):
        filter_type, _, clean_args = self._parse_filter_and_ignored(args)
        return filter_type, clean_args

    def _get_filter_name(self, filter_type):
        names = {
            FILTER_ALL: "Все сообщения",
            FILTER_MEDIA: "Только медиа",
            FILTER_PHOTO_VIDEO: "Фото и видео",
            FILTER_DOCS: "Документы",
            FILTER_TEXT: "Текст",
        }
        return names.get(filter_type, "Неизвестно")

    def _get_effective_batch_size(self) -> int:
        """Returns the current batch_size from config, always fresh."""
        val = self.config.get("batch_size", 100)
        if isinstance(val, int) and 1 <= val <= 100:
            return val
        return 100

    async def _get_latest_message_id(self, entity, topic_id=None):
        try:
            kwargs = {"limit": 1}
            if topic_id:
                kwargs["reply_to"] = topic_id
            latest = await self.client.get_messages(entity, **kwargs)
            latest_msg = latest[0] if latest else None
            return getattr(latest_msg, "id", 0) or 0
        except Exception as e:
            logger.warning("Latest message id lookup failed: %s", e)
            return 0

    async def _show_status(self, message):
        """Текущий статус активных копирований: прогресс, скорость, ETA, FloodWait по путям."""
        if not self.active_dumps:
            return await utils.answer(message, self.strings["status_none"])
        status_map = {"running": "Идёт", "paused": "Пауза (FloodWait)",
                      "stopped": "Остановлено", "counting": "Подсчёт сообщений"}
        text = self.strings["status_header"].format(n=len(self.active_dumps))
        for tid, ad in list(self.active_dumps.items()):
            task = next((t for t in self.task_queue if t.get("tid") == tid), {})
            src = utils.escape_html(str(task.get("src", ad.get("name", "?"))))
            dest = utils.escape_html(str(task.get("dest", "?")))
            current = ad.get("current", 0)
            total = ad.get("total_estimated", 0) or task.get("total_msgs", 0) or 0
            progress = round(current / total * 100, 1) if total else 0
            speed = round(ad.get("current_speed", 0))
            remaining = max(0, total - current)
            eta = self._fmt_left(remaining / speed * 60) if speed > 0 else "—"
            fwd_left, bypass_left = self._flood_state(tid)
            fwd = self._fmt_left(fwd_left) if fwd_left > 0 else "свободна"
            bypass = self._fmt_left(bypass_left) if bypass_left > 0 else "свободна"
            if ad.get("noflood"):
                if fwd_left <= 0:
                    work = "пересылка"
                elif bypass_left <= 0:
                    work = "скачка"
                else:
                    work = "ожидание (оба на FW)"
            else:
                work = "пересылка" if fwd_left <= 0 else "ожидание возобновления"
            status = status_map.get(ad.get("status", "running"), ad.get("status", "?"))
            text += self.strings["status_item"].format(
                src=src, dest=dest, status=status, current=current, total=total,
                progress=progress, speed=speed, eta=eta, fwd=fwd, bypass=bypass, working=work,
                floods=ad.get("flood_count", 0), flood_time=self._fmt_left(ad.get("flood_total_seconds", 0)))
        await utils.answer(message, self._default_html(text))

    @loader.command()
    async def chatcopy(self, message: Message):
        """<src> <dest> [start_id:final_id] [-n] [-dmc] [--now] [--noflood] [-status] [--itopic 1] [-theme123] [--media|--photo_video|--docs|--text] — Добавить задачу в очередь."""
        args_raw = self._split_args(message)
        if "-status" in args_raw:
            return await self._show_status(message)
        no_author = "-n" in args_raw
        no_captions = "-dmc" in args_raw
        start_now = "--now" in args_raw
        noflood = ("--noflood" in args_raw) and no_author  # обход FloodWait скачкой; только с -n
        if start_now:
            args_raw.remove("--now")
        args_raw = [x for x in args_raw if x not in ["-n", "-dmc", "--noflood"]]
        filter_type, ignored_topics, clean_args = self._parse_filter_and_ignored(args_raw)
        if len(clean_args) < 2:
            return await utils.answer(message, self.strings["args_err"])
        start_id = 0
        final_id = 0
        if len(clean_args) >= 3:
            id_arg = clean_args[2]
            if ":" in id_arg:
                parts = id_arg.split(":")
                if parts[0].isdigit(): 
                    start_id = int(parts[0])
                if len(parts) > 1 and parts[1].isdigit(): 
                    final_id = int(parts[1])
            elif id_arg.isdigit():
                start_id = int(id_arg)
        src, src_map = await self._resolve_arg(clean_args[0])
        if start_id == 0 and src_map.get('msg'):
            start_id = src_map['msg']  # старт подтянут из ссылки t.me/.../<msg>
        dest, dest_map = await self._resolve_arg(clean_args[1])
        if not src or not dest:
            return await utils.answer(message, self.strings["err_ent"])
        src_peer_id = int(self._get_normalized_id(src))
        if await self._source_has_copy_restriction(src):
            self._restricted_srcs.add(src_peer_id)  # авто-обход запрета пересылки (bypass mode)
        dest_peer_id = int(self._get_normalized_id(dest))
        self._task_counter += 1
        tid = f"{src_peer_id}_{dest_peer_id}_{self._task_counter}_{int(time.time())}"
        src_is_forum = self._is_forum(src)
        dest_is_forum = self._is_forum(dest)
        if src_is_forum and not dest_is_forum:
            forum_result = await self._ensure_forum_enabled(dest)
            if forum_result:
                dest = await self.client.get_entity(dest.id)
                dest_is_forum = self._is_forum(dest)
                if not dest_is_forum:
                    await asyncio.sleep(2)
                    dest = await self.client.get_entity(dest.id)
                    dest_is_forum = self._is_forum(dest)
                if dest_is_forum:
                    logger.info("[%s] Режим топиков включён на dest %s", tid, getattr(dest, 'title', dest.id))
                else:
                    logger.warning("[%s] _ensure_forum_enabled вернул True, но _is_forum всё ещё False для dest %s", tid, getattr(dest, 'title', dest.id))
            else:
                logger.warning("[%s] Не удалось включить топики на dest %s — копирование пойдёт без маппинга топиков", tid, getattr(dest, 'title', dest.id))
        elif src_is_forum and dest_is_forum:
            try:
                dest = await self.client.get_entity(dest.id)
                dest_is_forum = self._is_forum(dest)
            except Exception:
                pass
        if src_is_forum and not dest_is_forum:
            logger.warning("[%s] src — форум, dest — НЕ форум. Все сообщения пойдут в General!", tid)
        status_msg = await utils.answer(message, self.strings[self._default_text_key("preparing")])
        total_msgs = 0
        f_src_t_for_count = src_map.get('topic')
        if start_now:
            try:
                if f_src_t_for_count:
                    async for _ in self.client.iter_messages(
                        src,
                        reply_to=f_src_t_for_count,
                        min_id=start_id - 1 if start_id else 0,
                        max_id=final_id + 1 if final_id else 0,
                    ):
                        total_msgs += 1
                        if total_msgs > 150000: break
                else:
                    result = await self.client(functions.messages.GetHistoryRequest(
                        peer=src,
                        offset_id=0,
                        offset_date=None,
                        add_offset=0,
                        limit=1,
                        max_id=final_id + 1 if final_id else 0,
                        min_id=start_id - 1 if start_id else 0,
                        hash=0,
                    ))
                    total_msgs = getattr(result, 'count', 0) or 0
            except Exception as e:
                logger.warning(f"Count failed for --now: {e}")
                total_msgs = 0
        else:
            try:
                iter_kwargs = {
                    "min_id": start_id - 1 if start_id else 0,
                    "max_id": final_id + 1 if final_id else 0,
                }
                if f_src_t_for_count:
                    iter_kwargs["reply_to"] = f_src_t_for_count
                async for _ in self.client.iter_messages(src, **iter_kwargs):
                    total_msgs += 1
                    if total_msgs > 150000: break
            except Exception as e:
                logger.error(f"Ошибка при подсчете сообщений: {e}")
                total_msgs = -1
        src_name = getattr(src, 'title', src.id)
        dest_name = getattr(dest, 'title', dest.id)
        async with self._queue_lock:
            queue_position = len([t for t in self.task_queue if t['status'] == 'queued']) + 1
            estimated_duration = self._estimate_duration(total_msgs)
            mode_str = "🗂️ Топики (Auto)" if src_is_forum else "Обычный"
            no_auth_str = "Да" if no_author else "Нет"
            no_capt_str = "Да" if no_captions else "Нет"
            start_id_str = f"с {start_id}" if start_id > 0 else "С начала"
            if final_id > 0: start_id_str += f" до {final_id}"
            task_info = {
                'tid': tid, 'src': src_name, 'dest': dest_name, 'src_id': src_peer_id, 'dest_id': dest_peer_id,
                'status': 'queued', 'position': queue_position, 'added_time': self._now().isoformat(),
                'no_author': no_author, 'no_captions': no_captions, 'filter_type': filter_type,
                'start_id': start_id, 'final_id': final_id, 'total_msgs': total_msgs if total_msgs > -1 else 0,
                'current': 0, 'last_processed_id': start_id - 1 if start_id > 0 else 0,
                'status_msg_id': status_msg.id, 'status_chat_id': status_msg.chat_id,
                'map_t': src_is_forum, 'f_src_t': src_map.get('topic'), 'f_dest_t': dest_map.get('topic'),
                'start_now': start_now, 'ignored_topics': ignored_topics,
                'noflood': noflood,
            }
            self.task_queue.append(task_info)
            self._save_tasks()
        filter_name = self._get_filter_name(filter_type)
        ignored_str = self._format_ignored_topics(ignored_topics)
        if src_peer_id in self._restricted_srcs:
            bypass_str = "Авто-скачка (запрет пересылки)"
        elif noflood:
            bypass_str = "Скачка при FloodWait (--noflood)"
        else:
            bypass_str = "Нет (обычная пересылка)"
        await status_msg.edit(self.strings[self._default_text_key("copy_start")].format(
            src=utils.escape_html(src_name), dest=utils.escape_html(dest_name),
            mode=mode_str, start_id=start_id_str, no_auth=no_auth_str,
            no_capt=no_capt_str, filter_type=filter_name,
            ignored_topics=ignored_str, bypass=bypass_str,
            total_msgs=total_msgs if total_msgs > -1 else "∞ (ошибка подсчета)",
            estimated_time=estimated_duration, position=queue_position
        ))
        await self.dump_queue.put({
            "status_msg": status_msg, "src": src, "dest": dest,
            "no_auth": no_author, "no_captions": no_captions,
            "map_t": src_is_forum, "f_src_t": src_map.get('topic'), "f_dest_t": dest_map.get('topic'),
            "tid": tid, "min_id": start_id, "max_id": final_id,
            "mode_str": mode_str, "no_auth_str": no_auth_str, "no_capt_str": no_capt_str,
            "start_id_str": start_id_str, "filter_type": filter_type, "filter_name": filter_name,
            "src_name": src_name, "queue_position": queue_position, "total_msgs": total_msgs if total_msgs > -1 else 0,
            "restored_count": 0, "ignored_topics": ignored_topics,
        })

    def _parse_duration(self, duration_str): # описание ниже
        """Парсит строку длительности в секунды"""
        if duration_str == "∞":
            return 3600
        total = 0
        parts = duration_str.split()
        for part in parts:
            if 'ч' in part:
                total += int(part.replace('ч', '')) * 3600
            elif 'ч' in part and 'м' in part:
                pass
            elif 'м' in part and 'с' not in part:
                total += int(part.replace('м', '')) * 60
            elif 'м' in part and 'с' in part:
                mins_secs = part.replace('м', '').replace('с', '').split()
                if len(mins_secs) >= 1:
                    total += int(mins_secs[0]) * 60
                if len(mins_secs) >= 2:
                    total += int(mins_secs[1])
            elif 'с' in part:
                total += int(part.replace('с', ''))
            elif part.isdigit():
                total += int(part)
        return total if total > 0 else 0

    @loader.command() # стартует слежку за чатом что бы пи... кхм кхм, благополучно заимствовать сей прекрасный или не очень контент
    async def ccwatch(self, message: Message):
        """<src> <dest> [start_id|last] [-n] [-dmc] [--itopic 1] [-theme123] [--media|--photo_video|--docs|--text] — Наблюдение за чатом"""
        args = self._split_args(message)
        if "--now" in args:
            return await utils.answer(message, "❌ Для <code>.ccwatch</code> используй третий аргумент <code>last</code> или стартовый ID вместо <code>--now</code>.\n\nПример: <code>.ccwatch @src @dst last</code>")
        no_author = "-n" in args
        no_captions = "-dmc" in args
        args = [x for x in args if x not in ["-n", "-t", "-dmc"]]
        filter_type, ignored_topics, clean_args = self._parse_filter_and_ignored(args)
        if len(clean_args) < 2: 
            return await utils.answer(message, self.strings["args_err"])
        start_arg = clean_args[2].strip() if len(clean_args) >= 3 else ""
        if ":" in start_arg:
            return await utils.answer(
                message,
                "❌ В <code>.ccwatch</code> нужен только стартовый ID без двоеточия.\n\n"
                "Пример: <code>.ccwatch @src @dst 62150</code>\n"
                "Только новые: <code>.ccwatch @src @dst last</code>"
            )
        src, src_map = await self._resolve_arg(clean_args[0])
        dest, dest_map = await self._resolve_arg(clean_args[1])
        if not src or not dest: 
            return await utils.answer(message, self.strings["err_ent"])
        # запрет пересылки обходится автоматически на лету (bypass mode)
        src_is_forum = self._is_forum(src)
        dest_is_forum = self._is_forum(dest)
        if src_is_forum and not dest_is_forum:
            forum_result = await self._ensure_forum_enabled(dest)
            if forum_result:
                await utils.answer(message, self.strings["forum_enabled"].format(chat=utils.escape_html(getattr(dest, 'title', dest.id))))
                dest = await self.client.get_entity(dest.id)
            else:
                return await utils.answer(message, self.strings["forum_enable_failed"].format(chat=utils.escape_html(getattr(dest, 'title', dest.id))))
        src_t = src_map.get('topic')
        dest_t = dest_map.get('topic')
        start_id = 0
        starts_after_latest = False
        if start_arg:
            start_token = start_arg.lower()
            if start_token in ("last", "latest", "now", "new", "новые", "последний"):
                starts_after_latest = True
                start_id = await self._get_latest_message_id(src, src_t)
            elif start_arg.isdigit() and int(start_arg) > 0:
                start_id = int(start_arg)
            else:
                return await utils.answer(
                    message,
                    "❌ Неверный старт для <code>.ccwatch</code>.\n\n"
                    "Нужен ID сообщения, например <code>62150</code>, или <code>last</code>, чтобы пропустить старую историю."
                )
        map_topics = src_is_forum
        cid = self._get_normalized_id(src)
        src_peer_id = int(cid)
        dest_peer_id = int(self._get_normalized_id(dest))
        try:
            dest_id = dest_peer_id
        except Exception:
            dest_id = dest.id
        if starts_after_latest:
            self.last_processed_ids[cid] = start_id
        elif start_id > 0:
            self.last_processed_ids[cid] = start_id - 1
        elif cid not in self.last_processed_ids:
            self.last_processed_ids[cid] = 0
        self.watchlist[cid] = {
            "dest": dest_id, "no_author": no_author, "no_captions": no_captions, "map_topics": map_topics,
            "fixed_src_topic": src_t, "fixed_dest_topic": dest_t, "src_entity_id": src_peer_id, "dest_entity_id": dest_peer_id,
            "filter_type": filter_type, "final_id": 0, "ignored_topics": ignored_topics
        }
        self.db.set("ChatCopy", "watchlist", self.watchlist)
        self.db.set("ChatCopy", "last_processed_ids", self.last_processed_ids)
        filter_name = self._get_filter_name(filter_type)
        ignored_str = self._format_ignored_topics(ignored_topics)
        msg_text = self.strings["watch_added"].format(
            src=getattr(src, 'title', src.id), src_id=cid, dest=getattr(dest, 'title', dest.id),
            topics="🗂️ ВКЛ (Auto-mapping)" if map_topics else "ВЫКЛ",
            no_capt="Да" if no_captions else "Нет",
            filter_type=filter_name,
            ignored=ignored_str
        )
        if starts_after_latest:
            msg_text += f"\nСтарт: только новые сообщения после ID <code>{start_id}</code>"
        elif start_id > 0:
            msg_text += f"\nСтартовый ID: <code>{start_id}</code>"
        await utils.answer(message, msg_text)

    async def _history_dumper(self, status_msg, src, dest, no_auth, no_captions, 
                                map_t, f_src_t, f_dest_t, tid, min_id=0, max_id=0,
                                filter_type=FILTER_ALL, filter_name="", restored_count=0,
                                ignored_topics=None, **kwargs):
        if ignored_topics is None:
            ignored_topics = []
        if tid in self.active_dumps:
            self.active_dumps[tid]["status"] = "running"
        task = next((t for t in self.task_queue if t['tid'] == tid), None)
        if not task:
            logger.error(f"Задача {tid} не найдена в очереди для дампа.")
            return
        count = task.get('current', 0) or restored_count
        if tid in self.active_dumps and count > 0:
            self.active_dumps[tid]["current"] = count
        start_from_id = task.get('last_processed_id', min_id - 1 if min_id > 0 else 0)
        if map_t:
            try:
                dest = await self.client.get_entity(dest.id)
                if not self._is_forum(dest):
                    logger.info("[%s] dest не форум, пытаемся включить топики...", tid)
                    ok = await self._ensure_forum_enabled(dest)
                    if ok:
                        await asyncio.sleep(2)
                        dest = await self.client.get_entity(dest.id)
                        if self._is_forum(dest):
                            logger.info("[%s] Режим топиков включён на dest в dumper", tid)
                        else:
                            logger.warning("[%s] _ensure_forum_enabled OK, но _is_forum False. Пробуем ещё раз...", tid)
                            await asyncio.sleep(3)
                            dest = await self.client.get_entity(dest.id)
                            if not self._is_forum(dest):
                                logger.warning("[%s] dest не является форумом после повторной проверки, пересылка без топиков", tid)
                                map_t = False
                    else:
                        logger.warning("[%s] dest не является форумом, пересылка без топиков", tid)
                        map_t = False
            except Exception as e:
                logger.warning("[%s] Ошибка обновления dest entity: %s", tid, e)
        if map_t:
            try:
                src = await self.client.get_entity(src.id)
                if not self._is_forum(src):
                    logger.warning("[%s] src не является форумом (хотя map_t=True), отключаем маппинг", tid)
                    map_t = False
            except Exception as e:
                logger.warning("[%s] Ошибка обновления src entity: %s", tid, e)
        if map_t and self._is_forum(src) and self._is_forum(dest):
            await self._precreate_topics(src, dest, ignored_topics, f_src_t, tid)
        batch = []
        dumper_kwargs = {"reverse": True}
        if f_src_t: dumper_kwargs["reply_to"] = f_src_t
        if start_from_id > 0: dumper_kwargs["min_id"] = start_from_id
        if max_id > 0: dumper_kwargs["max_id"] = max_id + 1
        dest_peer_id = int(self._get_normalized_id(dest))
        delay = self.config["delay"]
        try:
            async for msg in self.client.iter_messages(src, **dumper_kwargs):
                if tid not in self.active_dumps or self.active_dumps[tid].get("status") in ("stopped", "error"): break
                await self.active_dumps[tid].get("cancel", asyncio.Event()).wait()
                if tid not in self.active_dumps or self.active_dumps[tid].get("status") in ("stopped", "error"): break
                if isinstance(msg, types.MessageService) or not self._should_include_message(msg, filter_type): continue
                batch.append(msg)
                if len(batch) >= self._get_effective_batch_size():
                    processed = await self._process_batch(
                        messages=list(batch), dest_id=dest_peer_id, no_author=no_auth, no_captions=no_captions,
                        fixed_dest_topic=f_dest_t, map_topics=map_t, dest_entity=dest, src_entity=src,
                        filter_type=filter_type, status_msg=status_msg, tid=tid,
                        ignored_topics=ignored_topics
                    )
                    if tid not in self.active_dumps or self.active_dumps[tid].get("status") == "stopped": break
                    if self.active_dumps[tid].get("status") == "error": break
                    if tid in self.active_dumps:
                        self.active_dumps[tid]["current"] += processed
                        count = self.active_dumps[tid]["current"]
                        task['current'] = count
                        task['last_processed_id'] = batch[-1].id
                        self._save_tasks()
                        total = task.get('total_msgs', 0)
                        pct = round(count / total * 100, 1) if total else 0
                        spd = round(self.active_dumps[tid].get('current_speed', 0), 1)
                        logger.info("[%s] Прогресс: %d/%d (%.1f%%) | %.1f сооб/мин",
                                   tid, count, total, pct, spd)
                    batch = []
            if batch and self.active_dumps.get(tid, {}).get("status") not in ("stopped", "error"):
                processed = await self._process_batch(
                    messages=list(batch), dest_id=dest_peer_id, no_author=no_auth, no_captions=no_captions,
                    fixed_dest_topic=f_dest_t, map_topics=map_t, dest_entity=dest, src_entity=src,
                    filter_type=filter_type, status_msg=status_msg, tid=tid,
                    ignored_topics=ignored_topics
                )
                if tid in self.active_dumps and self.active_dumps[tid].get("status") not in ("stopped", "error"):
                    self.active_dumps[tid]["current"] += processed
                    count = self.active_dumps[tid]["current"]
                    task['current'] = count
                    task['last_processed_id'] = batch[-1].id
            if self.active_dumps.get(tid, {}).get("status") not in ("stopped", "error"):
                task['status'] = 'completed'
                if tid in self.active_dumps:
                    self.active_dumps[tid]["status"] = "completed"
                self.task_queue = [t for t in self.task_queue if t['tid'] != tid]
                self._save_tasks()
                task_data = self.active_dumps[tid]
                duration_seconds = time.time() - task_data.get('start_time', time.time())
                duration_str = self._format_duration(duration_seconds)
                active_seconds = duration_seconds - task_data.get('flood_total_seconds', 0)
                if active_seconds <= 0: active_seconds = 1
                avg_speed = round((count / active_seconds) * 60, 1)
                chat_id_to_report = status_msg.chat_id if status_msg and status_msg.chat_id else task.get('status_chat_id')
                done_full = self.strings[self._default_text_key("copy_done_detailed")].format(
                    src=utils.escape_html(getattr(src, 'title', src.id)), dest=utils.escape_html(getattr(dest, 'title', dest.id)),
                    no_auth=kwargs.get("no_auth_str", "N/A"), no_capt=kwargs.get("no_capt_str", "N/A"),
                    start_id=kwargs.get("start_id_str", "N/A"), mode=kwargs.get("mode_str", "N/A"),
                    filter_type=filter_name, count=count, duration=duration_str,
                    avg_speed=avg_speed, flood_info=self._format_flood_stats(task_data)
                )
                # краткий итог в логи
                logger.info(
                    "[✅ %s] Завершено: %d сообщений за %s | %.1f сооб/мин",
                    task_data.get('name', '?'), count, duration_str, avg_speed
                )
                # полный итог в чат где было запущено
                if chat_id_to_report:
                    await self.client.send_message(chat_id_to_report, done_full)
        except Exception as e:
            logger.error(f"Dumper Error: {e}", exc_info=True)
            chat_id_to_report = status_msg.chat_id if status_msg and status_msg.chat_id else task.get('status_chat_id')
            if chat_id_to_report: await self.client.send_message(chat_id_to_report, f"❌ Ошибка в задаче:\n{e}")
            task['status'] = 'error'
            if tid in self.active_dumps:
                self.active_dumps[tid]["status"] = "error"
            self._save_tasks()

    @loader.watcher() # сам ватчер, который следит за чатами
    async def watcher(self, message: Message):
        if isinstance(message, types.MessageService): 
            return
        # Проверка профилей
        wkey, ws = self._wizard_state_for_message(message)
        if ws:
            handled = await self._wizard_handler(message, ws, ws.get("cid", getattr(message, "chat_id", 0)), wkey)
            if handled:
                return
        # Основная логика watcher'а
        if not getattr(message, 'chat_id', None):
            return
        raw_chat_id = str(message.chat_id)
        normalized_id = self._get_normalized_id(getattr(message, 'chat', None))
        chat_id_from_utils = "0"
        if getattr(message, 'chat', None) and hasattr(utils, 'get_chat_id'):
            try:
                chat_id_from_utils = str(utils.get_chat_id(message.chat))
            except Exception:
                pass
        possible_ids = [
            normalized_id,
            raw_chat_id,
            raw_chat_id.replace("-100", ""),
            f"-100{raw_chat_id.replace('-100', '').replace('-', '')}",
            chat_id_from_utils
        ]
        cid = None
        for test_id in possible_ids:
            if test_id in self.watchlist:
                cid = test_id
                break
        if not cid:
            return
        cfg = self.watchlist[cid]
        filter_type = cfg.get("filter_type", FILTER_ALL)
        last_id = self.last_processed_ids.get(cid, 0)
        final_id = cfg.get("final_id", 0)
        if message.id <= last_id:
            return
        if final_id > 0 and message.id > final_id:
            return
        if not self._should_include_message(message, filter_type):
            self.last_processed_ids[cid] = message.id
            self.db.set("ChatCopy", "last_processed_ids", self.last_processed_ids)
            return
        if cfg.get("fixed_src_topic"):
            cur_t = self._topic_id_from_message(message)
            if cur_t != cfg["fixed_src_topic"]:
                self.last_processed_ids[cid] = message.id
                self.db.set("ChatCopy", "last_processed_ids", self.last_processed_ids)
                return
        if cfg.get("ignored_topics") and self._topic_is_ignored(self._topic_id_from_message(message), None, cfg.get("ignored_topics")):
            self.last_processed_ids[cid] = message.id
            self.db.set("ChatCopy", "last_processed_ids", self.last_processed_ids)
            return
        if cid not in self.watcher_buffer:
            self.watcher_buffer[cid] = []
        self.watcher_buffer[cid].append(message)
        self.last_watched[cid] = {
            "name": getattr(getattr(message, 'chat', None), "title", cid) if getattr(message, 'chat', None) else cid, 
            "time": self._format_clock()
        }
        if cid in self.watcher_flush_tasks:
            self.watcher_flush_tasks[cid].cancel()
        batch_size = self.config["batch_size"]
        if not isinstance(batch_size, int):
            batch_size = 100
        if len(self.watcher_buffer[cid]) >= batch_size:
            await self._flush_watcher_buffer(cid, cfg)
        else:
            self.watcher_flush_tasks[cid] = asyncio.get_event_loop().call_later(
                3.0, 
                lambda: asyncio.create_task(self._flush_watcher_buffer(cid, cfg))
            )

    async def _flush_watcher_buffer(self, cid, cfg): # опустошает буфер watcher'а: группирует альбомы и отправляет пачку в очередь на пересылку.
        if cid not in self.watcher_buffer or not self.watcher_buffer[cid]:
            return
        msgs = self.watcher_buffer[cid].copy()
        self.watcher_buffer[cid] = []
        if cid in self.watcher_flush_tasks:
            del self.watcher_flush_tasks[cid]
        try:
            cid_int = int(cid)
        except (ValueError, TypeError):
            logger.error(f"Watcher flush: неверный cid={cid}")
            return
        albums = {}
        single_msgs = []
        for msg in msgs:
            if msg.grouped_id:
                if msg.grouped_id not in albums:
                    albums[msg.grouped_id] = []
                albums[msg.grouped_id].append(msg)
            else:
                single_msgs.append(msg)
        for gid, album_msgs in albums.items():
            sorted_album = sorted(album_msgs, key=lambda x: x.id)
            try:
                dest_entity = await self.client.get_entity(cfg["dest"])
                src_entity = await self.client.get_entity(cid_int)
                await self.queue.put({
                    "messages": sorted_album, 
                    "dest_id": cfg["dest"], 
                    "no_author": cfg["no_author"],
                    "no_captions": cfg.get("no_captions", False), 
                    "fixed_dest_topic": cfg.get("fixed_dest_topic"),
                    "map_topics": cfg.get("map_topics"), 
                    "dest_entity": dest_entity, 
                    "src_entity": src_entity,
                    "filter_type": cfg.get("filter_type", FILTER_ALL), 
                    "watch_cid": cid,
                    "ignored_topics": cfg.get("ignored_topics", [])
                })
            except Exception as e:
                logger.error(f"Watcher album flush error (cid={cid}): {e}")
        batch_size = self.config["batch_size"]
        if not isinstance(batch_size, int):
            batch_size = 100
        for i in range(0, len(single_msgs), batch_size):
            batch = single_msgs[i:i + batch_size]
            try:
                dest_entity = await self.client.get_entity(cfg["dest"])
                src_entity = await self.client.get_entity(cid_int)
                await self.queue.put({
                    "messages": batch, 
                    "dest_id": cfg["dest"], 
                    "no_author": cfg["no_author"],
                    "no_captions": cfg.get("no_captions", False), 
                    "fixed_dest_topic": cfg.get("fixed_dest_topic"),
                    "map_topics": cfg.get("map_topics"), 
                    "dest_entity": dest_entity, 
                    "src_entity": src_entity,
                    "filter_type": cfg.get("filter_type", FILTER_ALL), 
                    "watch_cid": cid,
                    "ignored_topics": cfg.get("ignored_topics", [])
                })
            except Exception as e:
                logger.error(f"Watcher batch flush error (cid={cid}): {e}")

    async def _catch_up_on_restart(self): # ватчер восстанавливает после перезагрузки
        await asyncio.sleep(15)
        for cid_str, cfg in self.watchlist.items():
            try:
                last_id = self.last_processed_ids.get(cid_str, 0)
                if not isinstance(last_id, int):
                    last_id = 0
                missed = []
                batch_size = self.config["batch_size"]
                if not isinstance(batch_size, int): 
                    batch_size = 100
                filter_type = cfg.get("filter_type", FILTER_ALL)
                ignored_topics = cfg.get("ignored_topics", [])
                cid_int = int(cid_str)
                async for msg in self.client.iter_messages(cid_int, min_id=last_id):
                    if cfg.get("final_id", 0) > 0 and msg.id > cfg.get("final_id", 0):
                        continue
                    if isinstance(msg, types.MessageService):
                        continue
                    if cfg.get("fixed_src_topic"):
                        cur_t = self._topic_id_from_message(msg)
                        if cur_t != cfg["fixed_src_topic"]:
                            continue
                    if ignored_topics and self._topic_is_ignored(self._topic_id_from_message(msg), None, ignored_topics):
                        continue
                    if self._should_include_message(msg, filter_type):
                        missed.append(msg)
                if missed:
                    missed.sort(key=lambda x: x.id)
                    for i in range(0, len(missed), batch_size):
                        batch = missed[i:i + batch_size]
                        dest_ent = await self.client.get_entity(cfg["dest"])
                        src_ent = await self.client.get_entity(cid_int)
                        await self.queue.put({
                            "messages": batch, "dest_id": cfg["dest"], "no_author": cfg["no_author"],
                            "no_captions": cfg.get("no_captions", False), "fixed_dest_topic": cfg.get("fixed_dest_topic"),
                            "map_topics": cfg.get("map_topics"), "dest_entity": dest_ent, "src_entity": src_ent,
                            "filter_type": filter_type, "watch_cid": cid_str,
                            "ignored_topics": ignored_topics
                        })
                        await asyncio.sleep(self.config["delay"])
            except Exception as e:
                logger.debug(f"Catch-up error for {cid_str}: {e}")

    @loader.command()
    async def cchelp(self, message: Message):
        """— Подробная документация по модулю ChatCopy"""
        # ОБЫЧНЫЙ ТЕКСТ: справка отправляется обычным сообщением
        help_text = (
            '<emoji document_id=6030550768426159669>🛡</emoji> <b>Подробная документация по модулю ChatCopy!</b>\n\n'
            '<blockquote expandable><emoji document_id=5398049016556560225>1️⃣</emoji><b> Основные команды </b>\n'
            '<emoji document_id=5314310000531766389>🛫</emoji> <code>.chatcopy &lt;откуда&gt; &lt;куда&gt; [диапазон] [--itopic 1|\"Имя\"] [-theme123] [флаги]</code>\n'
            '<i>Копирует старую историю чата (делает дамп). Ставит задачу в очередь в случае если другая была запущена.</i>\n'
            '<emoji document_id=5258096772776991776>⚙️</emoji> <code>--now</code> — Начать немедленно, без полного подсчёта (примерное кол-во сообщений запрашивается у Telegram).\n\n'
            '<emoji document_id=6028228780256923695>👀</emoji> <code>.ccwatch &lt;откуда&gt; &lt;куда&gt; [start_id|last] [--itopic 1|\"Имя\"] [флаги]</code>\n'
            '<i>Режим слежки. Модуль будет висеть в фоне и пересылать новые сообщения. Третий аргумент — только стартовый ID или </i><code>last</code><i>, без двоеточия.</i>\n\n'
            '<emoji document_id=5355012477883004708>📺</emoji> <code>.ccpanel</code>\n'
            '<i>Открывает меню: управление задачами, пауза/стоп, статистика и настройки (скорость, задержка, профили).</i>\n\n'
            '<emoji document_id=6028352582689231001>🗑</emoji> <code>.ccclear topics</code>\n'
            '<i>Очищает кэш топиков (полезно, если форум сломался и пересылает не в те разделы).</i></blockquote>\n\n'
            '<blockquote expandable><emoji document_id=5397653273974939567>2️⃣</emoji><b> Источники и ID сообщений</b>\n'
            '<emoji document_id=5208758520647800433>✨</emoji> <b>Чаты:</b> Можно использовать юзернеймы (@chat), ID (-100123...) или прямые ссылки на топики (<a href="t.me/c/123/45">t.me/c/123/45</a>). Модуль сам всё распознает.\n'
            '<emoji document_id=5208556360832141255>⚪️</emoji> <b>.chatcopy диапазон [start:end]:</b> Пишется слитно, без пробелов.\n'
            '<emoji document_id=5208556360832141255>⚪️</emoji> <code>100:500</code> — скопировать с 100-го по 500-е сообщение.\n'
            '<emoji document_id=5208556360832141255>⚪️</emoji> <code>100:</code> — от 100-го до самых свежих.\n'
            '<emoji document_id=5208556360832141255>⚪️</emoji> <code>:500</code> — с самого начала чата и до 500-го.\n'
            '<emoji document_id=5208556360832141255>⚪️</emoji> <b>.ccwatch старт:</b> только один ID сообщения откуда начинать или <code>last</code>, без двоеточия.\n'
            '<emoji document_id=5208556360832141255>⚪️</emoji> <code>.ccwatch @src @dst 62150</code> — следить, начиная с ID 62150.\n'
            '<emoji document_id=5208556360832141255>⚪️</emoji> <code>.ccwatch @src @dst last</code> — пропустить старую историю и брать только новые.</blockquote>\n\n'
            '<blockquote expandable><emoji document_id=5397646938898178715>3️⃣</emoji><b> Флаги (Настройки текста)</b>\n'
            '<emoji document_id=5208556360832141255>⚪️</emoji> <code>-status</code> — статус прямо сейчас: прогресс, скорость, ETA, остаток FloodWait по каждому пути, число флудов.\n'
            '<emoji document_id=5208423865386026964>🆕</emoji> <code>--now</code> — начать <code>.chatcopy</code> без полного ручного подсчёта.\n'
            '<emoji document_id=5208809016578296327>🚫</emoji> <code>--itopic 1</code>, <code>--itopic "Название"</code>, <code>-theme123</code> — игнор топиков по ID или имени.\n'
            '<emoji document_id=5208809016578296327>👤</emoji> <code>-n</code> — Скрыть автора (пересылка без плашки «Переслано от...»).\n'
            '<emoji document_id=6028504027531055196>💬</emoji> <code>-dmc</code> — Удалить подпись к медиа (оставит только голую картинку или файл, удалив текст под ним)(!Работает только с[-n] флагом!).</blockquote>\n\n'
            '<blockquote expandable><emoji document_id=5397754265835938409>4️⃣</emoji><b> Фильтры контента</b>\n'
            '<i>(Указывайте только один! Если не указать ничего — скопируется всё подряд)</i>\n'
            '<emoji document_id=5208795483136348193>📌</emoji> <code>--media</code> — Любые медиа (фото, видео) и документы.\n'
            '<emoji document_id=5208443446141928861>📷</emoji> <code>--photo_video</code> — Строго только фото и видео (без гифок/стикеров).\n'
            '<emoji document_id=5208670581192411812>💼</emoji> <code>--docs</code> — Строго только документы (файлы, архивы, apk).\n'
            '<emoji document_id=6028504027531055196>💬</emoji> <code>--text</code> — Только чисто текстовые сообщения.</blockquote>\n\n'
            '<blockquote expandable><emoji document_id=5355012477883004708>5️⃣</emoji><b> Профили копирования</b>\n'
            '<emoji document_id=5355012477883004708>📋</emoji> Открой <code>.ccpanel</code> → <b>Профили</b>, чтобы сохранить связку источник → назначение.\n'
            '<emoji document_id=5208556360832141255>⚪️</emoji> Профиль хранит источник, назначение, топик назначения, старт/конец ID, фильтр, автора и подписи.\n'
            '<emoji document_id=5208556360832141255>⚪️</emoji> Ссылки вида <code>t.me/c/чат/сообщение</code> и <code>t.me/c/чат/топик/сообщение</code> распознаются: из них берётся чат, топик и стартовый ID.\n'
            '<emoji document_id=5208556360832141255>⚪️</emoji> Нажатие на номер профиля открывает настройки. Запуск всегда через подтверждение, случайно не стартанёт.\n'
            '<emoji document_id=5208556360832141255>⚪️</emoji> После копирования профиль запоминает последний ID сообщения и следующий запуск продолжает с момента последней остановки(с последнего пересланного сообщения).</blockquote>\n\n'
            '<blockquote expandable><emoji document_id=5208550511086683412>6️⃣</emoji><b> Полные примеры использования</b>\n'
            '<b>1. Полная копия канала со скрытием автора:</b>\n'
            '<emoji document_id=5296587908906511469>➡️</emoji> <code>.chatcopy @donor_channel @my_channel -n</code>\n\n'
            '<b>2. Слежка за конкретным топиком только с новых сообщений:</b>\n'
            '<emoji document_id=5296587908906511469>➡️</emoji> <code>.ccwatch <a href="t.me/c/123/4">t.me/c/123/4</a> <a href="t.me/c/321/5">t.me/c/321/5</a> last -dmc --photo_video</code>\n\n'
            '<b>3. Скопировать историю с 5000 по 6000 сообщение, только текст:</b>\n'
            '<emoji document_id=5296587908906511469>➡️</emoji> <code>.chatcopy -100111 -100222 5000:6000 --text</code></blockquote>\n\n'
            '<emoji document_id=5307554373457440075>💎</emoji> Приятного пользования!\n'
            '<emoji document_id=5345814569195421891>✅</emoji> Чаты с запретом копирования/пересылки обходятся автоматически (bypass): медиа скачивается и заливается заново.\n\n'
            '<blockquote expandable><emoji document_id=5341715473882955310>7️⃣</emoji><b> Обход запрета и флуда</b>\n'
            '<emoji document_id=5208556360832141255>⚪️</emoji> Если у источника включён запрет пересылки — модуль <b>сам</b> переходит в режим bypass (скачать → залить). Флаги не нужны.\n'
            '<emoji document_id=5208556360832141255>⚪️</emoji> <code>--noflood</code> (только вместе с <code>-n</code>) — при FloodWait на пересылке, содержимое временно отправляется через скачку, чтобы прогресс не стоял; после окончания FloodWait-а переходит к обычной пересылке.\n'
            '<emoji document_id=5208556360832141255>⚪️</emoji> Пересылка и скачка считают FloodWait <b>раздельно</b>. Если во флуде оба пути — бот ждёт тот, что освободится <b>первым</b>, и продолжает им.\n'
            '<emoji document_id=5208556360832141255>⚪️</emoji> Bypass-режим хранит медиа на диске по одному альбому за раз (память не растёт), пропускает файлы больше лимита аккаунта и проверяет свободное место. Кружки, голосовые, стикеры и гифки сохраняются.</blockquote>\n'
        )
        await utils.answer(message, self._default_html(help_text))

    @loader.command()
    async def ccpanel(self, message: Message):
        """Панель управления"""
        await self._show_main_panel(message)

    async def _show_main_panel(self, message, edit=False): # вот эта хрень это основная панель которая управляет кнопками и другим стафом
        active_text = "Нет"
        last_flood = "—"
        if self.current_dump_task and self.current_dump_task in self.active_dumps:
            task = self.active_dumps[self.current_dump_task]
            name = utils.escape_html(task.get('name', 'Unknown'))
            count = task.get('current', 0)
            total = task.get('total_estimated', 0)
            status = task.get('status', 'unknown')
            start_ts = task.get('start_time', time.time())
            elapsed = time.time() - start_ts
            if status == 'running':
                speed = task.get('current_speed', 0)
                progress = round((count / total * 100), 1) if total > 0 else 0
                eta = self._calculate_eta(count, total, speed)
                elapsed_str = self._format_duration(elapsed)
                start_dt = self._time_from_ts(start_ts)
                start_time = self._format_clock(start_dt)
                end_time = self._calculate_end_time(start_dt, total - count, speed)
                active_text = self.strings["panel_task_running"].format(
                    name=name,
                    count=count,
                    total=total,
                    speed=round(speed, 1),
                    progress=progress,
                    elapsed=elapsed_str,
                    eta=eta,
                    start_time=start_time,
                    end_time=end_time
                )
            elif status == 'paused':
                current_fw = task.get('current_flood_wait', 0)
                fw_str = f"{current_fw // 60}m {current_fw % 60}s" if current_fw >= 60 else f"{current_fw}s"
                resume_at = task.get('flood_wait_until', 0)
                resume_time = self._format_clock(resume_at) if resume_at else "неизвестно"
                active_text = self.strings["panel_task_paused"].format(
                    name=name,
                    flood_time=fw_str,
                    count=count,
                    total=total,
                    speed=round(task.get('current_speed', 0), 1),
                    resume_time=resume_time
                )
            else:
                active_text = f"{name}\n└ {status}"
        elif self.last_flood_info.get("time"):
            last_flood = self.last_flood_info["time"]
        text = self.strings["panel_summary"].format(
            queue_len=len([t for t in self.task_queue if t['status'] == 'queued']),
            active=active_text,
            watching_count=len(self.watchlist),
            last_flood=last_flood
        )
        queue_size = self.queue.qsize()
        if queue_size > 0:
            text += f"\n📥 Очередь watcher: {queue_size}"
        text += f"\n📋 Профилей: {len(self.profiles)}"
        pm_cid = getattr(message, "chat_id", 0) or 0
        if not pm_cid:
            pm_cid = self._call_chat_id(message) or self._last_panel_cid or 0
        if pm_cid:
            self._last_panel_cid = pm_cid
        btns = [
            [{"text": self.strings["btn_tasks"], "callback": self._panel_tasks}, {"text": self.strings["btn_watch"], "callback": self._panel_watching}],
            [{"text": self.strings["btn_profiles"], "callback": self._panel_profiles, "args": [pm_cid]}],
            [{"text": self.strings["btn_settings"], "callback": self._panel_settings}, {"text": self.strings["btn_stats"], "callback": self._panel_stats}]
        ]
        if edit: 
            await message.edit(text, reply_markup=btns)
        else: 
            await self.inline.form(text=text, message=message, reply_markup=btns)

    async def _panel_tasks(self, call): # описание ниже
        """Панель очереди задач со списком"""
        all_tasks = []
        for i, task in enumerate(self.task_queue, 1):
            task_with_num = task.copy()
            task_with_num['display_num'] = i
            all_tasks.append(task_with_num)
        if not all_tasks:
            text = self.strings["task_list_header"].format(total=0) + self.strings["no_tasks"]
            btns = [[{"text": self.strings["btn_back"], "callback": self._cb_back}]]
            await self._inline_edit(call, text, reply_markup=btns)
            return
        text = self.strings["task_list_header"].format(total=len(all_tasks))
        for task in all_tasks:
            num = task['display_num']
            src = utils.escape_html(task['src'][:20])
            dest = utils.escape_html(task['dest'][:20])
            status = task.get('status', 'queued')
            if status == 'running':
                active_data = self.active_dumps.get(task['tid'], {})
                current = active_data.get('current', 0)
                total = active_data.get('total_estimated', task.get('total_msgs', 0))
                progress = round((current / total * 100), 1) if total > 0 else 0
                text += self.strings["task_item_compact_running"].format(num=num, src=src, dest=dest, progress=progress) + "\n"
            elif status == 'paused':
                text += self.strings["task_item_compact_paused"].format(num=num, src=src, dest=dest) + "\n"
            elif status == 'completed':
                text += self.strings["task_item_compact_completed"].format(num=num, src=src, dest=dest) + "\n"
            elif status == 'stopped':
                text += self.strings["task_item_compact_stopped"].format(num=num, src=src, dest=dest) + "\n"
            elif status == 'error':
                text += self.strings["task_item_compact_error"].format(num=num, src=src, dest=dest) + "\n"
            else:
                wait_time = self._calculate_task_wait_time(task.get('position', num))
                text += self.strings["task_item_compact_queued"].format(num=num, src=src, dest=dest, wait=wait_time) + "\n"
        btns = []
        row = []
        for task in all_tasks:
            num = task['display_num']
            status = task.get('status', 'queued')
            emoji = "⏳" if status == 'queued' else "▶️" if status == 'running' else "⚠️" if status == 'paused' else "✅" if status == 'completed' else "❌"
            row.append({"text": f"{emoji}{num}", "callback": self._show_task_detail, "args": [task['tid'], num]})
            if len(row) == 5:
                btns.append(row)
                row = []
        if row:
            btns.append(row)
        btns.append([{"text": "🔄 Обновить", "callback": self._panel_tasks}])
        btns.append([{"text": self.strings["btn_back"], "callback": self._cb_back}])
        await self._inline_edit(call, text, reply_markup=btns)

    async def _show_task_detail(self, call, tid, num): # описание ниже
        """Детальный просмотр задачи с точным расчётом времени"""
        task = next((t for t in self.task_queue if t['tid'] == tid), None)
        if not task:
            history_task = next((t for t in self.task_history if t.get('tid') == tid), None)
            if history_task:
                await self._show_history_task_detail(call, history_task, num)
                return
            await call.answer("Задача не найдена")
            return
        status = task.get('status', 'queued')
        src = utils.escape_html(task['src'])
        dest = utils.escape_html(task['dest'])
        total = task.get('total_msgs', 0)
        position = task.get('position', num)
        if status == 'running':
            active_data = self.active_dumps.get(tid, {})
            current = active_data.get('current', 0)
            speed = active_data.get('current_speed', 0)
            start_ts = active_data.get('start_time', time.time())
            start_dt = self._time_from_ts(start_ts)
            start_time = self._format_clock(start_dt)
            elapsed = time.time() - start_ts
            elapsed_str = self._format_duration(elapsed)
            progress = round((current / total * 100), 1) if total > 0 else 0
            eta_left = self._calculate_eta(current, total, speed)
            end_time = self._calculate_end_time(start_dt, total - current, speed)
            text = self.strings["task_detail_running"].format(
                num=num, src=src, dest=dest, current=current, total=total,
                progress=progress, speed=round(speed, 1), eta_left=eta_left,
                elapsed=elapsed_str, start_time=start_time, end_time=end_time, position=position
            )
            btns = [
                [{"text": "⏸ Пауза", "callback": self._action_task, "args": [tid, "pause"]},
                 {"text": "🛑 Стоп", "callback": self._stop_specific, "args": [tid]}],
                [{"text": "🔙 К списку", "callback": self._panel_tasks}]
            ]
        elif status == 'queued':
            eta_start = self._calculate_task_wait_time(position)
            estimated = self._estimate_duration(total)
            text = self.strings["task_detail_queued"].format(
                num=num, src=src, dest=dest, total=total, eta_start=eta_start,
                position=position, estimated_duration=estimated
            )
            btns = [[{"text": "🗑 Удалить из очереди", "callback": self._remove_specific, "args": [tid]}],
                    [{"text": "🔙 К списку", "callback": self._panel_tasks}]
            ]
        elif status == 'paused':
            active_data = self.active_dumps.get(tid, {})
            current = active_data.get('current', 0)
            flood_count = active_data.get('flood_count', 0)
            flood_seconds = active_data.get('flood_total_seconds', 0)
            speed = active_data.get('current_speed', 0)
            resume_at = active_data.get('flood_wait_until', 0)
            resume_time = self._format_clock(resume_at) if resume_at else "неизвестно"
            progress = round((current / total * 100), 1) if total > 0 else 0
            remaining = max(0, total - current)
            text = self.strings["task_detail_paused"].format(
                num=num, src=src, dest=dest, current=current, total=total,
                progress=progress, flood_count=flood_count, 
                flood_time=self._format_duration(flood_seconds),
                resume_time=resume_time, speed=round(speed, 1), remaining=remaining
            )
            btns = [
                [{"text": "▶️ Продолжить", "callback": self._action_task, "args": [tid, "resume"]},
                 {"text": "🛑 Стоп", "callback": self._stop_specific, "args": [tid]}],
                [{"text": "🔙 К списку", "callback": self._panel_tasks}]
            ]
        elif status == 'completed':
            await self._show_history_task_detail(call, task, num)
            return
        elif status == 'stopped':
            text = f"<b>🛑 Задача #{num} останавливается</b>\n\n{src} → {dest}"
            btns = [[{"text": "🔙 К списку", "callback": self._panel_tasks}]]
        else:
            text = self.strings["task_detail_error"].format(num=num, src=src, dest=dest)
            btns = [
                [{"text": "🗑 Удалить", "callback": self._remove_specific, "args": [tid]}],
                [{"text": "🔙 К списку", "callback": self._panel_tasks}]
            ]
        await self._inline_edit(call, text, reply_markup=btns)

    async def _show_history_task_detail(self, call, task, num): # описание ниже
        """Показывает детали завершённой задачи"""
        src = utils.escape_html(task.get('src', 'Unknown'))
        dest = utils.escape_html(task.get('dest', 'Unknown'))
        count = task.get('current', 0)
        end_time = task.get('end_time', self._now())
        if isinstance(end_time, datetime):
            end_time_str = self._format_clock(end_time)
        else:
            end_time_str = str(end_time)
        start_ts = task.get('start_time', time.time())
        if isinstance(start_ts, (int, float)):
            start_dt = self._time_from_ts(start_ts)
            duration_seconds = time.time() - start_ts
        else:
            start_dt = start_ts
            duration_seconds = (end_time - start_ts).total_seconds() if isinstance(end_time, datetime) else 0
        duration_str = self._format_duration(duration_seconds)
        floods = task.get('flood_count', 0)
        avg_speed = round((count / duration_seconds) * 60, 1) if duration_seconds > 0 else 0
        text = self.strings["task_detail_completed"].format(
            num=num, src=src, dest=dest, count=count, duration=duration_str,
            avg_speed=avg_speed, end_time=end_time_str, floods=floods
        )
        btns = [[{"text": "🔙 К списку", "callback": self._panel_tasks}]]
        await self._inline_edit(call, text, reply_markup=btns)

    @staticmethod
    def _make_serializable(obj):
        if isinstance(obj, dict):
            return {k: ChatCopy._make_serializable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [ChatCopy._make_serializable(v) for v in obj]
        if isinstance(obj, datetime):
            return obj.timestamp()
        if isinstance(obj, (int, float, str, bool)) or obj is None:
            return obj
        return None  # рантайм-объекты (entity, Message, Event) в БД не храним

    def _save_tasks(self):
        tasks_to_save = []
        for task in self.task_queue:
            if task.get("status") in ["completed", "stopped", "error"]:
                continue
            snapshot = task.copy()
            tid = snapshot.get('tid')
            if tid and tid in self.active_dumps:
                live = self.active_dumps[tid]
                snapshot['current'] = live.get('current', snapshot.get('current', 0))
                snapshot['total_msgs'] = live.get('total_estimated', snapshot.get('total_msgs', 0))
            tasks_to_save.append(self._make_serializable(snapshot))
        self.db.set("ChatCopy", "persistent_queue", tasks_to_save)

    def _request_dump_stop(self, tid):
        changed = False
        if tid in self.active_dumps:
            self.active_dumps[tid]["status"] = "stopped"
            if "cancel" in self.active_dumps[tid]:
                self.active_dumps[tid]["cancel"].set()
            changed = True
        for task in self.task_queue:
            if task.get("tid") == tid:
                if tid in self.active_dumps:
                    task["status"] = "stopped"
                else:
                    task["status"] = "stopped"
                changed = True
        self._save_tasks()
        return changed

    async def _action_task(self, call, tid, action): # вот эта хрень держит все что находится в панели, лучше не трогать
        if tid in self.active_dumps:
            if action == "pause":
                self.active_dumps[tid]["status"] = "paused"
                self.active_dumps[tid]["cancel"].clear()
                for t in self.task_queue: 
                    if t['tid'] == tid: t['status'] = 'paused'
            elif action == "resume":
                self.active_dumps[tid]["status"] = "running"
                self.active_dumps[tid]["cancel"].set()
                for t in self.task_queue: 
                    if t['tid'] == tid: t['status'] = 'running'
            elif action == "stop":
                self._request_dump_stop(tid)
                return await self._panel_tasks(call)
        else:
            if action == "stop":
                self.task_queue = [t for t in self.task_queue if t['tid'] != tid]
                self._save_tasks()
                return await self._panel_tasks(call)
        self._save_tasks()
        await self._show_task_detail(call, tid, 0)

    async def _stop_specific(self, call, tid): # останавливаем определенную задачу (копирование)
        if tid in self.active_dumps:
            self._request_dump_stop(tid)
        else:
            self.task_queue = [t for t in self.task_queue if t['tid'] != tid]
        self._save_tasks() # сохраняем изменения
        await call.answer("Задача остановлена")
        await self._panel_tasks(call)

    async def _remove_specific(self, call, tid): # удаляем определенную задачу (копирование)
        if tid in self.active_dumps:
            self._request_dump_stop(tid)
        else:
            self.task_queue = [t for t in self.task_queue if t['tid'] != tid]
        self._save_tasks() # сохраняем изменения
        await call.answer("Задача удалена из очереди")
        await self._panel_tasks(call)

    async def _panel_watching(self, call): # часть панели под кнопкой "Слежка", где ватчер следит за чатами
        text = f"<b>👀 Слежка ({len(self.watchlist)})</b>\n\n"
        btns = []
        for i, (cid, cfg) in enumerate(self.watchlist.items(), 1):
            info = self.last_watched.get(cid, {"name": cid, "time": "—"})
            filter_name = self._get_filter_name(cfg.get("filter_type", FILTER_ALL))
            text += f"{i}. <b>{utils.escape_html(info['name'])}</b>\n   ID: <code>{cid}</code>\n   Фильтр: {filter_name}\n   Активность: {info['time']}\n\n"
            btns.append({"text": f"🗑 {i}", "callback": self._stop_watch, "args": [cid]})
        chunked_btns = utils.chunks(btns, 3) if btns else []
        chunked_btns.append([{"text": self.strings["btn_back"], "callback": self._cb_back}])
        await self._inline_edit(call, text or "<i>Пусто</i>", reply_markup=chunked_btns)

    async def _panel_settings(self, call): # ну тут очевидно, вместо кфг такие настроечки
        text = (
            f"<b>⚙️ Настройки</b>\n\n"
            f"<b>Batch size:</b> <code>{self.config['batch_size']}</code>\n"
            f"<b>Delay:</b> <code>{self.config['delay']} сек</code>\n"
            f"<b>FloodWait buffer:</b> <code>{self.config['flood_buffer']} сек</code>\n"
            f"<b>Timezone:</b> <code>UTC{self.config['timezone_offset']:+d}</code>"
        )
        btns = [
            [{"text": "📦 +10", "callback": self._change_setting, "args": ["batch_size", 10]},
             {"text": "📦 -10", "callback": self._change_setting, "args": ["batch_size", -10]}],
            [{"text": "⏱ +5с", "callback": self._change_setting, "args": ["delay", 5]},
             {"text": "⏱ -5с", "callback": self._change_setting, "args": ["delay", -5]}],
            [{"text": "🛡️ +5с буфер", "callback": self._change_setting, "args": ["flood_buffer", 5]},
             {"text": "🛡️ -5с буфер", "callback": self._change_setting, "args": ["flood_buffer", -5]}],
            [{"text": "🕒 UTC +1", "callback": self._change_setting, "args": ["timezone_offset", 1]},
             {"text": "🕒 UTC -1", "callback": self._change_setting, "args": ["timezone_offset", -1]}],
            [{"text": "🗑 Очистить кэш топиков", "callback": self._clear_topics_cache}],
            [{"text": self.strings["btn_back"], "callback": self._cb_back}]
        ]
        await self._inline_edit(call, text, reply_markup=btns)

    async def _panel_stats(self, call): # в панеле статус вызываем и смотрим чо как идет копирование
        total_tasks = len(self.task_stats)
        completed = sum(1 for t in self.task_stats.values() if t.get('completed_at'))
        stopped = total_tasks - completed
        total_floods = sum(t.get('flood_count', 0) for t in self.task_stats.values())
        total_flood_time = sum(t.get('flood_time', 0) for t in self.task_stats.values())
        avg_speeds = [t.get('avg_speed', 0) for t in self.task_stats.values() if t.get('avg_speed', 0) > 0]
        if self.current_dump_task and self.current_dump_task in self.active_dumps:
            active_task_data = self.active_dumps[self.current_dump_task]
            total_tasks += 1
            total_floods += active_task_data.get('flood_count', 0)
            total_flood_time += active_task_data.get('flood_total_seconds', 0)
            if active_task_data.get('current_speed', 0) > 0:
                avg_speeds.append(active_task_data['current_speed'])
        global_avg = round(sum(avg_speeds) / len(avg_speeds), 1) if avg_speeds else 0
        text = self.strings["stats_title"]
        text += self.strings["stats_total"].format(
            total=total_tasks,
            completed=completed,
            stopped=stopped,
            floods=total_floods
        )
        if global_avg > 0:
            text += f"\n⚡️ <b>Средняя скорость:</b> {global_avg} сообщений/мин"
        if total_flood_time > 0:
            hours = int(total_flood_time // 3600)
            mins = int((total_flood_time % 3600) // 60)
            text += f"\n⏱️ <b>Общее время FW:</b> {hours}ч {mins}м"
        btns = [[{"text": self.strings["btn_back"], "callback": self._cb_back}]]
        await self._inline_edit(call, text, reply_markup=btns)

    async def _change_setting(self, call, key, delta): # изменить настройки через панель чтоб в кфг не лезть
        current = self.config[key]
        if not isinstance(current, int):
            current = 10 if key == "delay" else 100 if key == "batch_size" else 5
        new_val = max(0, current + delta)
        if key == "batch_size":
            new_val = min(100, max(1, new_val))
        elif key == "flood_buffer":
            new_val = min(60, max(0, new_val))
        elif key == "timezone_offset":
            new_val = min(14, max(-12, new_val))
        else:
            new_val = max(1, new_val)
        self.config[key] = new_val
        await self._panel_settings(call)

    async def _clear_topics_cache(self, call): # ну, очевидно
        self.topic_mapping = {}
        self.topic_info_cache = {}
        self.db.set("ChatCopy", "topic_mapping", {})
        await call.answer("Кэш топиков очищен!")
        await self._panel_settings(call)

    async def _cb_back(self, call):  # кнопка назад
        await self._show_main_panel(call, edit=True)

    def _peer_to_chat_id(self, peer):
        """Converts Telethon peer objects to the same ids Message.chat_id uses."""
        if not peer:
            return 0
        try:
            return int(tl_utils.get_peer_id(peer))
        except Exception:
            pass
        cid = getattr(peer, "channel_id", 0)
        if cid:
            return int(f"-100{cid}")
        cid = getattr(peer, "chat_id", 0)
        if cid:
            return -int(cid) if int(cid) > 0 else int(cid)
        cid = getattr(peer, "user_id", 0)
        if cid:
            return int(cid)
        if isinstance(peer, int):
            return peer
        return 0

    def _chat_id_variants(self, cid):
        variants = []

        def add(value):
            if value in (None, "", 0, "0"):
                return
            value = str(value)
            if value not in variants:
                variants.append(value)
        add(cid)
        try:
            cid_int = int(cid)
        except (TypeError, ValueError):
            return variants
        add(cid_int)
        cid_str = str(cid_int)
        if cid_str.startswith("-100"):
            add(cid_str[4:])
            add(f"-{cid_str[4:]}")
        elif cid_int > 0:
            add(f"-100{cid_int}")
        elif cid_str.startswith("-"):
            add(cid_str[1:])
        return variants

    def _wizard_state_for_message(self, message):
        candidates = []
        for value in (
            getattr(message, "chat_id", None),
            self._peer_to_chat_id(getattr(message, "peer_id", None)),
            self._get_normalized_id(getattr(message, "chat", None)),
        ):
            candidates.extend(self._chat_id_variants(value))
        for key in candidates:
            ws = self._wizard_state.get(str(key))
            if ws:
                return str(key), ws
        return None, None

    async def _safe_resolve_profile_arg(self, text):
        """Resolves a chat argument without letting wizard input crash the module."""
        try:
            resolved = await self._resolve_arg(text)
        except Exception as e:
            logger.debug("Profile wizard resolve failed for %r: %s", text, e)
            return None
        if isinstance(resolved, tuple):
            return resolved[0] if resolved else None
        return resolved

    async def _safe_resolve_profile_input(self, text, role):
        """Resolves profile wizard input and interprets t.me/c links by step role."""
        try:
            resolved = await self._resolve_arg(text)
        except Exception as e:
            logger.debug("Profile wizard resolve failed for %r: %s", text, e)
            return None, {}
        if isinstance(resolved, tuple):
            entity, extra = resolved
        else:
            entity, extra = resolved, {}
        info = {}
        if role == "src":
            if extra.get("msg"):
                info["src_topic_id"] = extra.get("topic")
                info["start_id"] = extra.get("msg")
            elif extra.get("topic"):
                info["start_id"] = extra.get("topic")
        elif role == "dst":
            if extra.get("topic"):
                info["dest_topic_id"] = extra.get("topic")
        return entity, info

    async def _profile_start_from_text(self, text):
        text = (text or "").strip()
        low = text.lower()
        if low in ("0", "-", "нет", "сначала", "с начала", "new", "новый"):
            return 0
        if text.isdigit():
            return max(int(text), 0)
        _, info = await self._safe_resolve_profile_input(text, "src")
        if info.get("start_id"):
            return max(int(info.get("start_id", 0) or 0), 0)
        return None

    def _profile_start_display(self, start_id):
        start_id = int(start_id or 0)
        return str(start_id) if start_id > 0 else "С начала"

    def _profile_topic_display(self, topic_id):
        topic_id = int(topic_id or 0)
        return str(topic_id) if topic_id > 0 else "Авто/нет"

    def _profile_end_display(self, final_id):
        final_id = int(final_id or 0)
        return str(final_id) if final_id > 0 else "Без ограничения"

    def _profile_next_id(self, p):
        start_id = int(p.get("start_id", 0) or 0)
        last_id = int(p.get("last_processed_id", 0) or 0)
        if last_id > 0:
            return last_id + 1
        return start_id if start_id > 0 else 0

    def _profile_c_id(self, chat_id):
        value = str(chat_id or "").strip()
        if not value:
            return None
        if value.startswith("-100"):
            value = value[4:]
        elif value.startswith("-"):
            value = value[1:]
        return value if value.isdigit() else None

    def _profile_c_link(self, chat_id, *parts):
        base = self._profile_c_id(chat_id)
        clean_parts = []
        for part in parts:
            try:
                part = int(part or 0)
            except (TypeError, ValueError):
                part = 0
            if part > 0:
                clean_parts.append(str(part))
        if not base or not clean_parts:
            return None
        return f"https://t.me/c/{base}/{'/'.join(clean_parts)}"

    def _profile_source_link(self, p, message_id=None):
        topic_id = int(p.get("src_topic_id", 0) or 0)
        message_id = int(message_id or 0)
        if topic_id > 0 and message_id > 0:
            return self._profile_c_link(p.get("src_id"), topic_id, message_id)
        if message_id > 0:
            return self._profile_c_link(p.get("src_id"), message_id)
        if topic_id > 0:
            return self._profile_c_link(p.get("src_id"), topic_id)
        return None

    def _profile_dest_link(self, p):
        dest_topic = int(p.get("dest_topic_id", 0) or 0)
        if dest_topic > 0:
            return self._profile_c_link(p.get("dest_id"), dest_topic)
        return None

    def _html_link(self, text, url=None, code=False, bold=False):
        text = utils.escape_html(str(text))
        if url:
            return f'<a href="{url}">{text}</a>'
        if code:
            text = f"<code>{text}</code>"
        elif bold:
            text = f"<b>{text}</b>"
        return text

    def _profile_next_display(self, p, linked=False):
        next_id = self._profile_next_id(p)
        final_id = int(p.get("final_id", 0) or 0)
        if final_id > 0 and next_id > final_id:
            return "Конец достигнут"
        if next_id <= 0:
            return "С начала"
        return self._html_link(next_id, self._profile_source_link(p, next_id) if linked else None, code=True)

    def _profile_topic_display_linked(self, p, role):
        if role == "src":
            topic_id = int(p.get("src_topic_id", 0) or 0)
            url = self._profile_source_link(p)
        else:
            topic_id = int(p.get("dest_topic_id", 0) or 0)
            url = self._profile_dest_link(p)
        if topic_id <= 0:
            return "Авто/нет"
        return self._html_link(topic_id, url, code=True)

    def _profile_chat_display(self, p, role):
        if role == "src":
            name = str(p.get("src_name", p.get("src_id", "?")))[:25]
            url = self._profile_source_link(p, self._profile_next_id(p))
        else:
            name = str(p.get("dest_name", p.get("dest_id", "?")))[:25]
            url = self._profile_dest_link(p)
        return self._html_link(name, url, bold=not url)

    def _profile_details(self, p):
        parts = []
        next_id = self._profile_next_id(p)
        dest_topic = int(p.get("dest_topic_id", 0) or 0)
        src_topic = int(p.get("src_topic_id", 0) or 0)
        final_id = int(p.get("final_id", 0) or 0)
        if final_id > 0 and next_id > final_id:
            parts.append("конец достигнут")
        elif next_id > 0:
            parts.append(f"след. {self._profile_next_display(p, linked=True)}")
        else:
            parts.append("с начала")
        if final_id > 0:
            parts.append(f"до {self._html_link(final_id, self._profile_source_link(p, final_id), code=True)}")
        if src_topic > 0:
            parts.append(f"ист.топик {self._profile_topic_display_linked(p, 'src')}")
        if dest_topic > 0:
            parts.append(f"топик {self._profile_topic_display_linked(p, 'dst')}")
        return f" ({', '.join(parts)})" if parts else ""

    def _profiles_step_view(self, ws):
        cid = ws.get("cid", 0)
        step = ws.get("step", "src")
        if step == "src":
            btns = []
            if ws.get("src_id"):
                btns.append([{"text": self.strings["profiles_btn_next"], "callback": self._profiles_wizard_goto, "args": ["dst", cid]}])
            btns.append([{"text": self.strings["profiles_btn_cancel_wizard"], "callback": self._profiles_wizard_cancel, "args": [cid]}])
            return self.strings["profiles_wizard_title"] + self.strings["profiles_wizard_ask_src"], btns
        if step == "dst":
            btns = [[{"text": self.strings["profiles_btn_back_wizard"], "callback": self._profiles_wizard_goto, "args": ["src", cid]}]]
            if ws.get("dest_id"):
                btns[0].append({"text": self.strings["profiles_btn_next"], "callback": self._profiles_wizard_goto, "args": ["start", cid]})
            btns.append([{"text": self.strings["profiles_btn_cancel_wizard"], "callback": self._profiles_wizard_cancel, "args": [cid]}])
            return self.strings["profiles_wizard_title"] + self.strings["profiles_wizard_ask_dst"], btns
        if step == "start":
            detected = self._profile_start_display(ws.get("detected_start_id", 0))
            current = self._profile_start_display(ws.get("start_id", 0))
            text = self.strings["profiles_wizard_title"] + self.strings["profiles_wizard_ask_start"].format(
                src=utils.escape_html(str(ws.get("src_name", "?"))),
                detected=detected,
                current=current,
            )
            btns = []
            detected_id = int(ws.get("detected_start_id", 0) or 0)
            if detected_id > 0:
                btns.append([{"text": self.strings["profiles_btn_use_detected"].format(id=detected_id), "callback": self._profiles_start_set, "args": ["detected", cid]}])
            btns.append([{"text": self.strings["profiles_btn_from_start"], "callback": self._profiles_start_set, "args": ["zero", cid]}])
            btns.append([
                {"text": self.strings["profiles_btn_back_wizard"], "callback": self._profiles_wizard_goto, "args": ["dst", cid]},
                {"text": self.strings["profiles_btn_next"], "callback": self._profiles_wizard_goto, "args": ["flags", cid]},
            ])
            btns.append([{"text": self.strings["profiles_btn_cancel_wizard"], "callback": self._profiles_wizard_cancel, "args": [cid]}])
            return text, btns
        return self._profiles_flags_view(ws)

    def _profiles_flags_view(self, ws):
        fmap = {
            FILTER_ALL: "Всё",
            FILTER_MEDIA: "Медиа",
            FILTER_PHOTO_VIDEO: "Фото/Видео",
            FILTER_DOCS: "Документы",
            FILTER_TEXT: "Текст",
        }
        amap = {True: "Без автора", False: "С автором"}
        cmap = {True: "Без подписей", False: "С подписями"}
        text = self.strings["profiles_wizard_title"] + self.strings["profiles_wizard_ask_flags"].format(
            src=utils.escape_html(str(ws.get("src_name", "?"))),
            dst=utils.escape_html(str(ws.get("dest_name", "?"))),
            start=self._profile_start_display(ws.get("start_id", 0)),
            dest_topic=self._profile_topic_display(ws.get("dest_topic_id", 0)),
            filter=fmap.get(ws.get("filter_type", FILTER_ALL), "Всё"),
            auth=amap.get(ws.get("no_author", True), "?"),
            capt=cmap.get(ws.get("no_captions", False), "?"),
            ignored=self._format_ignored_topics(ws.get("ignored_topics", [])),
        )
        cid = ws.get("cid", 0)
        btns = [
            [{"text": self.strings["profiles_btn_toggle_filter"].format(val=fmap.get(ws.get("filter_type", FILTER_ALL), "Всё")), "callback": self._profiles_flags_toggle, "args": ["filter", cid]}],
            [{"text": self.strings["profiles_btn_toggle_auth"].format(val=amap.get(ws.get("no_author", True), "?")), "callback": self._profiles_flags_toggle, "args": ["auth", cid]}],
            [{"text": self.strings["profiles_btn_toggle_capt"].format(val=cmap.get(ws.get("no_captions", False), "?")), "callback": self._profiles_flags_toggle, "args": ["capt", cid]}],
            [
                {"text": self.strings["profiles_btn_change_src"], "callback": self._profiles_wizard_goto, "args": ["src", cid]},
                {"text": self.strings["profiles_btn_change_dst"], "callback": self._profiles_wizard_goto, "args": ["dst", cid]},
                {"text": self.strings["profiles_btn_change_start"], "callback": self._profiles_wizard_goto, "args": ["start", cid]},
            ],
            [
                {"text": self.strings["profiles_btn_back_wizard"], "callback": self._profiles_wizard_goto, "args": ["start", cid]},
                {"text": self.strings["profiles_btn_save"], "callback": self._profiles_flags_save, "args": [cid]},
            ],
            [{"text": self.strings["profiles_btn_cancel_wizard"], "callback": self._profiles_wizard_cancel, "args": [cid]}],
        ]
        return text, btns

    async def _edit_wizard_panel(self, ws, text, reply_markup):
        call = ws.get("call")
        if not call:
            return False
        try:
            await self._inline_edit(call, text, reply_markup=reply_markup)
            return True
        except Exception as e:
            logger.debug("Profile wizard panel edit failed: %s", e)
            return False

    def _call_chat_id(self, call):
        """Безопасно получает chat_id из inline callback."""
        # 1) прямой chat_id
        cid = getattr(call, "chat_id", 0)
        if cid and cid != 0:
            return cid
        # 2) через message (основной путь для Telethon CallbackQuery)
        msg = getattr(call, "message", None)
        if msg:
            cid = getattr(msg, "chat_id", 0)
            if cid and cid != 0:
                return cid
            # peer_id может быть PeerChannel/PeerUser/PeerChat объектом
            peer = getattr(msg, "peer_id", None)
            if peer:
                cid = self._peer_to_chat_id(peer)
                if cid and cid != 0:
                    return cid
        # 3 original_update (Telethon raw update)
        ou = getattr(call, "original_update", None)
        if ou:
            cid = getattr(ou, "chat_id", 0) or self._peer_to_chat_id(getattr(ou, "peer", None))
            if cid and cid != 0:
                return cid
        # 4 query (CallbackQuery объект)
        q = getattr(call, "query", None)
        if q:
            cid = getattr(q, "chat_id", 0) or self._peer_to_chat_id(getattr(q, "peer_id", None))
            if cid and not isinstance(cid, type) and cid != 0:
                return int(cid) if isinstance(cid, (int, str)) else 0
        # 5 _client + get_messages через message_id
        mid = getattr(call, "message_id", None) or getattr(call, "id", None)
        client = getattr(call, "_client", None) or getattr(self, "client", None)
        if mid and client:
            try:
                # если не можем вызвать get_messages без chat_id
                pass
            except Exception:
                pass
        return self._last_panel_cid or 0

    def _profiles_save(self):
        self.db.set("ChatCopy", "profiles", self.profiles)

    def _profiles_flag_icons(self, p):
        """Собирает строку флагов-эмодзи для профиля."""
        fm = {
            FILTER_ALL: self.strings["profiles_flag_filter_all"],
            FILTER_MEDIA: self.strings["profiles_flag_filter_media"],
            FILTER_PHOTO_VIDEO: self.strings["profiles_flag_filter_photo_video"],
            FILTER_DOCS: self.strings["profiles_flag_filter_docs"],
            FILTER_TEXT: self.strings["profiles_flag_filter_text"],
        }
        flags = fm.get(p.get("filter_type", FILTER_ALL), "📄")
        flags += self.strings["profiles_flag_noauth"] if p.get("no_author") else self.strings["profiles_flag_auth"]
        flags += self.strings["profiles_flag_nocapt"] if p.get("no_captions") else self.strings["profiles_flag_capt"]
        return flags

    async def _panel_profiles(self, call, cid=0):
        """Панель со списком профилей."""
        if not cid:
            cid = self._call_chat_id(call) or self._last_panel_cid or 0
        if cid:
            self._last_panel_cid = cid
        if not self.profiles:
            text = self.strings["profiles_title"] + self.strings["profiles_empty"]
            btns = [
                [{"text": self.strings["profiles_btn_create"], "callback": self._profiles_create_start, "args": [cid]}],
                [{"text": self.strings["btn_back"], "callback": self._cb_back}]
            ]
            await self._inline_edit(call, text, reply_markup=btns)
            return
        text = self.strings["profiles_title"]
        for i, (pid, p) in enumerate(self.profiles.items(), 1):
            flags = self._profiles_flag_icons(p)
            src = self._profile_chat_display(p, "src")
            dst = self._profile_chat_display(p, "dst")
            details = self._profile_details(p)
            text += self.strings["profiles_item"].format(num=i, flags=flags, src=src, dst=dst, details=details)
        btns = []
        row = []
        for i in range(1, len(self.profiles) + 1):
            row.append({"text": str(i), "callback": self._profile_detail, "args": [i, cid]})
            if len(row) >= 5:
                btns.append(row)
                row = []
        if row:
            btns.append(row)
        btns.append([
            {"text": self.strings["profiles_btn_create"], "callback": self._profiles_create_start, "args": [cid]},
            {"text": self.strings["profiles_btn_delete"], "callback": self._profiles_delete_ask, "args": [cid]},
        ])
        btns.append([
            {"text": self.strings["profiles_btn_reset"], "callback": self._profiles_reset_ask, "args": [cid]},
            {"text": self.strings["btn_back"], "callback": self._cb_back},
        ])
        await self._inline_edit(call, text, reply_markup=btns)

    async def _profiles_delete_ask(self, call, cid=0):
        """Спрашивает какой профиль удалить."""
        if not self.profiles:
            await call.answer("Нет профилей.")
            return
        btns = []
        for i, pid in enumerate(self.profiles.keys(), 1):
            btns.append([{"text": f"🗑 {i}", "callback": self._profile_delete, "args": [i, cid]}])
        btns.append([{"text": self.strings["btn_back"], "callback": self._panel_profiles, "args": [cid]}])
        await self._inline_edit(call, "<b>🗑 Какой профиль удалить?</b>", reply_markup=btns)

    async def _profiles_reset_ask(self, call, cid=0):
        """Спрашивает какой профиль сбросить."""
        if not self.profiles:
            await call.answer("Нет профилей.")
            return
        btns = []
        for i, pid in enumerate(self.profiles.keys(), 1):
            btns.append([{"text": f"🔄 {i}", "callback": self._profile_reset, "args": [i, cid]}])
        btns.append([{"text": self.strings["btn_back"], "callback": self._panel_profiles, "args": [cid]}])
        await self._inline_edit(call, "<b>🔄 Какой профиль сбросить к стартовой точке?</b>", reply_markup=btns)

    def _profile_by_num(self, num):
        """Возвращает (pid, profile) по порядковому номеру."""
        try:
            pid = list(self.profiles.keys())[num - 1]
            return pid, self.profiles[pid]
        except (IndexError, ValueError):
            return None, None

    def _profile_text_values(self, p):
        last_id = int(p.get("last_processed_id", 0) or 0)
        return {
            "src": self._profile_chat_display(p, "src"),
            "dst": self._profile_chat_display(p, "dst"),
            "start": self._profile_start_display(p.get("start_id", 0)),
            "next": self._profile_next_display(p, linked=True),
            "end": self._profile_end_display(p.get("final_id", 0)),
            "last": str(last_id) if last_id > 0 else "Не запускался",
            "src_topic": self._profile_topic_display_linked(p, "src"),
            "dest_topic": self._profile_topic_display_linked(p, "dst"),
            "filter": self._get_filter_name(p.get("filter_type", FILTER_ALL)),
            "auth": "Без автора" if p.get("no_author", True) else "С автором",
            "capt": "Без подписей" if p.get("no_captions", False) else "С подписями",
        }

    def _profile_detail_buttons(self, num, cid, p):
        fmap = {
            FILTER_ALL: "Всё",
            FILTER_MEDIA: "Медиа",
            FILTER_PHOTO_VIDEO: "Фото/Видео",
            FILTER_DOCS: "Документы",
            FILTER_TEXT: "Текст",
        }
        auth = "Без автора" if p.get("no_author", True) else "С автором"
        capt = "Без подписей" if p.get("no_captions", False) else "С подписями"
        return [
            [{"text": self.strings["profiles_btn_run"], "callback": self._profile_run_ask, "args": [num, cid]}],
            [
                {"text": self.strings["profiles_btn_edit"], "callback": self._profile_edit_start, "args": [num, cid]},
                {"text": self.strings["profiles_btn_range"], "callback": self._profile_range_settings, "args": [num, cid]},
            ],
            [{"text": self.strings["profiles_btn_toggle_filter"].format(val=fmap.get(p.get("filter_type", FILTER_ALL), "Всё")), "callback": self._profile_toggle_setting, "args": [num, "filter", cid]}],
            [{"text": self.strings["profiles_btn_toggle_auth"].format(val=auth), "callback": self._profile_toggle_setting, "args": [num, "auth", cid]}],
            [{"text": self.strings["profiles_btn_toggle_capt"].format(val=capt), "callback": self._profile_toggle_setting, "args": [num, "capt", cid]}],
            [
                {"text": self.strings["profiles_btn_reset"], "callback": self._profile_reset_detail, "args": [num, cid]},
                {"text": self.strings["profiles_btn_delete"], "callback": self._profile_delete_confirm, "args": [num, cid]},
            ],
            [{"text": self.strings["btn_back"], "callback": self._panel_profiles, "args": [cid]}],
        ]

    async def _profile_detail(self, call, num, cid=0):
        if not cid:
            cid = self._call_chat_id(call) or self._last_panel_cid or 0
        pid, prof = self._profile_by_num(num)
        if not prof:
            await call.answer(self.strings["profiles_not_found"].format(num=num))
            return
        vals = self._profile_text_values(prof)
        await self._inline_edit(call, 
            self.strings["profiles_detail"].format(num=num, **vals),
            reply_markup=self._profile_detail_buttons(num, cid, prof),
        )

    async def _profile_run_ask(self, call, num, cid=0):
        if not cid:
            cid = self._call_chat_id(call) or self._last_panel_cid or 0
        pid, prof = self._profile_by_num(num)
        if not prof:
            await call.answer(self.strings["profiles_not_found"].format(num=num))
            return
        vals = self._profile_text_values(prof)
        await self._inline_edit(call, 
            self.strings["profiles_run_confirm"].format(num=num, **vals),
            reply_markup=[
                [{"text": self.strings["profiles_btn_confirm_run"], "callback": self._profile_run, "args": [num, cid]}],
                [{"text": self.strings["btn_back"], "callback": self._profile_detail, "args": [num, cid]}],
            ],
        )

    async def _profile_toggle_setting(self, call, num, what, cid=0):
        if not cid:
            cid = self._call_chat_id(call) or self._last_panel_cid or 0
        pid, prof = self._profile_by_num(num)
        if not prof:
            await call.answer(self.strings["profiles_not_found"].format(num=num))
            return
        if what == "filter":
            order = [FILTER_ALL, FILTER_MEDIA, FILTER_PHOTO_VIDEO, FILTER_DOCS, FILTER_TEXT]
            cur = prof.get("filter_type", FILTER_ALL)
            prof["filter_type"] = order[(order.index(cur) + 1) % len(order)] if cur in order else FILTER_ALL
        elif what == "auth":
            prof["no_author"] = not prof.get("no_author", True)
        elif what == "capt":
            prof["no_captions"] = not prof.get("no_captions", False)
        self._profiles_save()
        await self._profile_detail(call, num, cid)

    async def _profile_reset_detail(self, call, num, cid=0):
        pid, prof = self._profile_by_num(num)
        if not pid:
            await call.answer(self.strings["profiles_not_found"].format(num=num))
            return
        start_id = int(self.profiles[pid].get("start_id", 0) or 0)
        self.profiles[pid]["last_processed_id"] = start_id - 1 if start_id > 0 else 0
        self._profiles_save()
        await call.answer(self.strings["profiles_reset"].format(num=num))
        await self._profile_detail(call, num, cid)

    async def _profile_delete_confirm(self, call, num, cid=0):
        pid, prof = self._profile_by_num(num)
        if not prof:
            await call.answer(self.strings["profiles_not_found"].format(num=num))
            return
        vals = self._profile_text_values(prof)
        await self._inline_edit(call, 
            f"<b>🗑 Удалить профиль #{num}?</b>\n\n{vals['src']} → {vals['dst']}",
            reply_markup=[
                [{"text": self.strings["profiles_btn_delete"], "callback": self._profile_delete, "args": [num, cid]}],
                [{"text": self.strings["btn_back"], "callback": self._profile_detail, "args": [num, cid]}],
            ],
        )

    async def _profile_range_settings(self, call, num, cid=0):
        if not cid:
            cid = self._call_chat_id(call) or self._last_panel_cid or 0
        for key in self._chat_id_variants(cid):
            ws = self._wizard_state.get(str(key))
            if ws and str(ws.get("step", "")).startswith("profile_range_"):
                self._wizard_state.pop(str(key), None)
        pid, prof = self._profile_by_num(num)
        if not prof:
            await call.answer(self.strings["profiles_not_found"].format(num=num))
            return
        text, buttons = self._profile_range_view(num, cid, prof)
        await self._inline_edit(call, text, reply_markup=buttons)

    async def _profile_range_ask(self, call, num, what, cid=0):
        if not cid:
            cid = self._call_chat_id(call) or self._last_panel_cid or 0
        pid, prof = self._profile_by_num(num)
        if not prof:
            await call.answer(self.strings["profiles_not_found"].format(num=num))
            return
        ckey = str(cid)
        self._wizard_state[ckey] = {
            "step": f"profile_range_{what}",
            "cid": cid,
            "call": call,
            "profile_num": num,
            "profile_pid": pid,
        }
        text_key = "profiles_range_ask_start" if what == "start" else "profiles_range_ask_end"
        await self._inline_edit(call, 
            self.strings[text_key].format(num=num),
            reply_markup=[[{"text": self.strings["btn_back"], "callback": self._profile_range_settings, "args": [num, cid]}]],
        )

    async def _profile_range_clear_end(self, call, num, cid=0):
        pid, prof = self._profile_by_num(num)
        if not prof:
            await call.answer(self.strings["profiles_not_found"].format(num=num))
            return
        prof["final_id"] = 0
        self._profiles_save()
        await self._profile_range_settings(call, num, cid)

    async def _profile_range_apply(self, message, ws, cid, text):
        num = ws.get("profile_num")
        pid = ws.get("profile_pid")
        if pid not in self.profiles:
            await utils.answer(message, self.strings["profiles_not_found"].format(num=num))
            return True
        value = await self._profile_start_from_text(text)
        if value is None:
            await utils.answer(message, "❌ Отправь ID сообщения числом, ссылку на сообщение или 0.")
            return True
        prof = self.profiles[pid]
        if ws.get("step") == "profile_range_start":
            final_id = int(prof.get("final_id", 0) or 0)
            if final_id > 0 and value > final_id:
                await utils.answer(message, "❌ Стартовый ID не может быть больше конечного ID.")
                return True
            prof["start_id"] = value
            prof["last_processed_id"] = value - 1 if value > 0 else 0
        else:
            start_id = int(prof.get("start_id", 0) or 0)
            if value > 0 and start_id > 0 and value < start_id:
                await utils.answer(message, "❌ Конечный ID не может быть меньше стартового ID.")
                return True
            prof["final_id"] = value
        self._profiles_save()
        for key in self._chat_id_variants(cid):
            self._wizard_state.pop(str(key), None)
        edited = await self._edit_wizard_panel(ws, *self._profile_range_view(num, cid, prof))
        if not edited:
            await utils.answer(message, self.strings["profiles_range_settings"].format(num=num, **self._profile_text_values(prof)))
        else:
            try:
                await message.delete()
            except Exception:
                pass
        return True

    def _profile_range_view(self, num, cid, prof):
        vals = self._profile_text_values(prof)
        text = self.strings["profiles_range_settings"].format(num=num, **vals)
        buttons = [
            [
                {"text": self.strings["profiles_btn_set_start"], "callback": self._profile_range_ask, "args": [num, "start", cid]},
                {"text": self.strings["profiles_btn_set_end"], "callback": self._profile_range_ask, "args": [num, "end", cid]},
            ],
            [{"text": self.strings["profiles_btn_clear_end"], "callback": self._profile_range_clear_end, "args": [num, cid]}],
            [{"text": self.strings["btn_back"], "callback": self._profile_detail, "args": [num, cid]}],
        ]
        return text, buttons

    async def _profile_edit_start(self, call, num, cid=0):
        if not cid:
            cid = self._call_chat_id(call) or self._last_panel_cid or 0
        pid, prof = self._profile_by_num(num)
        if not prof:
            await call.answer(self.strings["profiles_not_found"].format(num=num))
            return
        self._last_panel_cid = cid
        ckey = str(cid)
        self._wizard_state[ckey] = {
            "step": "flags",
            "cid": cid,
            "call": call,
            "edit_pid": pid,
            "edit_num": num,
            "src_id": prof.get("src_id"),
            "src_name": prof.get("src_name", prof.get("src_id", "?")),
            "src_topic_id": int(prof.get("src_topic_id", 0) or 0),
            "dest_id": prof.get("dest_id"),
            "dest_name": prof.get("dest_name", prof.get("dest_id", "?")),
            "dest_topic_id": int(prof.get("dest_topic_id", 0) or 0),
            "start_id": int(prof.get("start_id", 0) or 0),
            "detected_start_id": int(prof.get("start_id", 0) or 0),
            "final_id": int(prof.get("final_id", 0) or 0),
            "filter_type": prof.get("filter_type", FILTER_ALL),
            "no_author": prof.get("no_author", True),
            "no_captions": prof.get("no_captions", False),
            "ignored_topics": prof.get("ignored_topics", []),
        }
        await self._profiles_show_wizard_step(call, self._wizard_state[ckey])

    async def _profile_run(self, call, num, cid=0):
        """Запускает копирование по профилю (ищет новые сообщения с last_processed_id)."""
        if not cid:
            cid = self._call_chat_id(call) or self._last_panel_cid or 0
        pid, prof = self._profile_by_num(num)
        if not prof:
            await call.answer(self.strings["profiles_not_found"].format(num=num))
            return
        await call.answer("Запускаю...")
        try:
            src_entity = await self._safe_resolve_profile_arg(prof["src_id"])
            dest_entity = await self._safe_resolve_profile_arg(prof["dest_id"])
            if not src_entity or not dest_entity:
                await self._inline_edit(call, "❌ Не удалось найти чат источника или цели.", reply_markup=[[{"text": self.strings["btn_back"], "callback": self._panel_profiles, "args": [cid]}]])
                return
        except Exception as e:
            await self._inline_edit(call, f"❌ Ошибка: {e}", reply_markup=[[{"text": self.strings["btn_back"], "callback": self._panel_profiles, "args": [cid]}]])
            return
        src_title = getattr(src_entity, "title", prof["src_id"])
        dst_title = getattr(dest_entity, "title", prof["dest_id"])
        # запрет пересылки обходится автоматически на лету (bypass mode)
        fixed_dest_topic = int(prof.get("dest_topic_id", 0) or 0) or None
        map_t = self._is_forum(src_entity)
        if (map_t or fixed_dest_topic) and not self._is_forum(dest_entity):
            if await self._ensure_forum_enabled(dest_entity):
                try:
                    dest_entity = await self.client.get_entity(getattr(dest_entity, "id", dest_entity))
                except Exception:
                    pass
            if fixed_dest_topic and not self._is_forum(dest_entity):
                await self._inline_edit(call, 
                    self.strings["forum_enable_failed"].format(chat=utils.escape_html(str(dst_title))),
                    reply_markup=[[{"text": self.strings["btn_back"], "callback": self._panel_profiles, "args": [cid]}]],
                )
                return
            if map_t and not self._is_forum(dest_entity):
                logger.warning("Profile %s: destination is not a forum; topic mapping disabled", pid)
                map_t = False
        if fixed_dest_topic:
            logger.info("Profile %s will send to fixed destination topic %s", pid, fixed_dest_topic)
        last_id = prof.get("last_processed_id", 0)
        if not last_id:
            start_id = int(prof.get("start_id", 0) or 0)
            last_id = start_id - 1 if start_id > 0 else 0
        ignored = prof.get("ignored_topics", [])
        filter_type = prof.get("filter_type", FILTER_ALL)
        final_id = int(prof.get("final_id", 0) or 0)
        fixed_src_topic = int(prof.get("src_topic_id", 0) or 0) or None
        if fixed_dest_topic:
            map_t = False

        await self._inline_edit(call, 
            self.strings["preparing"],
            reply_markup=[[{"text": self.strings["btn_back"], "callback": self._profile_detail, "args": [num, cid]}]],
        )
        total_msgs = 0
        try:
            count_kwargs = {"min_id": last_id}
            if final_id > 0:
                count_kwargs["max_id"] = final_id + 1
            if fixed_src_topic:
                count_kwargs["reply_to"] = fixed_src_topic
            async for _ in self.client.iter_messages(src_entity, **count_kwargs):
                total_msgs += 1
                if total_msgs > 150000:
                    break
        except Exception as e:
            logger.warning("Profile count failed: %s", e)
            total_msgs = -1
        filter_name = self._get_filter_name(filter_type)
        ignored_str = self._format_ignored_topics(ignored)
        mode_str = f"🧵 Топик {fixed_dest_topic}" if fixed_dest_topic else ("🗂️ Топики (Auto)" if map_t else "Обычный")
        start_id_str = "С начала" if last_id <= 0 else f"с {last_id + 1}"
        if final_id > 0:
            start_id_str += f" до {final_id}"
        try:
            _src_pid = int(self._get_normalized_id(src_entity))
            if await self._source_has_copy_restriction(src_entity):
                self._restricted_srcs.add(_src_pid)  # авто-обход запрета пересылки (bypass mode) для профилей
        except Exception:
            _src_pid = None
        bypass_str = "Авто-скачка (запрет пересылки)" if (_src_pid is not None and _src_pid in self._restricted_srcs) else "Нет (обычная пересылка)"
        await self._inline_edit(call, 
            self.strings["copy_start"].format(
                src=utils.escape_html(str(src_title)),
                dest=utils.escape_html(str(dst_title)),
                mode=mode_str,
                start_id=start_id_str,
                no_auth="Да" if prof.get("no_author", True) else "Нет",
                no_capt="Да" if prof.get("no_captions", False) else "Нет",
                filter_type=filter_name,
                ignored_topics=ignored_str,
                total_msgs=total_msgs if total_msgs > -1 else "∞ (ошибка подсчета)",
                estimated_time=self._estimate_duration(total_msgs),
                position="профиль",
                bypass=bypass_str,
            ),
            reply_markup=[[{"text": self.strings["btn_back"], "callback": self._profile_detail, "args": [num, cid]}]],
        )
        count = 0
        profile_failed = False
        start_time = time.time()
        profile_tid = f"prf_{pid}"
        profile_cancel = asyncio.Event()
        profile_cancel.set()
        self.active_dumps[profile_tid] = {
            "name": f"Profile #{num}",
            "cancel": profile_cancel,
            "status": "running",
            "current": 0,
            "total_estimated": total_msgs if total_msgs > -1 else 0,
            "start_time": start_time,
            "speed_samples": [],
            "flood_total_seconds": 0,
            "flood_count": 0,
            "last_successful_send": time.time(),
            "consecutive_floods": 0,
            "current_speed": 0,
            "status_chat_id": cid,
        }
        batch = []
        try:
            iter_kwargs = {"min_id": last_id, "reverse": True}
            if final_id > 0:
                iter_kwargs["max_id"] = final_id + 1
            if fixed_src_topic:
                iter_kwargs["reply_to"] = fixed_src_topic
            async for msg in self.client.iter_messages(src_entity, **iter_kwargs):
                if self.active_dumps.get(profile_tid, {}).get("status") in ("stopped", "error"):
                    profile_failed = True
                    break
                if isinstance(msg, types.MessageService):
                    continue
                if final_id > 0 and msg.id > final_id:
                    break
                if not self._should_include_message(msg, filter_type):
                    self.profiles[pid]["last_processed_id"] = msg.id
                    self._profiles_save()
                    continue
                batch.append(msg)
                if len(batch) >= self._get_effective_batch_size():
                    sent = await self._process_batch(
                        messages=list(batch),
                        dest_id=int(self._get_normalized_id(dest_entity)),
                        no_author=prof.get("no_author", True),
                        no_captions=prof.get("no_captions", False),
                        fixed_dest_topic=fixed_dest_topic,
                        map_topics=map_t,
                        dest_entity=dest_entity,
                        src_entity=src_entity,
                        filter_type=filter_type,
                        ignored_topics=ignored,
                        tid=profile_tid,
                    )
                    if self.active_dumps.get(profile_tid, {}).get("status") == "error":
                        logger.error("Profile %s stopped on batch error; last_processed_id not advanced", pid)
                        profile_failed = True
                        break
                    count += sent
                    self.active_dumps[profile_tid]["current"] = count
                    # сюда доходим только если статус != "error" (проверено выше):
                    # sent==0 здесь = «в батче нечего слать» (фильтр/игнор)
                    if batch:
                        self.profiles[pid]["last_processed_id"] = batch[-1].id
                        self._profiles_save()
                    batch = []
            if batch and not profile_failed:
                sent = await self._process_batch(
                    messages=list(batch),
                    dest_id=int(self._get_normalized_id(dest_entity)),
                    no_author=prof.get("no_author", True),
                    no_captions=prof.get("no_captions", False),
                    fixed_dest_topic=fixed_dest_topic,
                    map_topics=map_t,
                    dest_entity=dest_entity,
                    src_entity=src_entity,
                    filter_type=filter_type,
                    ignored_topics=ignored,
                    tid=profile_tid,
                )
                if self.active_dumps.get(profile_tid, {}).get("status") == "error":
                    logger.error("Profile %s stopped on final batch error; last_processed_id not advanced", pid)
                    sent = 0
                    profile_failed = True
                count += sent
                self.active_dumps[profile_tid]["current"] = count
                if batch and not profile_failed:
                    self.profiles[pid]["last_processed_id"] = batch[-1].id
                    self._profiles_save()
            self.profiles[pid]["last_used"] = time.time()
            self._profiles_save()
            if cid:
                if profile_failed:
                    try:
                        await self._inline_edit(call, 
                            self.strings["profiles_run_stopped"].format(num=num, count=count),
                            reply_markup=[[{"text": self.strings["btn_back"], "callback": self._profile_detail, "args": [num, cid]}]],
                        )
                    except Exception:
                        await self.client.send_message(cid, self.strings["profiles_run_stopped"].format(num=num, count=count))
                else:
                    task_data = self.active_dumps.get(profile_tid, {})
                    duration_seconds = time.time() - start_time
                    active_seconds = duration_seconds - task_data.get("flood_total_seconds", 0)
                    if active_seconds <= 0:
                        active_seconds = 1
                    avg_speed = round((count / active_seconds) * 60, 1)
                    done_msg = self.strings["copy_done_detailed"].format(
                        src=utils.escape_html(str(src_title)),
                        dest=utils.escape_html(str(dst_title)),
                        no_auth="Да" if prof.get("no_author", True) else "Нет",
                        no_capt="Да" if prof.get("no_captions", False) else "Нет",
                        start_id=start_id_str,
                        mode=mode_str,
                        filter_type=filter_name,
                        count=count,
                        duration=self._format_duration(duration_seconds),
                        avg_speed=avg_speed,
                        flood_info=self._format_flood_stats(task_data),
                    )
                    try:
                        await self._inline_edit(call, 
                            done_msg,
                            reply_markup=[[{"text": self.strings["btn_back"], "callback": self._profile_detail, "args": [num, cid]}]],
                        )
                    except Exception:
                        await self.client.send_message(cid, done_msg)
        except Exception as e:
            logger.error(f"Profile run error: {e}", exc_info=True)
            if cid:
                await self.client.send_message(cid, self.strings["profiles_run_stopped"].format(num=num, count=count))
        finally:
            self.active_dumps.pop(profile_tid, None)

    async def _profile_delete(self, call, num, cid=0):
        """Удаляет профиль."""
        pid, prof = self._profile_by_num(num)
        if not pid:
            await call.answer(self.strings["profiles_not_found"].format(num=num))
            return
        del self.profiles[pid]
        self._profiles_save()
        await call.answer(self.strings["profiles_deleted"].format(num=num))
        await self._panel_profiles(call, cid)

    async def _profile_reset(self, call, num, cid=0):
        """Сбрасывает last_processed_id профиля."""
        pid, prof = self._profile_by_num(num)
        if not pid:
            await call.answer(self.strings["profiles_not_found"].format(num=num))
            return
        start_id = int(self.profiles[pid].get("start_id", 0) or 0)
        self.profiles[pid]["last_processed_id"] = start_id - 1 if start_id > 0 else 0
        self._profiles_save()
        await call.answer(self.strings["profiles_reset"].format(num=num))
        await self._panel_profiles(call, cid)

    def _profiles_get_wizard_state(self, cid):
        for key in self._chat_id_variants(cid):
            ws = self._wizard_state.get(str(key))
            if ws:
                return ws
        return None

    def _profiles_ensure_wizard_defaults(self, ws):
        ws.setdefault("filter_type", FILTER_ALL)
        ws.setdefault("no_author", True)
        ws.setdefault("no_captions", False)
        ws.setdefault("ignored_topics", [])
        ws.setdefault("start_id", 0)
        ws.setdefault("detected_start_id", 0)
        ws.setdefault("src_topic_id", 0)
        ws.setdefault("dest_topic_id", 0)
        ws.setdefault("final_id", 0)

    async def _profiles_show_wizard_step(self, call, ws):
        ws["call"] = call
        text, btns = self._profiles_step_view(ws)
        await self._inline_edit(call, text, reply_markup=btns)

    async def _profiles_wizard_goto(self, call, step, cid=0):
        if not cid:
            cid = self._call_chat_id(call) or self._last_panel_cid or 0
        ws = self._profiles_get_wizard_state(cid)
        if not ws:
            await call.answer("Сессия истекла.")
            return
        if step in ("dst", "start", "flags") and not ws.get("src_id"):
            await call.answer("Сначала укажи источник.")
            step = "src"
        elif step in ("start", "flags") and not ws.get("dest_id"):
            await call.answer("Сначала укажи назначение.")
            step = "dst"
        if step == "flags":
            self._profiles_ensure_wizard_defaults(ws)
        ws["step"] = step
        await self._profiles_show_wizard_step(call, ws)

    async def _profiles_start_set(self, call, mode, cid=0):
        if not cid:
            cid = self._call_chat_id(call) or self._last_panel_cid or 0
        ws = self._profiles_get_wizard_state(cid)
        if not ws:
            await call.answer("Сессия истекла.")
            return
        if mode == "detected":
            ws["start_id"] = int(ws.get("detected_start_id", 0) or 0)
        else:
            ws["start_id"] = 0
        self._profiles_ensure_wizard_defaults(ws)
        ws["step"] = "flags"
        await self._profiles_show_wizard_step(call, ws)

    async def _profiles_create_start(self, call, cid=0):
        """Начинает wizard создания профиля."""
        if not cid:
            cid = self._call_chat_id(call) or self._last_panel_cid or 0
        if not cid:
            await call.answer("Ошибка: не удалось определить чат.")
            return
        self._last_panel_cid = cid
        ckey = str(cid)
        self._wizard_state[ckey] = {"step": "src", "cid": cid, "call": call}
        await self._profiles_show_wizard_step(call, self._wizard_state[ckey])

    async def _wizard_handler(self, message, ws, cid, wkey=None):
        """Обрабатывает сообщения пользователя во время wizard'а."""
        text = (message.text or "").strip()
        if not text:
            return False
        if text.startswith("."):
            return False
        step = ws.get("step")
        if str(step).startswith("profile_range_"):
            return await self._profile_range_apply(message, ws, cid, text)
        if step == "src":
            entity, info = await self._safe_resolve_profile_input(text, "src")
            if not entity:
                await utils.answer(message, self.strings["profiles_wizard_bad_entity"])
                return True
            ws["src_id"] = self._get_normalized_id(entity)
            ws["src_name"] = getattr(entity, "title", text)
            ws["src_topic_id"] = int(info.get("src_topic_id", 0) or 0)
            ws["detected_start_id"] = int(info.get("start_id", 0) or 0)
            ws["start_id"] = int(info.get("start_id", ws.get("start_id", 0)) or 0)
            ws["step"] = "dst"
            prompt, buttons = self._profiles_step_view(ws)
            edited = await self._edit_wizard_panel(ws, prompt, buttons)
            if not edited:
                await utils.answer(message, prompt, reply_markup=buttons)
            else:
                try:
                    await message.delete()
                except Exception:
                    pass
            return True
        elif step == "dst":
            entity2, info = await self._safe_resolve_profile_input(text, "dst")
            if not entity2:
                await utils.answer(message, self.strings["profiles_wizard_bad_entity"])
                return True
            ws["dest_id"] = self._get_normalized_id(entity2)
            ws["dest_name"] = getattr(entity2, "title", text)
            ws["dest_topic_id"] = int(info.get("dest_topic_id", 0) or 0)
            self._profiles_ensure_wizard_defaults(ws)
            ws["step"] = "start"
            prompt, buttons = self._profiles_step_view(ws)
            edited = await self._edit_wizard_panel(ws, prompt, buttons)
            if not edited:
                await utils.answer(message, prompt, reply_markup=buttons)
            else:
                try:
                    await message.delete()
                except Exception:
                    pass
            return True
        elif step == "start":
            start_id = await self._profile_start_from_text(text)
            if start_id is None:
                await utils.answer(message, "❌ Отправь ID сообщения числом, ссылку на сообщение или нажми «С начала».")
                return True
            ws["start_id"] = start_id
            self._profiles_ensure_wizard_defaults(ws)
            ws["step"] = "flags"
            ftxt, btns = self._profiles_flags_view(ws)
            edited = await self._edit_wizard_panel(ws, ftxt, btns)
            if not edited:
                await utils.answer(message, ftxt, reply_markup=btns)
            else:
                try:
                    await message.delete()
                except Exception:
                    pass
            return True
        return False

    async def _profiles_flags_toggle(self, call, what, cid=0):
        if not cid:
            cid = self._call_chat_id(call) or self._last_panel_cid or 0
        ws = None
        for key in self._chat_id_variants(cid):
            ws = self._wizard_state.get(str(key))
            if ws:
                break
        if not ws:
            await call.answer("Сессия истекла.")
            return
        cid = ws.get("cid", cid)
        if what == "filter":
            order = [FILTER_ALL, FILTER_MEDIA, FILTER_PHOTO_VIDEO, FILTER_DOCS, FILTER_TEXT]
            cur = ws.get("filter_type", FILTER_ALL)
            nxt = order[(order.index(cur) + 1) % len(order)]
            ws["filter_type"] = nxt
        elif what == "auth":
            ws["no_author"] = not ws.get("no_author", True)
        elif what == "capt":
            ws["no_captions"] = not ws.get("no_captions", False)
        text, btns = self._profiles_flags_view(ws)
        await self._inline_edit(call, text, reply_markup=btns)

    async def _profiles_flags_save(self, call, cid=0):
        """Сохраняет профиль — финальный шаг."""
        if not cid:
            cid = self._call_chat_id(call) or self._last_panel_cid or 0
        ws = None
        for key in self._chat_id_variants(cid):
            ws = self._wizard_state.pop(str(key), None)
            if ws:
                break
        if not ws:
            await call.answer("Сессия истекла.")
            return
        cid = ws.get("cid", cid)
        self._profiles_ensure_wizard_defaults(ws)
        start_id = int(ws.get("start_id", 0) or 0)
        final_id = int(ws.get("final_id", 0) or 0)
        if final_id > 0 and start_id > final_id:
            final_id = 0
        edit_pid = ws.get("edit_pid")
        edit_num = ws.get("edit_num")
        existing_edit = edit_pid in self.profiles
        pid = edit_pid if existing_edit else f"prof_{int(time.time())}_{cid}"
        old_profile = self.profiles.get(pid, {})
        should_reset_progress = (
            not existing_edit
            or str(old_profile.get("src_id")) != str(ws.get("src_id"))
            or int(old_profile.get("src_topic_id", 0) or 0) != int(ws.get("src_topic_id", 0) or 0)
            or int(old_profile.get("start_id", 0) or 0) != start_id
        )
        last_processed_id = (
            start_id - 1 if start_id > 0 else 0
        ) if should_reset_progress else int(old_profile.get("last_processed_id", 0) or 0)
        profile_data = {
            "src_id": ws["src_id"],
            "src_name": ws["src_name"],
            "src_topic_id": int(ws.get("src_topic_id", 0) or 0),
            "dest_id": ws["dest_id"],
            "dest_name": ws["dest_name"],
            "dest_topic_id": int(ws.get("dest_topic_id", 0) or 0),
            "no_author": ws.get("no_author", True),
            "no_captions": ws.get("no_captions", False),
            "filter_type": ws.get("filter_type", FILTER_ALL),
            "ignored_topics": ws.get("ignored_topics", []),
            "start_id": start_id,
            "final_id": final_id,
            "last_processed_id": last_processed_id,
            "created_at": old_profile.get("created_at", time.time()),
        }
        if old_profile.get("last_used"):
            profile_data["last_used"] = old_profile.get("last_used")
        self.profiles[pid] = profile_data
        self._profiles_save()
        num = edit_num if existing_edit else len(self.profiles)
        flags = self._profiles_flag_icons(self.profiles[pid])
        text_key = "profiles_updated" if existing_edit else "profiles_created"
        back_cb = self._profile_detail if existing_edit else self._panel_profiles
        back_args = [num, cid] if existing_edit else [cid]
        await self._inline_edit(call, 
            self.strings[text_key].format(
                num=num,
                src=utils.escape_html(ws["src_name"]),
                dst=utils.escape_html(ws["dest_name"]),
                start=self._profile_start_display(start_id),
                end=self._profile_end_display(final_id),
                dest_topic=self._profile_topic_display(ws.get("dest_topic_id", 0)),
                flags=flags,
            ),
            reply_markup=[[{"text": "📋 К профилю" if existing_edit else "📋 К профилям", "callback": back_cb, "args": back_args}]]
        )

    async def _profiles_wizard_cancel(self, call, cid=0):
        """Отмена wizard'а."""
        if not cid:
            cid = self._call_chat_id(call) or self._last_panel_cid or 0
        for key in self._chat_id_variants(cid):
            self._wizard_state.pop(str(key), None)
        await self._inline_edit(call, 
            self.strings["profiles_wizard_cancelled"],
            reply_markup=[[{"text": self.strings["btn_back"], "callback": self._panel_profiles, "args": [cid]}]]
        )

    async def _stop_watch(self, call, cid): # стопаем ватчер тута
        if cid in self.watchlist:
            if cid in self.watcher_buffer:
                self.watcher_buffer[cid] = []
            if cid in self.watcher_flush_tasks:
                self.watcher_flush_tasks[cid].cancel()
                del self.watcher_flush_tasks[cid]
            del self.watchlist[cid]
            self.db.set("ChatCopy", "watchlist", self.watchlist)
            await call.answer("Удалено из слежки.")
            await self._panel_watching(call)

    @loader.command()
    async def ccclear(self, message: Message):
        """Очистить кэш маппинга топиков. Использование: .ccclear topics"""
        args = utils.get_args_raw(message).strip().lower()
        if args == "topics":
            self.topic_mapping = {}
            self.topic_info_cache = {}
            self.db.set("ChatCopy", "topic_mapping", {})
            await utils.answer(message, "🗑 <b>Кэш топиков очищен</b>")
        else:
            await utils.answer(message, "❌ Укажите что очистить: <code>.ccclear topics</code>")
