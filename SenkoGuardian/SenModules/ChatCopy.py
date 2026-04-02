#  This file is part of SenkoGuardianModules
#  Copyright (c) 2025-2026 Senko
#  This software is released under the MIT License.
#  https://opensource.org/licenses/MIT

# scope heroku_min: 2.0.0
# meta banner: https://raw.githubusercontent.com/SenkoGuardian/SenkoGuardian.github.io/main/OfficialSenkoGuardianBanner.png
# meta pic: https://raw.githubusercontent.com/SenkoGuardian/SenkoGuardian.github.io/main/OfficialSenkoGuardianBanner.png

__version__ = ("1", "3", "0") # в этот раз комменты свои добавил что бы было понятно кратко, что да как и где что работает.

"""￣へ￣"""

# meta developer: @SenkoGuardianModules (from VIP section)

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
from datetime import datetime, timedelta, timezone
MSK = timezone(timedelta(hours=3), name="MSK")
from telethon import functions, errors, types
from telethon.tl.types import Message, Channel
from .. import loader, utils

logger = logging.getLogger(__name__)

_cc_client = None
_cc_log_channel = None
_cc_log_topic_id = None

class _CCTopicHandler(logging.Handler):

    def emit(self, record):
        if _cc_client is None or _cc_log_channel is None or _cc_log_topic_id is None:
            return
        try:
            text = f"<code>[{record.levelname}]</code> {self.format(record)}"
            asyncio.ensure_future(
                _cc_client.send_message(
                    int(f"-100{_cc_log_channel}"),
                    text,
                    parse_mode="html",
                    reply_to=_cc_log_topic_id,
                )
            )
        except Exception:
            pass


_cc_topic_handler = _CCTopicHandler()
_cc_topic_handler.setLevel(logging.INFO)  # INFO чтобы видеть прогресс пересылки
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
        "copy_start_prem": (
            '<emoji document_id=5372917041193828849>🚀</emoji><b> ChatCopy: Запуск копирования</b>\n\n'
            "<b>Источник:</b> {src}\n"
            '<emoji document_id=5116204921766544244>⏬</emoji><emoji document_id=5116204921766544244>⏬</emoji><emoji document_id=5116204921766544244>⏬</emoji><emoji document_id=5116204921766544244>⏬</emoji>\n'
            "<b>Цель:</b> {dest}\n\n"
            '<emoji document_id=5258096772776991776>⚙️</emoji> <b>Режим:</b> {mode}\n'
            '<emoji document_id=5226513232549664618>🔢</emoji> <b>Старт с ID:</b> {start_id}\n'
            '<emoji document_id=6035191085452497972>👤</emoji> <b>Без автора:</b> {no_auth}\n'
            '<emoji document_id=6028504027531055196>💬</emoji> <b>Без подписей:</b> {no_capt}\n'
            '📎 <b>Фильтр:</b> {filter_type}\n'
            '📦 <b>Всего сообщений:</b> {total_msgs}\n'
            '⏱ <b>Оценка времени:</b> {estimated_time}\n\n'
            "<i>Задача добавлена в очередь. Позиция: {position}</i>"
        ),
        "copy_start_no_prem": (
            "🚀 <b>ChatCopy: Запуск копирования</b>\n\n"
            "<b>Источник:</b> {src}\n"
            "⏬⏬⏬⏬\n"
            "<b>Цель:</b> {dest}\n\n"
            "⚙️ <b>Режим:</b> {mode}\n"
            "🔢 <b>Старт с ID:</b> {start_id}\n"
            "👤 <b>Без автора:</b> {no_auth}\n"
            "💬 <b>Без подписей:</b> {no_capt}\n"
            "📎 <b>Фильтр:</b> {filter_type}\n"
            "📦 <b>Всего сообщений:</b> {total_msgs}\n"
            "⏱ <b>Оценка времени:</b> {estimated_time}\n\n"
            "<i>Задача добавлена в очередь. Позиция: {position}</i>"
        ),
        "copy_done_detailed_prem": (
            '<emoji document_id=5208422125924275090>✅</emoji> <b>Задача выполнена</b>\n'
            "<blockquote>{src} → {dest}\n"
            "Без автора: {no_auth}\n"
            "Без подписей: {no_capt}\n"
            "Старт с ID: {start_id}\n"
            "Режим: {mode}\n"
            "Фильтр: {filter_type}</blockquote>\n"
            '<emoji document_id=5123248930124989216>✅</emoji> <b>Перенесено сообщений: {count}</b> <emoji document_id=5123248930124989216>✅</emoji>\n'
            '⏱ <b>Длительность:</b> {duration}\n'
            '⚡ <b>Средняя скорость:</b> {avg_speed} сообщений/мин'
            "{flood_info}"
        ),
        "copy_done_detailed_no_prem": (
            "<b>Задача выполнена</b>\n"
            "<blockquote>{src} → {dest}\n"
            "Без автора: {no_auth}\n"
            "Без подписей: {no_capt}\n"
            "Старт с ID: {start_id}\n"
            "Режим: {mode}\n"
            "Фильтр: {filter_type}</blockquote>\n"
            "✔️ <b>Перенесено сообщений: {count}</b> ✔️\n"
            "⏱ <b>Длительность:</b> {duration}\n"
            "⚡ <b>Средняя скорость:</b> {avg_speed} сообщений/мин"
            "{flood_info}"
        ),
        "flood_wait_notice": (
            "⏸ <b>FloodWait</b>\n"
            "📊 <b>Задержка:</b> <code>{minutes}m {seconds}s</code>\n"
            "🕐 <b>Возобновление:</b> <code>{resume_time}</code>\n"
            "📨 <b>Переслано:</b> <code>{count}</code> сообщений\n"
            "⏳ <b>Осталось:</b> <code>{remaining}</code> сообщений\n"
            "⚡ <b>Скорость:</b> <code>{speed}</code> сообщений/мин"
        ),
        "panel_summary": "<b>📊 ChatCopy Status</b>\n\n<b>🔄 Активная:</b> {active}\n<b>⏳ В очереди:</b> {queue_len}\n<b>👀 Слежка:</b> {watching_count}\n<b>⏱ Последний FW:</b> {last_flood}",
        "panel_task_running": "{name}\n├ 📦 {count}/{total} сообщений\n├ ⚡ {speed}/мин | 📊 {progress}%\n├ ⏱ Прошло: {elapsed} | Осталось: {eta}\n└ 🕐 Начало: {start_time} | Окончание: {end_time}",
        "panel_task_paused": "{name}\n├ ⏸ На паузе (FW: {flood_time})\n├ 📦 {count}/{total} сообщений\n├ ⚡ {speed}/мин\n└ 🕐 Продолжение: {resume_time}",
        "btn_stop": "🛑 Стоп",
        "btn_pause": "⏸ Пауза",
        "btn_resume": "▶️ Продолжить",
        "btn_back": "🔙 Назад",
        "btn_tasks": "📋 Очередь задач",
        "btn_watch": "👀 Слежка",
        "btn_settings": "⚙️ Настройки",
        "btn_stats": "📊 Статистика",
        "forum_enabled": "✅ Топики включены в {chat}",
        "forum_enable_failed": "❌ Не удалось включить топики в {chat}. Нужны права администратора.",
        "forum_not_channel": "❌ {chat} не является каналом/группой",
        "err_ent": "❌ Ошибка: Чат не найден или нет доступа.",
        "args_err": "❌ Синтаксис: .chatcopy <src> <dest>[start_id:final_id] [-n] [-dmc] [--now] [--media|--photo_video|--docs|--text]",
        "watch_added": "<b>👀 Наблюдение активировано</b>\nID: <code>{src_id}</code>\n{src} -> {dest}\nРежим топиков: {topics}\nБез подписей: {no_capt}\nФильтр: {filter_type}",
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
        "task_item_compact_error": "❌{num}. <b>{src}</b> → <b>{dest}</b>",
        "task_detail_running": "<b>▶️ Задача #{num}</b>\n\n<b>{src}</b> → <b>{dest}</b>\n├ Статус: <code>Выполняется</code>\n├ Прогресс: <code>{current}/{total}</code> ({progress}%)\n├ Скорость: <code>{speed}/мин</code>\n├ Прошло: <code>{elapsed}</code>\n├ Осталось: <code>{eta_left}</code>\n├ Начато: <code>{start_time}</code>\n├ Окончание: <code>{end_time}</code>\n└ Позиция: <code>{position}</code>",
        "task_detail_queued": "<b>⏳ Задача #{num}</b>\n\n<b>{src}</b> → <b>{dest}</b>\n├ Статус: <code>В очереди</code>\n├ Позиция: <code>{position}</code>\n├ Сообщений: <code>~{total}</code>\n├ Ожидание старта: <code>{eta_start}</code>\n└ Примерное время работы: <code>{estimated_duration}</code>",
        "task_detail_paused": "<b>⚠️ Задача #{num}</b>\n\n<b>{src}</b> → <b>{dest}</b>\n├ Статус: <code>Пауза (FloodWait)</code>\n├ Прогресс: <code>{current}/{total}</code> ({progress}%)\n├ FloodWait'ов: <code>{flood_count}</code>\n├ Время ожидания: <code>{flood_time}</code>\n├ Продолжение: <code>{resume_time}</code>\n├ Скорость до паузы: <code>{speed}/мин</code>\n└ Осталось сообщений: <code>{remaining}</code>",
        "task_detail_completed": "<b>✅ Задача #{num}</b>\n\n<b>{src}</b> → <b>{dest}</b>\n├ Статус: <code>Завершена</code>\n├ Переслано: <code>{count}</code> сообщений\n├ Длительность: <code>{duration}</code>\n├ Средняя скорость: <code>{avg_speed}/мин</code>\n├ Завершено: <code>{end_time}</code>\n└ FloodWait'ов: <code>{floods}</code>",
        "task_detail_error": "<b>❌ Задача #{num}</b>\n\n<b>{src}</b> → <b>{dest}</b>\n├ Статус: <code>Ошибка</code>\n└ Попробуйте перезапустить",
        "no_tasks": "<i>Нет активных задач</i>",
        "preparing_prem": "<emoji document_id=5208722554591659638>💫</emoji> <b>Подготовка к копированию. Подсчитываем (да, вручную!) кол-во медиа, это может занять время...</b>",
        "preparing_no_prem": "⌛️ <b>Подготовка к копированию. Подсчитываем кол-во медиа, это может занять время...</b>",
    }

    def __init__(self):
        self._tasks = []
        self.config = loader.ModuleConfig(
            loader.ConfigValue("batch_size", 100, lambda: self.strings["cfg_batch"], validator=loader.validators.Integer(minimum=1, maximum=100)),
            loader.ConfigValue("delay", 10, lambda: self.strings["cfg_delay"], validator=loader.validators.Integer(minimum=1)),
            loader.ConfigValue("flood_buffer", 5, lambda: self.strings["cfg_flood_buffer"], validator=loader.validators.Integer(minimum=0, maximum=60)),
        )
        self.queue = asyncio.Queue()
        self.dump_queue = asyncio.Queue()
        self.watcher_buffer = {}
        self.watcher_flush_tasks = {}
        self.watchlist = {}
        self.active_dumps = {}
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
        self._task_counter = 0

    async def client_ready(self, client, db):
        global _cc_client, _cc_log_channel, _cc_log_topic_id
        self.client = client
        self.db = db
        self.watchlist = self.db.get("ChatCopy", "watchlist", {})
        self.last_processed_ids = self.db.get("ChatCopy", "last_processed_ids", {})
        self.topic_mapping = self.db.get("ChatCopy", "topic_mapping", {})
        self.task_stats = self.db.get("ChatCopy", "task_stats", {})
        self.task_queue = self.db.get("ChatCopy", "persistent_queue", [])
        for task in self.task_queue:
            task['status'] = 'queued'
        me = await client.get_me()
        self.is_premium = getattr(me, 'premium', False)
        try:
            asset_channel = self._db.get("heroku.forums", "channel_id", 0)
            if asset_channel:
                notif_topic = await utils.asset_forum_topic(
                    self._client,
                    self._db,
                    asset_channel,
                    "ChatCopy Logs",
                    description="ChatCopy module activity logs (warnings & errors).",
                    icon_emoji_id=5372917041193828849,
                )
                _cc_client = self._client
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
                })
            except Exception as e:
                logger.error(f"Не удалось возобновить задачу {task.get('tid')}: {e}")

    async def _resolve_arg(self, arg):  # все виды (ну почти) ссылок как дадут id и прочее, 
                                        # работает если копировать сообщение в топике и в аргумент типа куда отправлять вставить.
        extra = {}
        entity = None
        arg = str(arg).strip()
        regex = r"(?:t\.me/|tg://resolve\?domain=|tg://openmessage\?user_id=)(?:c/)?([\w\d_]+)(?:/(\d+))?(?:/(\d+))?"
        match = re.search(regex, arg)
        if match:
            identifier = match.group(1)
            if match.group(2): extra['topic'] = int(match.group(2))
            if match.group(3): extra['msg'] = int(match.group(3))
            if identifier.isdigit():
                for potential_id in [int(identifier), int(f"-100{identifier}")]:
                    try:
                        entity = await self.client.get_entity(potential_id)
                        if entity: break
                    except: continue
            else:
                try: entity = await self.client.get_entity(identifier)
                except: pass
        else:
            try:
                if arg.lstrip("-").isdigit(): entity = await self.client.get_entity(int(arg))
                else: entity = await self.client.get_entity(arg)
            except: pass
        return entity, extra

    def _get_normalized_id(self, entity): # что бы получать норм айди а не нечто, что бы копировка шла хорошо.
        if not entity:
            return "0"
        try:
            return str(utils.get_chat_id(entity))
        except Exception:
            if hasattr(entity, 'id') and entity.id:
                eid = str(entity.id)
                if not eid.startswith("-100") and len(eid) > 9: 
                     return f"-100{eid}"
                if not eid.startswith("-"):
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
                result = await self.client(functions.messages.GetForumTopicsRequest(peer=chat_entity, offset_date=0, offset_id=0, offset_topic=0, limit=100))
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
                    topics_result = await self.client(functions.messages.GetForumTopicsRequest(peer=dest_entity, offset_date=0, offset_id=0, offset_topic=0, limit=20))
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
        try:
            offset_date = 0
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
    task_id, total_msgs=0, speed=0): # ниже этой функции, функция обработки флудвейта, он просто отправляет примерное время когда продолжит работать.
        minutes = seconds // 60
        secs = seconds % 60
        resume_time = (datetime.now(MSK) + timedelta(seconds=seconds + self.config["flood_buffer"])).strftime("%H:%M:%S")
        remaining = max(0, total_msgs - count)
        self.last_flood_info = {
            "time": datetime.now(MSK).strftime("%H:%M:%S"),
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
                    speed=round(speed, 1)
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
    src_entity=None, filter_type=FILTER_ALL, status_msg=None, tid=None): 
        if not messages: 
            return 0
        if tid and tid in self.active_dumps:
            await self.active_dumps[tid].get("cancel", asyncio.Event()).wait()
            if self.active_dumps[tid].get("status") == "stopped":
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
                if hasattr(msg, 'reply_to') and msg.reply_to:
                    src_topic_id = getattr(msg.reply_to, 'reply_to_top_id', None) or getattr(msg.reply_to, 'reply_to_msg_id', None)
                if not src_topic_id and hasattr(msg, 'topic_id') and msg.topic_id:
                    src_topic_id = msg.topic_id
            key = src_topic_id if src_topic_id else "no_topic"
            msg_groups.setdefault(key, []).append(msg)
        total_sent = 0
        delay = self.config["delay"]
        if not isinstance(delay, int):
            delay = 10
        for src_topic_id, msgs in msg_groups.items():
            if tid and tid in self.active_dumps:
                await self.active_dumps[tid].get("cancel", asyncio.Event()).wait()
                if self.active_dumps[tid].get("status") == "stopped":
                    break
            target_topic = fixed_dest_topic
            if map_topics and src_topic_id != "no_topic":
                target_topic = await self._ensure_topic_mapping(src_entity, dest_entity, src_topic_id)
                if not target_topic:
                    continue
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
            await asyncio.sleep(delay)
        return total_sent

    async def worker(self): # воркер для Watcher'а
        while True:
            item = await self.queue.get()
            try:
                watch_cid = item.get("watch_cid")
                if watch_cid and watch_cid not in self.watchlist:
                    logger.debug(f"Игнорируем сообщение для {watch_cid}, слежка была остановлена")
                    continue
                result = await self._process_batch(**item)
                if watch_cid and item.get("messages"):
                    last_msg = item["messages"][-1]
                    self.last_processed_ids[watch_cid] = last_msg.id
                    self.db.set("ChatCopy", "last_processed_ids", self.last_processed_ids)
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
            async with self._queue_lock:
                self.is_processing_queue = True
                self.current_dump_task = tid
                self._update_queue_positions()
                if tid in self.task_queue:
                    idx = next((i for i, t in enumerate(self.task_queue) if t['tid'] == tid), None)
                    if idx is not None:
                        self.task_queue[idx]['status'] = 'running'
                        self.task_queue[idx]['start_time'] = datetime.now(MSK)
                        self.current_task_index = idx
                if tid:
                    self.active_dumps[tid] = {
                        "current": 0,
                        "cancel": asyncio.Event(),
                        "name": task_data.get('src_name', 'Unknown'),
                        "status": "running",
                        "start_time": time.time(),
                        "flood_count": 0,
                        "flood_total_seconds": 0,
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
                update_task = asyncio.create_task(self._auto_update_status(tid, task_data.get('status_msg')))
                try:
                    logger.info("[%s] Задача запущена: %s → %s | Всего: %d сообщений",
                               tid, task_data.get('src_name', '?'),
                               getattr(task_data.get('dest'), 'title', '?'),
                               task_data.get('total_msgs', 0))
                    await self._history_dumper(**task_data)
                except Exception as e:
                    logger.error(f"Dump Worker Error: {e}")
                    if tid and tid in self.active_dumps:
                        self.active_dumps[tid]["status"] = "error"
                finally:
                    update_task.cancel()
                    if tid in self.active_dumps:
                        completed_task = self.active_dumps[tid].copy()
                        completed_task['tid'] = tid
                        completed_task['end_time'] = datetime.now(MSK)
                        self.task_history.append(completed_task)
                        self.task_queue = [t for t in self.task_queue if t['tid'] != tid]
                        duration = time.time() - completed_task.get('start_time', time.time())
                        active_duration = duration - completed_task.get('flood_total_seconds', 0)
                        if active_duration <= 0: active_duration = 1
                        avg_spd = (completed_task.get('current', 0) / active_duration) * 60
                        self.task_stats[tid] = {
                            'completed_at': time.time() if completed_task.get('status') == 'completed' else None,
                            'flood_count': completed_task.get('flood_count', 0),
                            'flood_time': completed_task.get('flood_total_seconds', 0),
                            'avg_speed': avg_spd
                        }
                        self.db.set("ChatCopy", "task_stats", self.task_stats)
                    logger.info("[%s] Задача завершена. Переслано: %d",
                               tid, self.active_dumps.get(tid, {}).get('current', 0))
                    self.current_dump_task = None
                    self.is_processing_queue = False
                    self.dump_queue.task_done()
                    if tid and tid in self.task_history:
                        last_task = next((t for t in reversed(self.task_history) if t.get('tid') == tid), None)
                        if last_task and last_task.get('flood_count', 0) > 0:
                            final_wait = min(60 * last_task['flood_count'], 300)
                            logger.info(f"Финальная задержка после задачи с FloodWait'ами: {final_wait}с")
                            await asyncio.sleep(final_wait)
                            self._save_tasks()

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
        """Улучшенный sender с умной обработкой FloodWait"""
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
            return True
        except errors.FloodWaitError as e:
            wait_time = e.seconds if e.seconds is not None else 60
            if tid and tid in self.active_dumps:
                task = self.active_dumps[tid]
                task["consecutive_floods"] = task.get("consecutive_floods", 0) + 1
                task["flood_count"] = task.get("flood_count", 0) + 1
                task["flood_total_seconds"] = task.get("flood_total_seconds", 0) + wait_time
                task["current_flood_wait"] = wait_time
                task["status"] = "paused"
                task["flood_wait_until"] = time.time() + wait_time + self.config["flood_buffer"]
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
            logger.error(f"[{tid}] Send Error: {e}")
            return False

    def _parse_filter(self, args): # все аргументы нужные цепляет
        filter_type = FILTER_ALL
        args_list = list(args)
        for arg in args_list:
            if arg == "--media":
                filter_type = FILTER_MEDIA
                if arg in args: args.remove(arg)
            elif arg == "--photo_video":
                filter_type = FILTER_PHOTO_VIDEO
                if arg in args: args.remove(arg)
            elif arg == "--docs":
                filter_type = FILTER_DOCS
                if arg in args: args.remove(arg)
            elif arg == "--text":
                filter_type = FILTER_TEXT
                if arg in args: args.remove(arg)
        return filter_type, args

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

    @loader.command()
    async def chatcopy(self, message: Message):
        """<src> <dest> [start_id:final_id] [-n] [-dmc] [--now] [--media|--photo_video|--docs|--text] — Добавить задачу в очередь. --now: начать сразу, без полного подсчёта."""
        args_raw = utils.get_args_raw(message).split()
        no_author = "-n" in args_raw
        no_captions = "-dmc" in args_raw
        start_now = "--now" in args_raw
        if start_now:
            args_raw.remove("--now")
        filter_type, args_raw = self._parse_filter(args_raw)
        clean_args = [x for x in args_raw if x not in ["-n", "-dmc"]]
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
        dest, dest_map = await self._resolve_arg(clean_args[1])
        if not src or not dest:
            return await utils.answer(message, self.strings["err_ent"])
        self._task_counter += 1
        tid = f"{src.id}_{dest.id}_{self._task_counter}_{int(time.time())}"
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
        prep_key = "preparing_prem" if self.is_premium else "preparing_no_prem"
        status_msg = await utils.answer(message, self.strings[prep_key])
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
                'tid': tid, 'src': src_name, 'dest': dest_name, 'src_id': src.id, 'dest_id': dest.id,
                'status': 'queued', 'position': queue_position, 'added_time': datetime.now(MSK).isoformat(),
                'no_author': no_author, 'no_captions': no_captions, 'filter_type': filter_type,
                'start_id': start_id, 'final_id': final_id, 'total_msgs': total_msgs if total_msgs > -1 else 0,
                'current': 0, 'last_processed_id': start_id,
                'status_msg_id': status_msg.id, 'status_chat_id': status_msg.chat_id,
                'map_t': src_is_forum, 'f_src_t': src_map.get('topic'), 'f_dest_t': dest_map.get('topic'),
                'start_now': start_now,
            }
            self.task_queue.append(task_info)
            self._save_tasks()
        filter_name = self._get_filter_name(filter_type)
        start_string_key = "copy_start_prem" if self.is_premium else "copy_start_no_prem"
        await status_msg.edit(self.strings[start_string_key].format(
            src=utils.escape_html(src_name), dest=utils.escape_html(dest_name),
            mode=mode_str, start_id=start_id_str, no_auth=no_auth_str,
            no_capt=no_capt_str, filter_type=filter_name,
            total_msgs=total_msgs if total_msgs > -1 else "∞ (ошибка подсчета)",
            estimated_time=estimated_duration, position=queue_position
        ))
        await self.dump_queue.put({
            "status_msg": status_msg, "src": src, "dest": dest,
            "no_auth": no_author, "no_captions": no_captions,
            "map_t": src_is_forum, "f_src_t": src_map.get('topic'), "f_dest_t": dest_map.get('topic'),
            "tid": tid, "min_id": start_id, "max_id": final_id,
            "mode_str": mode_str, "no_auth_str": no_auth_str, "no_capt_str": no_capt_str,
            "start_id_str": start_id_str, "filter_type": filter_name, "filter_name": filter_name,
            "src_name": src_name, "queue_position": queue_position, "total_msgs": total_msgs if total_msgs > -1 else 0,
            "restored_count": 0,
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
        """<src> <dest> [start_id:final_id] [-n] [-dmc][--media|--photo_video|--docs|--text] — Наблюдение за чатом"""
        args = utils.get_args_raw(message).split()
        no_author = "-n" in args
        no_captions = "-dmc" in args
        filter_type, args = self._parse_filter(args)
        clean_args = [x for x in args if x not in ["-n", "-t", "-dmc"]]
        if len(clean_args) < 2: 
            return await utils.answer(message, self.strings["args_err"])
        start_id = 0
        final_id = 0
        if len(clean_args) >= 3:
            id_arg = clean_args[2]
            if ":" in id_arg:
                parts = id_arg.split(":")
                if parts[0].isdigit(): start_id = int(parts[0])
                if len(parts) > 1 and parts[1].isdigit(): final_id = int(parts[1])
            elif id_arg.isdigit():
                start_id = int(id_arg)
        src, src_map = await self._resolve_arg(clean_args[0])
        dest, dest_map = await self._resolve_arg(clean_args[1])
        if not src or not dest: 
            return await utils.answer(message, self.strings["err_ent"])
        src_is_forum = self._is_forum(src)
        dest_is_forum = self._is_forum(dest)
        if src_is_forum and not dest_is_forum:
            forum_result = await self._ensure_forum_enabled(dest)
            if forum_result:
                await utils.answer(message, self.strings["forum_enabled"].format(chat=utils.escape_html(getattr(dest, 'title', dest.id))))
                dest = await self.client.get_entity(dest.id)
            else:
                return await utils.answer(message, self.strings["forum_enable_failed"].format(chat=utils.escape_html(getattr(dest, 'title', dest.id))))
        is_restricted = False
        try:
            async for test_m in self.client.iter_messages(src, limit=1):
                if test_m.noforwards:
                    is_restricted = True
                break
        except Exception:
            pass
        if is_restricted:
            return await utils.answer(message, "❌ Ошибка: канал в режиме запрета копирования") # ну как бы, учитываем да
        src_t = src_map.get('topic')
        dest_t = dest_map.get('topic')
        map_topics = src_is_forum
        cid = self._get_normalized_id(src)
        try: 
            dest_id = utils.get_chat_id(dest)
        except: 
            dest_id = dest.id
        if start_id > 0:
            self.last_processed_ids[cid] = start_id - 1
        elif cid not in self.last_processed_ids:
            self.last_processed_ids[cid] = 0
        self.watchlist[cid] = {
            "dest": dest_id, "no_author": no_author, "no_captions": no_captions, "map_topics": map_topics,
            "fixed_src_topic": src_t, "fixed_dest_topic": dest_t, "src_entity_id": src.id, "dest_entity_id": dest.id,
            "filter_type": filter_type, "final_id": final_id
        }
        self.db.set("ChatCopy", "watchlist", self.watchlist)
        self.db.set("ChatCopy", "last_processed_ids", self.last_processed_ids)
        filter_name = self._get_filter_name(filter_type)
        msg_text = self.strings["watch_added"].format(
            src=getattr(src, 'title', src.id), src_id=cid, dest=getattr(dest, 'title', dest.id),
            topics="🗂️ ВКЛ (Auto-mapping)" if map_topics else "ВЫКЛ", no_capt="Да" if no_captions else "Нет", filter_type=filter_name
        )
        if start_id > 0 or final_id > 0:
            range_str = "Все новые"
            if start_id > 0 and final_id > 0: range_str = f"с {start_id} по {final_id}"
            elif start_id > 0: range_str = f"с {start_id}"
            elif final_id > 0: range_str = f"до {final_id}"
            msg_text += f"\nДиапазон ID: {range_str}"
        await utils.answer(message, msg_text)

    async def _history_dumper(self, status_msg, src, dest, no_auth, no_captions, 
                                map_t, f_src_t, f_dest_t, tid, min_id=0, max_id=0,
                                filter_type=FILTER_ALL, filter_name="", restored_count=0, **kwargs):
        if tid in self.active_dumps:
            self.active_dumps[tid]["status"] = "running"
        task = next((t for t in self.task_queue if t['tid'] == tid), None)
        if not task:
            logger.error(f"Задача {tid} не найдена в очереди для дампа.")
            return
        count = task.get('current', 0) or restored_count
        if tid in self.active_dumps and count > 0:
            self.active_dumps[tid]["current"] = count
        start_from_id = task.get('last_processed_id', min_id)
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
        batch = []
        dumper_kwargs = {"reverse": True}
        if f_src_t: dumper_kwargs["reply_to"] = f_src_t
        if start_from_id > 0: dumper_kwargs["min_id"] = start_from_id - 1
        if max_id > 0: dumper_kwargs["max_id"] = max_id + 1
        delay = self.config["delay"]
        try:
            async for msg in self.client.iter_messages(src, **dumper_kwargs):
                if tid not in self.active_dumps or self.active_dumps[tid].get("status") == "stopped": break
                await self.active_dumps[tid].get("cancel", asyncio.Event()).wait()
                if tid not in self.active_dumps or self.active_dumps[tid].get("status") == "stopped": break
                if isinstance(msg, types.MessageService) or not self._should_include_message(msg, filter_type): continue
                batch.append(msg)
                if len(batch) >= self._get_effective_batch_size():
                    processed = await self._process_batch(
                        messages=list(batch), dest_id=dest.id, no_author=no_auth, no_captions=no_captions,
                        fixed_dest_topic=f_dest_t, map_topics=map_t, dest_entity=dest, src_entity=src,
                        filter_type=filter_type, status_msg=status_msg, tid=tid
                    )
                    if tid not in self.active_dumps or self.active_dumps[tid].get("status") == "stopped": break
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
            if batch and self.active_dumps.get(tid, {}).get("status") != "stopped":
                processed = await self._process_batch(
                    messages=list(batch), dest_id=dest.id, no_author=no_auth, no_captions=no_captions,
                    fixed_dest_topic=f_dest_t, map_topics=map_t, dest_entity=dest, src_entity=src,
                    filter_type=filter_type, status_msg=status_msg, tid=tid
                )
                if tid in self.active_dumps:
                    self.active_dumps[tid]["current"] += processed
                    count = self.active_dumps[tid]["current"]
                    task['current'] = count
                    task['last_processed_id'] = batch[-1].id
            if self.active_dumps.get(tid, {}).get("status") != "stopped":
                task['status'] = 'completed'
                self.task_queue = [t for t in self.task_queue if t['tid'] != tid]
                self._save_tasks()
                task_data = self.active_dumps[tid]
                duration_seconds = time.time() - task_data.get('start_time', time.time())
                duration_str = self._format_duration(duration_seconds)
                active_seconds = duration_seconds - task_data.get('flood_total_seconds', 0)
                if active_seconds <= 0: active_seconds = 1
                avg_speed = round((count / active_seconds) * 60, 1)
                chat_id_to_report = status_msg.chat_id if status_msg and status_msg.chat_id else task.get('status_chat_id')
                done_string_key = "copy_done_detailed_prem" if self.is_premium else "copy_done_detailed_no_prem"
                done_full = self.strings[done_string_key].format(
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
            self._save_tasks()
        except Exception as e:
            logger.error(f"Dumper Error: {e}")
            await self.client.send_message(status_msg.chat_id, f"❌ Ошибка в задаче:\n{e}")

    @loader.watcher() # сам ватчер, который следит за чатами
    async def watcher(self, message: Message):
        if isinstance(message, types.MessageService): 
            return
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
            cur_t = getattr(message, 'topic_id', None) or (message.reply_to.reply_to_top_id if message.reply_to else None)
            if cur_t != cfg["fixed_src_topic"]:
                self.last_processed_ids[cid] = message.id
                self.db.set("ChatCopy", "last_processed_ids", self.last_processed_ids)
                return
        if cid not in self.watcher_buffer:
            self.watcher_buffer[cid] = []
        self.watcher_buffer[cid].append(message)
        self.last_watched[cid] = {
            "name": getattr(getattr(message, 'chat', None), "title", cid) if getattr(message, 'chat', None) else cid, 
            "time": datetime.now(MSK).strftime("%H:%M:%S")
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
                    "watch_cid": cid
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
                    "watch_cid": cid
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
                cid_int = int(cid_str)
                async for msg in self.client.iter_messages(cid_int, min_id=last_id):
                    if cfg.get("final_id", 0) > 0 and msg.id > cfg.get("final_id", 0):
                        continue
                    if not isinstance(msg, types.MessageService) and self._should_include_message(msg, filter_type): 
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
                            "filter_type": filter_type, "watch_cid": cid_str
                        })
                        await asyncio.sleep(self.config["delay"])
            except Exception as e:
                logger.debug(f"Catch-up error for {cid_str}: {e}")

    @loader.command()
    async def cchelp(self, message: Message):
        """— Подробная документация по модулю ChatCopy"""
        help_text_prem = (
            '<emoji document_id=6030550768426159669>🛡</emoji> <b>Подробная документация по модулю ChatCopy!</b>\n\n'
            '<blockquote expandable><emoji document_id=5398049016556560225>1️⃣</emoji><b> Основные команды </b>\n'
            '<emoji document_id=5314310000531766389>🛫</emoji> <code>.chatcopy &lt;откуда&gt; &lt;куда&gt;[диапазон (от:до)] [флаги (можно несколько)]</code>\n'
            '<i>Копирует старую историю чата (делает дамп). Ставит задачу в очередь в случае если другая была запущена.</i>\n'
            '<emoji document_id=5258096772776991776>⚙️</emoji> <code>--now</code> — Начать немедленно, без полного подсчёта (примерное кол-во сообщений запрашивается у Telegram мгновенно). Идеально для 110k+ медиа.\n\n'
            '<emoji document_id=6028228780256923695>👀</emoji> <code>.ccwatch &lt;откуда&gt; &lt;куда&gt; [диапазон (от:до)] [флаги (можно несколько)]</code>\n'
            '<i>Режим слежки. Модуль будет висеть в фоне и моментально пересылать все новые сообщения. Функции [от:до] аналогичны </i><code>.chatcopy</code>\n\n'
            '<emoji document_id=5355012477883004708>📺</emoji> <code>.ccpanel</code>\n'
            '<i>Открывает меню: управление задачами, пауза/стоп, статистика и настройки (скорость, задержка).</i>\n\n'
            '<emoji document_id=6028352582689231001>🗑</emoji> <code>.ccclear topics</code>\n'
            '<i>Очищает кэш топиков (полезно, если форум сломался и пересылает не в те разделы).</i></blockquote>\n\n'
            '<blockquote expandable><emoji document_id=5397653273974939567>2️⃣</emoji><b> Источники и Диапазоны([от:до] функция) (ID)</b>\n'
            '<emoji document_id=5208758520647800433>✨</emoji> <b>Чаты:</b> Можно использовать юзернеймы (@chat), ID (-100123...) или прямые ссылки на топики (<a href="t.me/c/123/45">t.me/c/123/45</a>). Модуль сам всё распознает.\n'
            '<emoji document_id=5208556360832141255>⚪️</emoji> <b>Диапазон [start:end]:</b> Пишется слитно, без пробелов.\n'
            '<emoji document_id=5208556360832141255>⚪️</emoji> <code>100:500</code> — скопировать с 100-го по 500-е сообщение.\n'
            '<emoji document_id=5208556360832141255>⚪️</emoji> <code>100:</code> — от 100-го до самых свежих.\n'
            '<emoji document_id=5208556360832141255>⚪️</emoji> <code>:500</code> — с самого начала чата и до 500-го.</blockquote>\n\n'
            '<blockquote expandable><emoji document_id=5397646938898178715>3️⃣</emoji><b> Флаги (Настройки текста)</b>\n'
            '<tg-emoji emoji-id=5208423865386026964>🆕</tg-emoji> <code>--now</code> - начать пересылку сразу без подсчитывания, но без копирования топиков и последующей пересылки в них'
            '<emoji document_id=5208809016578296327>👤</emoji> <code>-n</code> — Скрыть автора (пересылка без плашки «Переслано от...»).\n'
            '<emoji document_id=6028504027531055196>💬</emoji> <code>-dmc</code> — Удалить подпись к медиа (оставит только голую картинку или файл, удалив текст под ним)(!Работает только с[-n] флагом!).</blockquote>\n\n'
            '<blockquote expandable><emoji document_id=5397754265835938409>4️⃣</emoji><b> Фильтры контента</b>\n'
            '<i>(Указывайте только один! Если не указать ничего — скопируется всё подряд)</i>\n'
            '<emoji document_id=5208795483136348193>📌</emoji> <code>--media</code> — Любые медиа (фото, видео) и документы.\n'
            '<emoji document_id=5208443446141928861>📷</emoji> <code>--photo_video</code> — Строго только фото и видео (без гифок/стикеров).\n'
            '<emoji document_id=5208670581192411812>💼</emoji> <code>--docs</code> — Строго только документы (файлы, архивы, apk).\n'
            '<emoji document_id=6028504027531055196>💬</emoji> <code>--text</code> — Только чисто текстовые сообщения.</blockquote>\n\n'
            '<blockquote expandable><emoji document_id=5208550511086683412>💡</emoji><b> Полные примеры использования</b>\n'
            '<b>1. Полная копия канала со скрытием автора:</b>\n'
            '<emoji document_id=5296587908906511469>➡️</emoji> <code>.chatcopy @donor_channel @my_channel -n</code>\n\n'
            '<b>2. Слежка за конкретным топиком (воруем только фото/видео без подписей):</b>\n'
            '<emoji document_id=5296587908906511469>➡️</emoji> <code>.ccwatch <a href="t.me/c/123/4">t.me/c/123/4</a> <a href="t.me/c/321/5">t.me/c/321/5</a> -dmc --photo_video</code>\n\n'
            '<b>3. Скопировать историю с 5000 по 6000 сообщение, только текст:</b>\n'
            '<emoji document_id=5296587908906511469>➡️</emoji> <code>.chatcopy -100111 -100222 5000:6000 --text</code></blockquote>\n\n'
            '<emoji document_id=5307554373457440075>💎</emoji> Приятного пользования!\n'
            '<emoji document_id=5345814569195421891>❕</emoji> Единственный минус, не копирует с чатов с запрещенным копированием.'
        )

        help_text_no_prem = (
            '🛡 <b>Подробная документация по модулю ChatCopy!</b>\n\n'
            '<blockquote expandable>1️⃣<b> Основные команды </b>\n'
            '🛫 <code>.chatcopy &lt;откуда&gt; &lt;куда&gt;[диапазон (от:до)] [флаги (можно несколько)]</code>\n'
            '<i>Копирует старую историю чата (делает дамп). Ставит задачу в очередь в случае если другая была запущена.</i>\n'
            '⚙️ <code>--now</code> — Начать немедленно, без полного подсчёта (примерное кол-во запрашивается у Telegram мгновенно). Идеально для 110k+ медиа.\n\n'
            '👀 <code>.ccwatch &lt;откуда&gt; &lt;куда&gt; [диапазон (от:до)] [флаги (можно несколько)]</code>\n'
            '<i>Режим слежки. Модуль будет висеть в фоне и моментально пересылать все новые сообщения. Функции [от:до] аналогичны </i><code>.chatcopy</code>\n\n'
            '📺 <code>.ccpanel</code>\n'
            '<i>Открывает меню: управление задачами, пауза/стоп, статистика и настройки (скорость, задержка).</i>\n\n'
            '🗑 <code>.ccclear topics</code>\n'
            '<i>Очищает кэш топиков (полезно, если форум сломался и пересылает не в те разделы).</i></blockquote>\n\n'
            '<blockquote expandable>2️⃣<b> Источники и Диапазоны([от:до] функция) (ID)</b>\n'
            '✨ <b>Чаты:</b> Можно использовать юзернеймы (@chat), ID (-100123...) или прямые ссылки на топики (<a href="t.me/c/123/45">t.me/c/123/45</a>). Модуль сам всё распознает.\n'
            '⚪️ <b>Диапазон [start:end]:</b> Пишется слитно, без пробелов.\n'
            '⚪️ <code>100:500</code> — скопировать с 100-го по 500-е сообщение.\n'
            '⚪️ <code>100:</code> — от 100-го до самых свежих.\n'
            '⚪️ <code>:500</code> — с самого начала чата и до 500-го.</blockquote>\n\n'
            '<blockquote expandable>3️⃣<b> Флаги (Настройки текста)</b>\n'
            '🆕 <code>--now</code> - начать пересылку сразу без подсчитывания, но без копирования топиков и последующей пересылки в них'
            '👤 <code>-n</code> — Скрыть автора (пересылка без плашки «Переслано от...»).\n'
            '💬 <code>-dmc</code> — Удалить подпись к медиа (оставит только голую картинку или файл, удалив текст под ним)(!Работает только с [-n] флагом!).</blockquote>\n\n'
            '<blockquote expandable>4️⃣<b> Фильтры контента</b>\n'
            '<i>(Указывайте только один! Если не указать ничего — скопируется всё подряд)</i>\n'
            '📌 <code>--media</code> — Любые медиа (фото, видео) и документы.\n'
            '📷 <code>--photo_video</code> — Строго только фото и видео (без гифок/стикеров).\n'
            '💼 <code>--docs</code> — Строго только документы (файлы, архивы, apk).\n'
            '💬 <code>--text</code> — Только чисто текстовые сообщения.</blockquote>\n\n'
            '<blockquote expandable>💡<b> Полные примеры использования</b>\n'
            '<b>1. Полная копия канала со скрытием автора:</b>\n'
            '➡️ <code>.chatcopy @donor_channel @my_channel -n</code>\n\n'
            '<b>2. Слежка за конкретным топиком (воруем только фото/видео без подписей):</b>\n'
            '➡️ <code>.ccwatch <a href="t.me/c/123/4">t.me/c/123/4</a> <a href="t.me/c/321/5">t.me/c/321/5</a> -dmc --photo_video</code>\n\n'
            '<b>3. Скопировать историю с 5000 по 6000 сообщение, только текст:</b>\n'
            '➡️ <code>.chatcopy -100111 -100222 5000:6000 --text</code></blockquote>\n\n'
            '💎 Приятного пользования!\n'
            '❕ Единственный минус, не копирует с чатов с запрещенным копированием.'
        )
        final_text = help_text_prem if self.is_premium else help_text_no_prem
        await utils.answer(message, final_text)

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
                start_time = datetime.fromtimestamp(start_ts, MSK).strftime("%H:%M:%S")
                end_time = self._calculate_end_time(datetime.fromtimestamp(start_ts, MSK), total - count, speed)
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
                resume_time = datetime.fromtimestamp(resume_at, MSK).strftime("%H:%M:%S") if resume_at else "неизвестно"
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
        btns = [
            [{"text": self.strings["btn_tasks"], "callback": self._panel_tasks}, {"text": self.strings["btn_watch"], "callback": self._panel_watching}],
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
            await call.edit(text, reply_markup=btns)
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
        await call.edit(text, reply_markup=btns)

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
            start_time = datetime.fromtimestamp(start_ts, MSK).strftime("%H:%M:%S")
            elapsed = time.time() - start_ts
            elapsed_str = self._format_duration(elapsed)
            progress = round((current / total * 100), 1) if total > 0 else 0
            eta_left = self._calculate_eta(current, total, speed)
            end_time = self._calculate_end_time(datetime.fromtimestamp(start_ts, MSK), total - current, speed)
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
            resume_time = datetime.fromtimestamp(resume_at, MSK).strftime("%H:%M:%S") if resume_at else "неизвестно"
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
        else:
            text = self.strings["task_detail_error"].format(num=num, src=src, dest=dest)
            btns = [
                [{"text": "🗑 Удалить", "callback": self._remove_specific, "args": [tid]}],
                [{"text": "🔙 К списку", "callback": self._panel_tasks}]
            ]
        await call.edit(text, reply_markup=btns)

    async def _show_history_task_detail(self, call, task, num): # описание ниже
        """Показывает детали завершённой задачи"""
        src = utils.escape_html(task.get('src', 'Unknown'))
        dest = utils.escape_html(task.get('dest', 'Unknown'))
        count = task.get('current', 0)
        end_time = task.get('end_time', datetime.now(MSK))
        if isinstance(end_time, datetime):
            end_time_str = end_time.strftime("%H:%M:%S")
        else:
            end_time_str = str(end_time)
        start_ts = task.get('start_time', time.time())
        if isinstance(start_ts, (int, float)):
            start_dt = datetime.fromtimestamp(start_ts)
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
        await call.edit(text, reply_markup=btns)

    def _save_tasks(self):
        """Saves the current task queue to DB, including live progress from active_dumps."""
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
            tasks_to_save.append(snapshot)
        self.db.set("ChatCopy", "persistent_queue", tasks_to_save)

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
                self.active_dumps[tid]["status"] = "stopped"
                self.active_dumps[tid]["cancel"].set()
                self.task_queue = [t for t in self.task_queue if t['tid'] != tid]
                return await self._panel_tasks(call)
        else:
            if action == "stop":
                self.task_queue = [t for t in self.task_queue if t['tid'] != tid]
                return await self._panel_tasks(call)
        await self._show_task_detail(call, tid, 0)

    async def _stop_specific(self, call, tid): # останавливаем определенную задачу (копирование)
        if tid in self.active_dumps:
            self.active_dumps[tid]["status"] = "stopped"
            self.active_dumps[tid]["cancel"].set()
        self.task_queue = [t for t in self.task_queue if t['tid'] != tid]
        self._save_tasks() # сохраняем изменения
        await call.answer("Задача остановлена")
        await self._panel_tasks(call)

    async def _remove_specific(self, call, tid): # удаляем определенную задачу (копирование)
        if tid in self.active_dumps:
            self.active_dumps[tid]["status"] = "stopped"
            self.active_dumps[tid]["cancel"].set()
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
        await call.edit(text or "<i>Пусто</i>", reply_markup=chunked_btns)

    async def _panel_settings(self, call): # ну тут очевидно, вместо кфг такие настроечки
        text = (
            f"<b>⚙️ Настройки</b>\n\n"
            f"<b>Batch size:</b> <code>{self.config['batch_size']}</code>\n"
            f"<b>Delay:</b> <code>{self.config['delay']} сек</code>\n"
            f"<b>FloodWait buffer:</b> <code>{self.config['flood_buffer']} сек</code>"
        )
        btns = [
            [{"text": "📦 +10", "callback": self._change_setting, "args": ["batch_size", 10]},
             {"text": "📦 -10", "callback": self._change_setting, "args": ["batch_size", -10]}],
            [{"text": "⏱ +5с", "callback": self._change_setting, "args": ["delay", 5]},
             {"text": "⏱ -5с", "callback": self._change_setting, "args": ["delay", -5]}],
            [{"text": "🛡️ +5с буфер", "callback": self._change_setting, "args": ["flood_buffer", 5]},
             {"text": "🛡️ -5с буфер", "callback": self._change_setting, "args": ["flood_buffer", -5]}],
            [{"text": "🗑 Очистить кэш топиков", "callback": self._clear_topics_cache}],
            [{"text": self.strings["btn_back"], "callback": self._cb_back}]
        ]
        await call.edit(text, reply_markup=btns)

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
        await call.edit(text, reply_markup=btns)

    async def _change_setting(self, call, key, delta): # изменить настройки через панель чтоб в кфг не лезть
        current = self.config[key]
        if not isinstance(current, int):
            current = 10 if key == "delay" else 100 if key == "batch_size" else 5
        new_val = max(0, current + delta)
        if key == "batch_size":
            new_val = min(100, max(1, new_val))
        elif key == "flood_buffer":
            new_val = min(60, max(0, new_val))
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
