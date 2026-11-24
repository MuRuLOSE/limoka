# meta developer: @pymodule
# requires: cryptography

__version__ = (1, 0, 1)

import base64
import logging
from hashlib import sha256

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.exceptions import InvalidSignature

from telethon.tl.types import Message
from telethon import functions, types
from typing import Optional

from .. import loader, utils

logger = logging.getLogger(__name__)

pubkey_data = """
-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEA0S50qdajfeRmKqS+sBsn
VYYJL8loDMkfMf55flSPkhwwAwKbHk9i+VxRxHs32/J/LHxPR0ix3W6bgzf8m1/A
79uu2WkMrkfcIrAaOoz07EqHdyyD7MEZuHIAm977uQfdYgseOMa2uclYgNppJf35
8oqGP7+0+ks5IxzNLn8/7zeo6DrlyOVJ2lgv860NXPQ+WqTttMovkjDTTwBthE8i
WMg02r6fo+GFafeyaTRHusPAGqg2oZ3VFIxcsJFVqgxmGJkbQVGgSuPwHWM5yPGi
gx0uB71i6y4NXk/PpoYdQMDanOFJvYe7JBpiktcqk8LB/PqPEm4ctsdGFiu9PR6K
wrzo0fK9zbpbPyiAHaCC/0/LkfWT7Cdc9bECDPaSGgJJde9wUpDoz+coAc5BfeW5
6xu9J5fzkiw+zBQNlpkrtjG7JvqAYzul2GB+kDfCdVgkcQEPwBCTn6xGZvtWgE5b
yzQXaDkaTvbTUkUA41Ab6xsKSmU43otwV+9Rrzxovd+Nk7u9qwj5Ghambt37YNf3
vUJ9XQFr8uy2nKaPHzGoLgNCBReUyua6aYqMtqCkU1id+dI4HqgDMPlDDGxGV6mK
Gamdu+eIJHl9chHrlTOxEDetLxZLuAdnoDRzHJyTce6NCsyz8tvwWnKv+8l3R+Bu
B9EM+BFIFwCXKt85P/eabMcCAwEAAQ==
-----END PUBLIC KEY-----
"""

pubkey = serialization.load_pem_public_key(pubkey_data.strip().encode())

@loader.tds
class PyInstallMod(loader.Module):
    """Provides PyModule modules installation trough buttons"""

    strings = {
        "name": "PyInstall",
        "_cls_doc": "Provides PyModule modules installation trough buttons",
        "module_downloaded": "Module downloaded!"
    }

    strings_ru = {
        "_cls_doc": "Позволяет устанавливать модули от PyModule через кнопки",
        "module_downloaded": "Модуль загружен!"
    }

    async def on_dlmod(self, client, db):
        ent = await self.client(functions.users.GetFullUserRequest('@pymodule_bot'))
        if ent.full_user.blocked:
            await self.client(functions.contacts.UnblockRequest('@pymodule_bot'))
        await self.client.send_message('@pymodule_bot', '/start')
        await self.client.delete_dialog('@pymodule_bot')

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

        if message.sender_id == 7575984561 and message.raw_text.startswith("#install"):
            await message.delete()

            try:
                fileref = message.raw_text.split("#install:")[1].strip().splitlines()[0].strip()
                sig_b64 = message.raw_text.splitlines()[1].strip()
                sig = base64.b64decode(sig_b64)
            except (IndexError, ValueError):
                logger.error("Invalid #install message format")
                return

            try:
                pubkey.verify(
                    signature=sig,
                    data=fileref.encode("utf-8"),
                    padding=padding.PKCS1v15(),
                    algorithm=hashes.SHA256()
                )
                logger.info(f"Signature verified successfully for {fileref}")
            except InvalidSignature:
                logger.error(f"Got message with non-verified signature ({fileref=})")
                return
            except Exception as e:
                logger.error(f"Signature verification error: {e}")
                return

            await self._load_module(
                f"https://raw.githubusercontent.com/fiksofficial/python-modules/refs/heads/main/{fileref}",
                message
            )
            await self.client.send_message('@pymodule_bot', self.strings['module_downloaded'])
