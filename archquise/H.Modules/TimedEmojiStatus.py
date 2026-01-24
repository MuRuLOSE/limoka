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
# Name: TimedEmojiStatus
# Description: Temporary emoji status with auto-revert
# Author: @hikka_mods
# ---------------------------------------------------------------------------------
# meta developer: @hikka_mods
# scope: TimedEmojiStatus
# scope: TimedEmojiStatus 0.0.1
# ---------------------------------------------------------------------------------

import asyncio
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

from telethon.tl.functions.account import UpdateEmojiStatusRequest
from telethon.tl.types import EmojiStatus, MessageEntityCustomEmoji, Message

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class TimedEmojiStatusMod(loader.Module):
    """Temporary emoji status with auto-revert using scheduler"""

    strings = {
        "name": "TimedEmojiStatus",
        "no_emoji": "<emoji document_id=5337117114392127164>❌</emoji> <b>Specify emoji or emoji document_id</b>",
        "no_time": "<emoji document_id=5337117114392127164>❌</emoji> <b>Specify time (ex: 1h, 30m, 2d)</b>",
        "invalid_time": "<emoji document_id=5337117114392127164>❌</emoji> <b>Invalid time format (ex: 30m, 2h, 1d, 1w)</b>",
        "status_set": "<emoji document_id=5336965905773504919>✅</emoji> <b>Status set:</b>\n<b>Current:</b> {}\n<b>Final:</b> {}\n<b>For:</b> {} ({})",
        "status_updated": "<emoji document_id=5336965905773504919>✅</emoji> <b>Status updated: {}</b>",
        "no_status": "<emoji document_id=5337117114392127164>❌</emoji> <b>No active status</b>",
        "status_removed": "<emoji document_id=5336965905773504919>✅</emoji> <b>Status removed</b>",
        "current_status": "<emoji document_id=5348186233610711303>📊</emoji> <b>Active status:</b>\n<b>Current:</b> {}\n<b>Final:</b> {}\n<b>Until:</b> {} ({})",
        "no_premium": "<emoji document_id=5337117114392127164>❌</emoji> <b>Premium required for emoji status</b>",
        "error": "<emoji document_id=5337117114392127164>❌</emoji> <b>Error: {}</b>",
    }

    strings_ru = {
        "no_emoji": "<emoji document_id=5337117114392127164>❌</emoji> <b>Укажите эмодзи или document_id</b>",
        "no_time": "<emoji document_id=5337117114392127164>❌</emoji> <b>Укажите время (напр: 1h, 30m, 2d)</b>",
        "invalid_time": "<emoji document_id=5337117114392127164>❌</emoji> <b>Неверный формат времени (напр: 30m, 2h, 1d, 1w)</b>",
        "status_set": "<emoji document_id=5336965905773504919>✅</emoji> <b>Статус установлен:</b>\n<b>Текущий:</b> {}\n<b>Финальный:</b> {}\n<b>На:</b> {} ({})",
        "status_updated": "<emoji document_id=5336965905773504919>✅</emoji> <b>Статус обновлён: {}</b>",
        "no_status": "<emoji document_id=5337117114392127164>❌</emoji> <b>Нет активного статуса</b>",
        "status_removed": "<emoji document_id=5336965905773504919>✅</emoji> <b>Статус удалён</b>",
        "current_status": "<emoji document_id=5348186233610711303>📊</emoji> <b>Активный статус:</b>\n<b>Текущий:</b> {}\n<b>Финальный:</b> {}\n<b>До:</b> {} ({})",
        "no_premium": "<emoji document_id=5337117114392127164>❌</emoji> <b>Требуется Premium для эмодзи статуса</b>",
        "error": "<emoji document_id=5337117114392127164>❌</emoji> <b>Ошибка: {}</b>",
    }

    def __init__(self):
        self.status_data: Dict[int, Dict] = {}
        self.scheduler_tasks: Dict[int, asyncio.Task] = {}

    async def client_ready(self, client, db):
        self._client = client
        self._db = db

        if not self._client.hikka_me.premium:
            logger.warning("Premium required for emoji status functionality")

        await self._restore_active_statuses()

    async def _restore_active_statuses(self):
        """Restore and reschedule active statuses after restart"""
        saved = self._db.get(__name__, "statuses", {})
        current_time = time.time()

        for user_id, data in saved.items():
            end_time = data.get("end_time", 0)
            if end_time > current_time:
                remaining_time = end_time - current_time
                logger.info(
                    f"Restoring status for user {user_id}, remaining: {remaining_time}s"
                )

                task = asyncio.create_task(
                    self._schedule_revert_sleep(user_id, remaining_time)
                )
                self.scheduler_tasks[user_id] = task

                self.status_data[user_id] = data
            else:
                logger.info(f"Removing expired status for user {user_id}")
                del saved[user_id]

        if saved != self._db.get(__name__, "statuses", {}):
            self._db.set(__name__, "statuses", saved)

    def _parse_time(self, time_str: str) -> Optional[timedelta]:
        """Parse time string like 1h30m, 2d, 1w, 1mth"""
        pattern = r"(\d+)([smhdwmth]+)"
        matches = re.findall(pattern, time_str.lower())

        if not matches:
            return None

        total_seconds = 0
        for value, unit in matches:
            value = int(value)
            if unit == "s":
                total_seconds += value
            elif unit == "m":
                total_seconds += value * 60
            elif unit == "h":
                total_seconds += value * 3600
            elif unit == "d":
                total_seconds += value * 86400
            elif unit == "w":
                total_seconds += value * 604800
            elif unit in ["mth", "month"]:
                total_seconds += value * 2592000  # 30 days

        return timedelta(seconds=total_seconds)

    def _format_time(self, td: timedelta) -> str:
        """Format timedelta to human readable string"""
        total_days = td.days
        months = total_days // 30
        remaining_days = total_days % 30

        if months > 0:
            if remaining_days > 0:
                return f"{months}mth {remaining_days}d"
            return f"{months}mth"
        elif total_days > 0:
            return f"{total_days}d {td.seconds // 3600}h"
        elif td.seconds >= 3600:
            return f"{td.seconds // 3600}h {(td.seconds % 3600) // 60}m"
        else:
            return f"{td.seconds // 60}m"

    def _extract_document_id(self, emoji_input: str) -> Optional[int]:
        """Extract document_id from emoji string"""

        pattern = r"<emoji\s+document_id=(\d+)>.*?</emoji>"
        match = re.search(pattern, emoji_input)
        if match:
            return int(match.group(1))

        if emoji_input.isdigit():
            return int(emoji_input)

        return None

    def _extract_document_id_from_entities(self, message: Message) -> Optional[int]:
        """Extract document_id from message entities"""
        if not message.entities:
            return None

        for entity in message.entities:
            if isinstance(entity, MessageEntityCustomEmoji):
                return entity.document_id
        return None

    def _safe_emoji_display(
        self, emoji_str: str, document_id: Optional[int] = None
    ) -> str:
        """Safely display emoji without causing errors"""
        if not emoji_str:
            return "❌"

        if document_id:
            return f"[Custom Emoji ID: {document_id}]"

        if emoji_str.isdigit():
            return f"[Custom Emoji ID: {emoji_str}]"

        if "<emoji document_id=" in emoji_str:
         
            import re
            match = re.search(r'document_id=(\d+)', emoji_str)
            if match:
                return f"[Custom Emoji ID: {match.group(1)}]"
            return "[Custom Emoji]"

        if len(emoji_str) == 1 or (
            len(emoji_str) <= 4 and all(ord(c) >= 0x1F000 for c in emoji_str)
        ):
            return emoji_str

        return emoji_str[:10] + "..." if len(emoji_str) > 10 else emoji_str

    async def _set_emoji_status(
        self, emoji_input: str, until: datetime | None = None, message: Message = None
    ) -> tuple[bool, Optional[int]]:
        """Set emoji status (requires Premium). Returns (success, document_id)"""
        try:
            logger.info(f"Setting emoji status for: {emoji_input}")

            if not self._client.hikka_me.premium:
                logger.warning("Premium required for emoji status")
                return False, None

            if not emoji_input:
                logger.info("Removing emoji status")
                await self._client(UpdateEmojiStatusRequest(emoji_status=None))
                return True, None

            document_id = None

            if message:
                document_id = self._extract_document_id_from_entities(message)
                if document_id:
                    logger.info(
                        f"Found document_id from message entities: {document_id}"
                    )

            if not document_id:
                document_id = self._extract_document_id(emoji_input)
                if document_id:
                    logger.info(f"Extracted document_id from text: {document_id}")

            if not document_id:
                try:
                    logger.info("Trying to get document_id from test message")
                    test_msg = await self._client.send_message("me", emoji_input)
                    document_id = self._extract_document_id_from_entities(test_msg)
                    await self._client.delete_messages("me", [test_msg.id])

                    if document_id:
                        logger.info(
                            f"Found document_id from test message: {document_id}"
                        )
                    else:
                        logger.warning("No document_id found in test message")

                except Exception as e:
                    logger.error(f"Error getting document_id from test message: {e}")

            if document_id:
                try:
                    emoji_status = EmojiStatus(document_id=document_id, until=until)
                    await self._client(
                        UpdateEmojiStatusRequest(emoji_status=emoji_status)
                    )
                    logger.info(
                        f"Status set successfully with document_id: {document_id}"
                    )
                    return True, document_id
                except Exception as e:
                    logger.error(f"Error setting status: {e}")
                    if "PREMIUM" in str(e).upper():
                        return False, None
                    return False, None

            logger.warning("No document_id found, all methods failed")
            return False, None

        except Exception as e:
            logger.error(f"General error setting emoji status: {e}")
            return False, None

    async def _revert_status(self, user_id: int):
        """Revert status to final emoji or remove"""
        logger.info(f"Starting revert status for user {user_id}")

        if user_id in self.scheduler_tasks:
            del self.scheduler_tasks[user_id]

        if user_id in self.status_data:
            data = self.status_data[user_id]
            final_emoji = data.get("final_emoji", "")
            final_doc_id = data.get("final_doc_id")

            logger.info(
                f"Reverting status for user {user_id} to: '{final_emoji}' (saved doc_id: {final_doc_id})"
            )

            try:
                if final_emoji and final_doc_id:
                    logger.info(
                        f"Setting final emoji using saved document_id: {final_doc_id}"
                    )
                    try:
                        emoji_status = EmojiStatus(document_id=final_doc_id)
                        await self._client(
                            UpdateEmojiStatusRequest(emoji_status=emoji_status)
                        )
                        logger.info(
                            f"Successfully set final emoji with document_id: {final_doc_id}"
                        )
                    except Exception as e:
                        logger.error(f"Error setting final emoji with document_id: {e}")

                        success, _ = await self._set_emoji_status(final_emoji)
                        if not success:
                            await self._set_emoji_status("")
                elif final_emoji:
                    logger.info(f"Attempting to set final emoji: '{final_emoji}'")
                    success, final_doc_id = await self._set_emoji_status(final_emoji)
                    if success:
                        logger.info(
                            f"Successfully reverted to final emoji: '{final_emoji}' (doc_id: {final_doc_id})"
                        )
                    else:
                        logger.warning(
                            f"Failed to set final emoji '{final_emoji}', removing status instead"
                        )
                        await self._set_emoji_status("")
                else:
                    logger.info("No final emoji specified, removing status")
                    await self._set_emoji_status("")
            except Exception as e:
                logger.error(f"Error reverting status: {e}")

                try:
                    await self._set_emoji_status("")
                except Exception as e2:
                    logger.error(f"Error removing status: {e2}")

            logger.info(f"Removing status data for user {user_id}")
            del self.status_data[user_id]

        saved = self._db.get(__name__, "statuses", {})
        if user_id in saved:
            logger.info(f"Removing saved status for user {user_id}")
            del saved[user_id]
            self._db.set(__name__, "statuses", saved)

        logger.info(f"Revert status completed for user {user_id}")

    async def _schedule_revert_sleep(self, user_id: int, delay: float):
        """Schedule status revert using asyncio.sleep"""
        try:
            logger.info(f"Scheduling revert for user {user_id} in {delay} seconds")
            await asyncio.sleep(delay)
            await self._revert_status(user_id)
        except asyncio.CancelledError:
            logger.info(f"Revert task cancelled for user {user_id}")
        except Exception as e:
            logger.error(f"Error in scheduled revert for user {user_id}: {e}")

    async def _schedule_revert(self, user_id: int, data: Dict):
        """Schedule status revert"""
        end_time = data.get("end_time", 0)
        delay = max(0, end_time - time.time())

        self.status_data[user_id] = data

        await self._schedule_revert_sleep(user_id, delay)

    @loader.command(
        ru_doc="<время> <эмодзи/document_id> [финальный_эмодзи/document_id] - установить временный статус",
        en_doc="<time> <emoji/document_id> [final_emoji/document_id] - set temporary status",
    )
    async def setmoji(self, message: Message):
        """Set timed emoji status"""
        args = utils.get_args_raw(message)

        if not args:
            return await utils.answer(message, self.strings["no_time"])

        parts = args.split(maxsplit=2)
        if len(parts) < 2:
            return await utils.answer(message, self.strings["no_emoji"])

        time_str, initial_emoji = parts[0], parts[1]
        final_emoji = parts[2] if len(parts) > 2 else ""

        td = self._parse_time(time_str)
        if not td:
            return await utils.answer(message, self.strings["invalid_time"])

        if message.sender_id in self.scheduler_tasks:
            self.scheduler_tasks[message.sender_id].cancel()
            del self.scheduler_tasks[message.sender_id]

        try:
            success, initial_doc_id = await self._set_emoji_status(
                initial_emoji, message=message
            )
            if not success:
                return await utils.answer(message, self.strings["no_premium"])
        except Exception as e:
            return await utils.answer(message, self.strings["error"].format(str(e)))

        final_doc_id = None
        if final_emoji:
            try:
                final_doc_id = self._extract_document_id(final_emoji)
                if not final_doc_id:
                    if message and len(parts) > 2:
                        emoji_entities = [
                            e
                            for e in message.entities
                            if isinstance(e, MessageEntityCustomEmoji)
                        ]
                        if len(emoji_entities) >= 2:
                            final_doc_id = emoji_entities[1].document_id

                if not final_doc_id:
                    try:
                        test_msg = await self._client.send_message("me", final_emoji)
                        final_doc_id = self._extract_document_id_from_entities(test_msg)
                        await self._client.delete_messages("me", [test_msg.id])
                    except Exception as e:
                        logger.warning(
                            f"Could not get document_id for final emoji: {e}"
                        )

                if final_doc_id:
                    logger.info(f"Final emoji document_id: {final_doc_id}")
                else:
                    logger.warning(
                        f"Could not resolve document_id for final emoji: {final_emoji}"
                    )

            except Exception as e:
                logger.warning(f"Error getting final emoji document_id: {e}")

        end_time = time.time() + td.total_seconds()
        user_id = message.sender_id

        data = {
            "initial_emoji": initial_emoji,
            "final_emoji": final_emoji,
            "initial_doc_id": initial_doc_id,
            "final_doc_id": final_doc_id,
            "end_time": end_time,
            "set_time": time.time(),
        }

        self.status_data[user_id] = data

        saved = self._db.get(__name__, "statuses", {})
        saved[user_id] = data
        self._db.set(__name__, "statuses", saved)

        task = asyncio.create_task(
            self._schedule_revert_sleep(user_id, td.total_seconds())
        )
        self.scheduler_tasks[user_id] = task

        end_dt = datetime.fromtimestamp(end_time)
        time_str = self._format_time(td)

        logger.info(
            f"Display formatting - initial: '{initial_emoji}' (doc_id: {initial_doc_id}), final: '{final_emoji}' (doc_id: {final_doc_id})"
        )
        current_display = self._safe_emoji_display(initial_emoji, initial_doc_id)
        final_display = (
            self._safe_emoji_display(final_emoji, final_doc_id)
            if final_emoji
            else "❌ (удалить)"
        )

        logger.info(
            f"Display results - current: '{current_display}', final: '{final_display}'"
        )

        await utils.answer(
            message,
            self.strings["status_set"].format(
                current_display, final_display, time_str, f"{end_dt:%H:%M:%S}"
            ),
        )

    @loader.command(ru_doc="Показать текущий статус", en_doc="Show current status")
    async def showmoji(self, message: Message):
        """Show current emoji status"""
        user_id = message.sender_id

        if user_id not in self.status_data:
            return await utils.answer(message, self.strings["no_status"])

        data = self.status_data[user_id]
        end_time = data.get("end_time", 0)
        initial_emoji = data.get("initial_emoji", "")
        final_emoji = data.get("final_emoji", "")
        initial_doc_id = data.get("initial_doc_id")
        final_doc_id = data.get("final_doc_id")

        if end_time <= time.time():
            return await utils.answer(message, self.strings["no_status"])

        end_dt = datetime.fromtimestamp(end_time)
        remaining = timedelta(seconds=end_time - time.time())
        remaining_str = self._format_time(remaining)

        current_display = self._safe_emoji_display(initial_emoji, initial_doc_id)
        final_display = (
            self._safe_emoji_display(final_emoji, final_doc_id)
            if final_emoji
            else "❌ (удалить)"
        )

        await utils.answer(
            message,
            self.strings["current_status"].format(
                current_display, final_display, f"{end_dt:%H:%M:%S}", remaining_str
            ),
        )

    @loader.command(ru_doc="Удалить статус", en_doc="Remove status")
    async def removemoji(self, message: Message):
        """Remove emoji status"""
        user_id = message.sender_id

        if user_id not in self.status_data:
            return await utils.answer(message, self.strings["no_status"])

        if user_id in self.scheduler_tasks:
            self.scheduler_tasks[user_id].cancel()
            del self.scheduler_tasks[user_id]

        await self._revert_status(user_id)
        await utils.answer(message, self.strings["status_removed"])

    async def on_unload(self):
        """Cancel all scheduled tasks on unload"""
        for task in self.scheduler_tasks.values():
            task.cancel()
        self.scheduler_tasks.clear()
