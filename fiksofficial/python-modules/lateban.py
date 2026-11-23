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

import asyncio
import logging
from datetime import datetime, timezone

from herokutl.tl.functions.channels import (
    EditBannedRequest,
    GetParticipantsRequest,
)
from herokutl.tl.types import (
    ChatBannedRights,
    ChannelParticipantsSearch,
    MessageService,
    MessageActionChatAddUser,
    MessageActionChatJoinedByLink,
    MessageActionChatJoinedByRequest,
)

from .. import loader, utils

logger = logging.getLogger(__name__)

_BAN = ChatBannedRights(until_date=None, view_messages=True)

@loader.tds
class LateBanMod(loader.Module):
    """Ban all members who joined the chat after a specified date/time"""

    strings = {
        "name": "LateBan",
        "no_args": (
            "❌ Specify date/time:\n"
            "<code>.lateban DD.MM.YYYY</code>\n"
            "<code>.lateban DD.MM.YYYY HH:MM</code>\n"
            "<code>.lateban HH:MM</code> — today"
        ),
        "bad_date": (
            "❌ Invalid format. Use <code>DD.MM.YYYY</code>, "
            "<code>DD.MM.YYYY HH:MM</code> or <code>HH:MM</code>"
        ),
        "not_chat":  "❌ Only works in supergroups",
        "no_rights": "❌ No permission to ban members",
        "scanning":  "🔍 Scanning members who joined after <b>{dt}</b>...",
        "confirm": (
            "⚠️ Found <b>{count}</b> members who joined after <b>{dt}</b>.\n\n"
            "Confirm ban:"
        ),
        "btn_ban":    "✅ Ban {count} members",
        "btn_cancel": "❌ Cancel",
        "banning":   "⏳ Banning {count} members...",
        "progress":  "⏳ Banned {done}/{total}...",
        "done": (
            "✅ Banned: <b>{banned}</b>\n"
            "Skipped (errors/bots): <b>{skipped}</b>\n"
            "Service messages deleted: <b>{deleted}</b>"
        ),
        "nobody":    "✅ No members found who joined after <b>{dt}</b>.",
    }

    strings_ru = {
        "name": "LateBan",
        "_cls_doc": "Заблокируйте всех участников, присоединившихся к чату после указанной даты/времени.",
        "no_args": (
            "❌ Укажи дату/время:\n"
            "<code>.lateban DD.MM.YYYY</code>\n"
            "<code>.lateban DD.MM.YYYY HH:MM</code>\n"
            "<code>.lateban HH:MM</code>"
        ),
        "bad_date": (
            "❌ Неверный формат. Используй <code>DD.MM.YYYY</code>, "
            "<code>DD.MM.YYYY HH:MM</code> или <code>HH:MM</code>"
        ),
        "not_chat":  "❌ Команда работает только в супергруппах",
        "no_rights": "❌ Нет прав на бан участников",
        "scanning":  "🔍 Сканирую участников, вступивших после <b>{dt}</b>...",
        "confirm": (
            "⚠️ Найдено <b>{count}</b> участников, вступивших после <b>{dt}</b>.\n\n"
            "Подтверди бан:"
        ),
        "btn_ban":    "✅ Забанить {count} участников",
        "btn_cancel": "❌ Отмена",
        "banning":   "⏳ Баню {count} участников...",
        "progress":  "⏳ Забанено {done}/{total}...",
        "done": (
            "✅ Забанено: <b>{banned}</b>\n"
            "Пропущено (ошибки/боты): <b>{skipped}</b>\n"
            "Удалено сервисных сообщений: <b>{deleted}</b>"
        ),
        "nobody":    "✅ Участников, вступивших после <b>{dt}</b>, не найдено.",
    }

    async def client_ready(self):
        pass

    @loader.command(ru_doc="<DD.MM.YYYY [HH:MM] | HH:MM> - Забанить всех, кто присоединился после определённой даты/времени.")
    async def latebancmd(self, message):
        """<DD.MM.YYYY [HH:MM] | HH:MM> — ban all who joined after this date/time"""
        args = utils.get_args_raw(message).strip()
        if not args:
            return await utils.answer(message, self.strings["no_args"])

        cutoff = _parse_dt(args)
        if cutoff is None:
            return await utils.answer(message, self.strings["bad_date"])

        chat = await message.get_chat()
        if not getattr(chat, "megagroup", False) and not getattr(chat, "gigagroup", False):
            return await utils.answer(message, self.strings["not_chat"])

        me = await self._client.get_me()
        perms = await self._client.get_permissions(chat, me)
        if not getattr(perms, "ban_users", False):
            return await utils.answer(message, self.strings["no_rights"])

        dt_str = cutoff.strftime("%d.%m.%Y %H:%M")
        await utils.answer(message, self.strings["scanning"].format(dt=dt_str))

        targets = await self._collect_targets(chat, cutoff, me.id)

        if not targets:
            return await utils.answer(message, self.strings["nobody"].format(dt=dt_str))

        await self.inline.form(
            message=message,
            text=self.strings["confirm"].format(count=len(targets), dt=dt_str),
            reply_markup=[[
                {
                    "text": self.strings["btn_ban"].format(count=len(targets)),
                    "callback": self._do_ban,
                    "args": (chat, targets, dt_str, cutoff),
                },
                {
                    "text": self.strings["btn_cancel"],
                    "callback": self._cancel,
                },
            ]],
            force_me=True,
        )

    async def _collect_targets(self, chat, cutoff: datetime, my_id: int) -> list:
        targets = []
        offset  = 0
        limit   = 200

        while True:
            res = await self._client(GetParticipantsRequest(
                channel=chat,
                filter=ChannelParticipantsSearch(""),
                offset=offset,
                limit=limit,
                hash=0,
            ))
            if not res.users:
                break

            users_map = {u.id: u for u in res.users}

            for p in res.participants:
                joined = getattr(p, "date", None)
                if joined is None:
                    continue
                if joined.tzinfo is None:
                    joined = joined.replace(tzinfo=timezone.utc)
                if joined <= cutoff:
                    continue

                uid  = p.user_id
                user = users_map.get(uid)
                if not user or user.id == my_id:
                    continue
                if getattr(user, "bot", False):
                    continue
                if p.__class__.__name__ in ("ChannelParticipantAdmin", "ChannelParticipantCreator"):
                    continue

                targets.append(uid)

            if len(res.participants) < limit:
                break
            offset += limit
            await asyncio.sleep(0.3)

        return targets

    async def _do_ban(self, call, chat, targets: list, dt_str: str, cutoff: datetime):
        await call.edit(self.strings["banning"].format(count=len(targets)))

        banned     = 0
        skipped    = 0
        banned_ids = set()

        for i, uid in enumerate(targets, 1):
            try:
                await self._client(EditBannedRequest(chat, uid, _BAN))
                banned += 1
                banned_ids.add(uid)
            except Exception as e:
                logger.warning("LateBan: skip %s — %s", uid, e)
                skipped += 1

            if i % 10 == 0:
                try:
                    await call.edit(
                        self.strings["progress"].format(done=i, total=len(targets))
                    )
                except Exception:
                    pass

            await asyncio.sleep(0.4)

        deleted = await self._delete_join_messages(chat, banned_ids, cutoff)

        await call.edit(self.strings["done"].format(
            banned=banned, skipped=skipped, deleted=deleted
        ))

    async def _delete_join_messages(
        self, chat, banned_ids: set, cutoff: datetime
    ) -> int:
        _JOIN_ACTIONS = (
            MessageActionChatAddUser,
            MessageActionChatJoinedByLink,
            MessageActionChatJoinedByRequest,
        )
        to_delete = []

        try:
            async for msg in self._client.iter_messages(
                chat,
                filter=MessageService,
                reverse=False,
                limit=None,
                offset_date=None,
            ):
                ts = msg.date
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts < cutoff:
                    break

                action = getattr(msg, "action", None)
                if not isinstance(action, _JOIN_ACTIONS):
                    continue

                if isinstance(action, MessageActionChatAddUser):
                    if any(uid in banned_ids for uid in action.users):
                        to_delete.append(msg.id)
                else:
                    sender_id = getattr(msg, "from_id", None)
                    if sender_id is not None:
                        uid = getattr(sender_id, "user_id", None)
                        if uid in banned_ids:
                            to_delete.append(msg.id)

        except Exception as e:
            logger.warning("LateBan: failed to scan service messages — %s", e)
            return 0

        deleted = 0
        for chunk in _chunks(to_delete, 100):
            try:
                await self._client.delete_messages(chat, chunk)
                deleted += len(chunk)
            except Exception as e:
                logger.warning("LateBan: delete chunk failed — %s", e)
            await asyncio.sleep(0.2)

        return deleted

    async def _cancel(self, call):
        await call.delete()

def _parse_dt(raw: str) -> datetime | None:
    """
    Supported formats:
      DD.MM.YYYY           → 00:00 UTC
      DD.MM.YYYY HH:MM     → HH:MM UTC
      HH:MM                → today HH:MM UTC
    """
    raw   = raw.strip()
    today = datetime.now(timezone.utc).date()

    try:
        return datetime.strptime(raw, "%d.%m.%Y %H:%M").replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    try:
        return datetime.strptime(raw, "%d.%m.%Y").replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    try:
        t = datetime.strptime(raw, "%H:%M").time()
        return datetime(
            today.year, today.month, today.day,
            t.hour, t.minute, tzinfo=timezone.utc,
        )
    except ValueError:
        pass

    return None


def _chunks(lst: list, n: int):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
