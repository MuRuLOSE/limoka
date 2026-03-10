# Proprietary License Agreement

# Copyright (c) 2024-29 Archquise

# Permission is hereby granted to any person obtaining a copy of this software and associated documentation files (the "Software"), to use the Software for personal and non-commercial purposes, subject to the following conditions:

# 1. The Software may not be modified, altered, or otherwise changed in any way without the explicit written permission of the author.

# 2. Redistribution of the Software, in original or modified form, is strictly prohibited without the explicit written permission of the author.

# 3. The Software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement. In no event shall the author or copyright holder be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of or in connection with the Software or the use or other dealings in the Software.

# 4. Any use of the Software must include the above copyright notice and this permission notice in all copies or substantial portions of the Software.

# 5. By using the Software, you agree to be bound by the terms and conditions of this license.
# For any inquiries or requests for permissions, please contact archquise@gmail.com.

# ---------------------------------------------------------------------------------
# Name: FolderAutoRead
# Description: Automatically reads chats in selected folders
# Author: @hikka_mods
# ---------------------------------------------------------------------------------
# meta developer: @hikka_mods
# ---------------------------------------------------------------------------------

import logging

from telethon import functions
from telethon.tl.types import DialogFilter, InputPeerChannel

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class FolderAutoReadMod(loader.Module):
    """Automatically reads chats in selected folders"""

    strings = {
        "name": "FolderAutoRead",
        "not_exists_or_already_added": "<emoji document_id=5278578973595427038>🚫</emoji> <b>This folder does not exists or it is already added for tracking!</b>",
        "_cls_doc": "Automatically reads chats in selected folders every 60 seconds!",
        "_cmd_doc_addfolder": "Adds folder to the tracking list by it's name. Usage: .addfolder FolderName",
        "_cmd_doc_listfolders": "Prints list of tracked folders",
        "_cmd_doc_delfolder": "Deletes folder from the tracking list",
        "wrong_args": "<emoji document_id=5278578973595427038>🚫</emoji> <b>Wrong arguments!</b> Usage: .addfolder/delfolder FolderName\n\n<i>Tip: If you trying to delete the folder from the tracking list, double-check that it really still tracking using .listfolders</i>",
        "listfolders": "<emoji document_id=5278227821364275264>📁</emoji> <b>List of tracked folders:</b>\n",
        "delfolder": "<emoji document_id=5276384644739129761>🗑</emoji> <b>Folder is successfully deleted from the tracking list!</b>",
        "addfolder": "<emoji document_id=5278227821364275264>📁</emoji> <b>Folder is successfully added to the tracking list!</b>",
    }

    strings_ru = {
        "not_exists_or_already_added": "<emoji document_id=5278578973595427038>🚫</emoji> <b>Такой папки не существует, или она уже добавлена для отслеживания!</b>",
        "_cls_doc": "Автоматически читает чаты в выбранных папках каждые 60 секунд!",
        "_cmd_doc_addfolder": "Добавляет папки в список отслеживания по их названию. Использование: .addfolder НазваниеПапки",
        "_cmd_doc_listfolders": "Выводит список отслеживаемых папок",
        "_cmd_doc_delfolder": "Удаляет папку из списка для отслежнивания",
        "wrong_args": "<emoji document_id=5278578973595427038>🚫</emoji> <b>Неверные аргументы!</b> Использование: .addfolder/delfolder НазваниеПапки\n\n<i>Совет: Если вы пытаетесь удалить папку из списка отслеживания, проверьте, что она вообще отслеживается, используя .listfolders</i>",
        "listfolders": "<emoji document_id=5278227821364275264>📁</emoji> <b>Список отслеживаемых папок:</b>\n",
        "delfolder": "<emoji document_id=5276384644739129761>🗑</emoji> <b>Папка успешно удалена из листа отслеживания!</b>",
        "addfolder": "<emoji document_id=5278227821364275264>📁</emoji> <b>Папка успешно добавлена в лист отслеживания!</b>",
    }

    def __init__(self):
        self.tracked_folders = []

    async def client_ready(self, client, db):
        self.tracked_folders = self.pointer("tracked_folders", [])

    async def _read_peers(self, peers):
        for peer in peers:
            try:
                await self._client(functions.messages.ReadMentionsRequest(peer=peer))
                await self._client(functions.messages.ReadReactionsRequest(peer=peer))
                if isinstance(peer, InputPeerChannel):
                    await self._client(
                        functions.channels.ReadHistoryRequest(channel=peer, max_id=0)
                    )
                else:
                    await self._client(
                        functions.messages.ReadHistoryRequest(peer=peer, max_id=0)
                    )
            except Exception as e:
                logger.debug(f"Failed to read peer {peer}: {e}")

    @loader.loop(interval=60, autostart=True)
    async def read_chats_in_folders(self):
        if self.tracked_folders:
            all_folders = await self._client(
                functions.messages.GetDialogFiltersRequest()
            )
            for folder_name in self.tracked_folders:
                match = next(
                    (
                        f
                        for f in all_folders.filters
                        if isinstance(f, DialogFilter) and f.title.text == folder_name
                    ),
                    None,
                )
                if match is None:
                    continue
                await self._read_peers(match.pinned_peers)
                await self._read_peers(match.include_peers)

    @loader.command(
        ru_doc="Добавить папку в список отслеживания",
        en_doc="Add folder to the tracking list",
    )
    async def addfolder(self, message):
        arg = utils.get_args_raw(message)
        if arg:
            all_folders = await self._client(
                functions.messages.GetDialogFiltersRequest()
            )
            match = next(
                (
                    f
                    for f in all_folders.filters
                    if isinstance(f, DialogFilter) and f.title.text == arg
                ),
                None,
            )
            if match and arg not in self.tracked_folders:
                self.tracked_folders.append(arg)
                await utils.answer(message, self.strings("addfolder"))
            else:
                await utils.answer(message, self.strings("not_exists_or_already_added"))
        else:
            await utils.answer(message, self.strings("wrong_args"))

    @loader.command(
        ru_doc="Удалить папку из списка отслеживания",
        en_doc="Delete folder from the tracking list",
    )
    async def delfolder(self, message):
        arg = utils.get_args_raw(message)
        if arg and arg in self.tracked_folders:
            self.tracked_folders.remove(arg)
            await utils.answer(message, self.strings("delfolder"))
        else:
            await utils.answer(message, self.strings("wrong_args"))

    @loader.command(
        ru_doc="Список отслеживаемых папок",
        en_doc="List tracked folders",
    )
    async def listfolders(self, message):
        await utils.answer(
            message,
            self.strings("listfolders")
            + "\n".join(f"• {folder}" for folder in self.tracked_folders),
        )
