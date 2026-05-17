__version__ = (1, 0, 1)

# █▀▀▄   █▀▄▀█ █▀█ █▀▄ █▀
# ▀▀▀█ ▄ █ ▀ █ █▄█ █▄▀ ▄█

# #### Copyright (c) 2026 Archquise #####

# 💬 Contact: https://t.me/archquise
# 🔒 Licensed under the GNU AGPLv3.
# 📄 LICENSE: https://raw.githubusercontent.com/archquise/Q.Mods/main/LICENSE
# ---------------------------------------------------------------------------------
# Name: QNotes
# Description: A notes module that just works
# Author: @quise_m
# ---------------------------------------------------------------------------------
# meta developer: @quise_m
# meta banner: https://raw.githubusercontent.com/archquise/qmods_meta/main/qnotes.png
# ---------------------------------------------------------------------------------

import logging
import asyncio

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class QNotes(loader.Module):
    """A notes module that just works\nUsage: #notetag in any chat"""

    strings = {
        "name": "QNotes",
        "topic_desc": "Stores your notes content\nUsage: #notetag in any chat",
        "wrongargs": "<emoji document_id=5980953710157632545>❌</emoji> <b>Wrong arguments. Check command usage.</b>",
        "not_exist": "There is no such note!",
        "no_reply": "No reply! Reply to the message, which text will become a note.",
        "already_exists": "Seems like note with the same tag already exists. Overwrite?",
        "show_note_inline": "<blockquote>#{}</blockquote>\n\n<blockquote>{}</blockquote>",
        "notelist": "Note list:",
        "msg_not_found_inline": "Message with this note wasn't found. Probably, it was been removed. Note has been removed from the database.",
        "remnote_inline": "🗑 Remove",
        "close_inline": "❌ Close",
        "yes": "✔️ Yes",
        "no": "❌ No",
        "saved": "Note saved!",
        "removed": "Note removed!",
        "nonotes": "You don't have any notes!",
    }

    strings_ru = {
        "_cls_doc": "Модуль для заметок, который просто работает\nИспользование: #тегзаметки в любом чате",
        "topic_desc": "Хранит содержимое ваших заметок\nИспользование: #тегзаметки в любом чате",
        "wrongargs": "<emoji document_id=5980953710157632545>❌</emoji> <b>Неверные аргументы. Проверьте использование команды.</b>",
        "no_reply": "Нет реплая! Ответьте на сообещние, текст которого станет заметкой.",
        "not_exist": "Такой заметки не найдено!",
        "already_exists": "Кажется, заметка с таким тегом уже существует. Перезаписать?",
        "show_note_inline": "<blockquote>#{}</blockquote>\n\n<blockquote>{}</blockquote>",
        "notelist": "Список заметок:",
        "msg_not_found_inline": "Сообщение с этой заметкой не было найдено. Вероятно, оно было удалено. Заметка очищена из базы данных.",
        "remnote_inline": "🗑 Удалить",
        "close_inline": "❌ Закрыть",
        "yes": "✔️ Да",
        "no": "❌ Нет",
        "saved": "Заметка сохранена!",
        "removed": "Заметка удалена!",
        "nonotes": "Нет заметок!",
    }

    async def client_ready(self, client, db):  # type: ignore
        self._content_channel_id = await utils.wait_for_content_channel(self._db)
        self._notes_topic = await utils.asset_forum_topic(
            client=self._client,
            db=self._db,
            peer=self._content_channel_id,  # type: ignore
            title="QNotes | Storage",
            description=self.strings["topic_desc"],
            icon_emoji_id=5272001961326049733,
        )

        self._notemap = self.pointer("notemap", default={})

    async def _ask_overwrite(self, message):

        loop = asyncio.get_running_loop()
        future = loop.create_future()

        form = await self.inline.form(
            self.strings["already_exists"],
            message=message,
            reply_markup=[
                [
                    {
                        "text": self.strings["yes"],
                        "callback": (
                            lambda call, flag: (
                                future.set_result(flag) if not future.done() else None
                            )
                        ),
                        "args": (True,),
                    },
                    {
                        "text": self.strings["no"],
                        "callback": (
                            lambda call, flag: (
                                future.set_result(flag) if not future.done() else None
                            )
                        ),
                        "args": (False,),
                    },
                ]
            ],
        )

        try:
            async with asyncio.timeout(15):
                overwrite_answer = await future
        except TimeoutError:
            await form.delete()  # type: ignore
            return [False, message]

        if not overwrite_answer:
            await form.delete()  # type: ignore
            return [False, form]

        return [True, form]

    async def _show_note_inline(self, call, notetag, page=0):
        async def _remnote(call, notetag, note_msg):
            await note_msg.delete()
            self._notemap.pop(notetag, None)  # type: ignore

            await call.edit(self.strings["removed"])

        note_msg = await self._client.get_messages(
            self._content_channel_id, ids=notetag[1]
        )

        if not note_msg:
            self._notemap.pop(notetag[0], None)

            await call.edit(
                self.strings["msg_not_found_inline"],
                reply_markup=[
                    {"text": "⬅️ Назад", "callback": self._list_page, "args": (page,)},
                    {"text": self.strings["close_inline"], "action": "close"},
                ],
            )
            return

        await call.edit(
            self.strings["show_note_inline"].format(notetag[0], note_msg.text),  # type: ignore
            reply_markup=[
                [
                    {"text": "⬅️ Назад", "callback": self._list_page, "args": (page,)},
                    {
                        "text": self.strings["remnote_inline"],
                        "callback": _remnote,
                        "args": (notetag[0], note_msg),
                    },
                ],
                [{"text": self.strings["close_inline"], "action": "close"}],
            ],
        )

    def _build_list_markup(self, page: int):
        items = list(self._notemap.items())  # type: ignore
        total = -(-len(items) // 3)
        page = max(0, min(page, total - 1))
        rows = [
            [
                {
                    "text": notetag,
                    "callback": self._show_note_inline,
                    "args": ([notetag, msg_id], page),
                }
            ]
            for notetag, msg_id in items[page * 3 : (page + 1) * 3]
        ]
        return (
            rows
            + self.inline.build_pagination(
                callback=self._list_page,  # type: ignore
                total_pages=total,
                current_page=page + 1,
            )
            + [[{"text": self.strings["close_inline"], "action": "close"}]]
        )

    async def _list_page(self, call, page):
        await call.edit(
            text=self.strings["notelist"], reply_markup=self._build_list_markup(page)
        )

    @loader.command(
        ru_doc="Сохраняет заметку под тегом | Пример: .qnsave заметка",
        en_doc="Saves note by tag | Example: .qnsave note",
    )
    async def qnsave(self, message) -> None:
        args = utils.get_args(message)
        if not args:
            await utils.answer(message, self.strings["wrongargs"])
            return

        current_message = message

        if not (reply := await message.get_reply_message()):
            await utils.answer(message, self.strings["no_reply"])
            return
        try:
            if args[0].strip() in self._notemap:  # type: ignore
                overwrite = await self._ask_overwrite(message)
                if not overwrite[0]:
                    return
                await (
                    await self._client.get_messages(
                        self._content_channel_id,
                        ids=self._notemap[args[0].strip()],  # type: ignore
                    )
                ).delete()  # type: ignore
                current_message = overwrite[1]

            note_message = await self._client.send_message(
                self._content_channel_id, reply.text, reply_to=self._notes_topic.id
            )
            self._notemap[args[0].strip()] = note_message.id  # type: ignore

        except Exception as e:
            await utils.answer(current_message, f"Произошла ошибка: {e}")
            logger.exception("Произошла ошибка при сохранении заметки!")
            return
        await utils.answer(current_message, self.strings["saved"])

    @loader.command(
        ru_doc="Удаляет заметку по тегу | Пример: .qnrem заметка",
        en_doc="Removes note by tag | Example: .qnrem note",
    )
    async def qnrem(self, message) -> None:
        args = utils.get_args(message)
        if not args:
            await utils.answer(message, self.strings["wrongargs"])
            return

        if args[0] not in self._notemap or not (  # type: ignore
            note_message := await self._client.get_messages(
                self._content_channel_id,
                ids=self._notemap[args[0]],  # type: ignore
            )
        ):
            await utils.answer(message, self.strings["not_exist"])
            return

        await note_message.delete()  # type: ignore
        self._notemap.pop(args[0], None)  # type: ignore

        await utils.answer(message, self.strings["removed"])

    @loader.command(
        ru_doc="Выводит список всех заметок и позволяет управлять ими",
        en_doc="Shows note list and allows managing them",
    )
    async def qnlist(self, message) -> None:
        if self._notemap:
            await self.inline.form(
                text=self.strings["notelist"],
                reply_markup=self._build_list_markup(0),
                message=message,
            )
            return
        await utils.answer(message, self.strings["nonotes"])

    @loader.watcher(startswith="#")
    async def _note_watcher(self, message):
        if not (
            await self._client.dispatcher.security.check(message, self._note_watcher)
        ):
            return

        notetag = message.text.split("#", maxsplit=1)[1]

        if notetag in self._notemap:  # type: ignore
            if not (
                note_message := await self._client.get_messages(
                    self._content_channel_id,
                    ids=self._notemap[notetag],  # type: ignore
                )
            ):
                self._notemap.pop(notetag, None)  # type: ignore
                return
            notetext = note_message.text  # type: ignore
            await utils.answer(message, notetext)
            return
