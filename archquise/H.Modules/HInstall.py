# 🔐 Licensed under the GNU AGPLv3.
# ---------------------------------------------------------------------------------
# Name: HInstall
# Description: Provides H:Mods modules installation trough buttons
# Author: @hikka_mods
# ---------------------------------------------------------------------------------
# meta developer: @hikka_mods
# requires: PyCryptodome
# ---------------------------------------------------------------------------------
# #################################################################################
# ########## This module is based on @hikariatama 's hikkamods_socket!! ###########
# #################################################################################


__version__ = (1, 0, 0)

import base64
import logging

from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15

from telethon.tl.types import Message
from telethon import functions, types
from typing import Optional

from .. import loader, utils

logger = logging.getLogger(__name__)

pubkey_data = """
-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAvekpGqKiD2HZwY/J7jZv
PwGRobAS2TaC9HU5LUNRDg90jA/r8xgoFhlCBJocq8+XvJIWpgmIEYWJCz0KpCXu
Meu42bAXvLqniDOqnOt8FjXFapGZvEMLen1CLCRr1OQhVNpRlPjjWo7PM+YpUnbw
giqEZ9nA5DQ5Gi0vsSHXAnBa+ZIsxaY3EwosHMvUUhnnijcbBpkyYRJ8atvsT9AX
cNS+NjDE4Kj8jSnArQ1D1Ct1pcZEXD6DUk2k3HAD4OlZS5nY5IFchWEcpLT/Fjbt
BzGBZCJZ+rp8qR1tCVvVTV3itACc8O0Pirmptkrxb3A4pC0S8oxYBFQcnZAlIiw3
uX36O90AkRwbsdnsp2JVg5AAPUYvdsMoCGG+cSGZC73arqcrvn0VFo7EhsYq/1Ds
CevorFI4TiLVbSlFSVnX5baqmTj+XNhgaWWmiY/+mhErzsWtpCOHYFitf1xqp3zD
9O2Vs7lQIxMsHFISAEhn8BqQxvlwslfcjmbuJxkYriqAHXQGS3IZDXhEZXwouOUV
HGN2YD5aLK0L8OuTNY5cf1TN8C5xgVZoEodAKqAva/i1v/F6IQk3iEo0ncgypeyg
NM1TUudkQ+f1wXqLj2YaVKqRdKswl9vgYpUCHjGZfN+WYT4DbOMrJm1OFeen6geo
xqON1/xeRBgkE3tna3RuhmUCAwEAAQ==
-----END PUBLIC KEY-----
"""

pubkey = RSA.importKey(pubkey_data.strip())


@loader.tds
class HInstallMod(loader.Module):
    """Provides H:Mods modules installation trough buttons"""

    strings = {
        "name": "HInstall",
        "_cls_doc": "Provides H:Mods modules installation trough buttons",
        "module_downloaded": "Module downloaded!"
    }

    strings_ru = {
        "_cls_doc": "Позволяет устанавливать модули от H:Mods через кнопки",
        "module_downloaded": "Модуль загружен!"
    }

    async def on_dlmod(self, client, db):
        ent = await self.client(functions.users.GetFullUserRequest('@hinstall_bot'))
        if ent.full_user.blocked:
            await self.client(functions.contacts.UnblockRequest('@hinstall_bot'))
        await self.client.send_message('@hinstall_bot', '/start')
        await self.client.delete_dialog('@hinstall_bot')

    
    async def _load_module(self, url: str, message: Optional[Message] = None):
        loader_m = self.lookup("loader")

        await loader_m.download_and_install(url, None)

        if getattr(loader_m, "_fully_loaded", getattr(loader_m, "fully_loaded", False)):
            getattr(
                loader_m,
                "_update_modules_in_db",
                getattr(loader_m, "update_modules_in_db", lambda: None),
            )()
       

    async def watcher(self, message: Message):
        if not isinstance(message, Message):
            return
        if message.sender_id == 8104671142 and message.raw_text.startswith("#install"):
            await message.delete()
            fileref = (
                message.raw_text.split("#install:")[1].strip().splitlines()[0].strip()
                )
            sig = base64.b64decode(message.raw_text.splitlines()[1].strip().encode())
            try:
                h = SHA256.new(fileref.encode("utf-8"))
                pkcs1_15.new(pubkey).verify(h, sig)
            except (ValueError, TypeError):
                logger.error(f"Got message with non-verified signature ({fileref=})")
                return
            await self._load_module(f"https://raw.githubusercontent.com/archquise/H.Modules/refs/heads/main/{fileref}", message)
            await self.client.send_message('@hinstall_bot', self.strings['module_downloaded'])
            

    
