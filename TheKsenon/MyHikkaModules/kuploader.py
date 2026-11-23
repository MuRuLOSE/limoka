# meta developer: @kmodules
# meta version: 2.0.0
# meta banner: https://i.ibb.co/LXxqyd3T/telecodex-file-b6eb8b2c-e187-4b91-928a-72bac914825f.jpg
# meta tags: uploader, upload, file, cloud, kmodules
# requires: aiohttp

import asyncio
import json
import os
import re
import secrets
from urllib.parse import quote

import aiohttp
from herokutl.tl.types import Message

from .. import loader, utils


class UploadError(RuntimeError):
    """Meow"""


@loader.tds
class KUploaderMod(loader.Module):
    """Загрузить файлы на хостинги."""

    strings = {
        "name": "K:Uploader 2.0",
        "uploading": (
            "<tg-emoji emoji-id=5873204392429096339>⌨</tg-emoji>"
            "<b>Uploading file...</b>"
        ),
        "uploaded": (
            "<tg-emoji emoji-id=5870570722778156940>📁</tg-emoji>"
            "<b>File uploaded:</b>\n<blockquote>{link}</blockquote>"
        ),
        "upload_error": (
            "<tg-emoji emoji-id=5870657884844462243>❌</tg-emoji> "
            "<b>File upload error: </b>\n<blockquote>{error}</blockquote>"
        ),
        "reply_to_file": (
            "<b>Upload a file to Uploader:</b> reply to a file, photo, video, "
            "or other media with <code>{prefix}{command}</code>."
        ),
        "file_too_large": (
            "<b>File is too large.</b> Module limit: <code>{limit} MB</code>."
        ),
    }

    strings_ru = {
        "name": "K:Uploader 2.0",
        "uploading": (
            "<tg-emoji emoji-id=5873204392429096339>⌨</tg-emoji>"
            "<b>Загружаю файл...</b>"
        ),
        "uploaded": (
            "<tg-emoji emoji-id=5870570722778156940>📁</tg-emoji>"
            "<b>Файл был загружен:</b>\n<blockquote>{link}</blockquote>"
        ),
        "upload_error": (
            "<tg-emoji emoji-id=5870657884844462243>❌</tg-emoji> "
            "<b>Ошибка при загрузке файла: </b>\n<blockquote>{error}</blockquote>"
        ),
        "reply_to_file": (
            "<b>Загрузить файл на Uploader:</b> ответьте на файл, фото, видео "
            "или другой медиафайл командой <code>{prefix}{command}</code>."
        ),
        "file_too_large": (
            "<b>Файл слишком большой.</b> Лимит модуля: <code>{limit} МБ</code>."
        ),
    }

    strings_ja = {
        "name": "K:Uploader 2.0",
        "uploading": (
            "<tg-emoji emoji-id=5873204392429096339>⌨</tg-emoji>"
            "<b>ファイルをアップロードしています...</b>"
        ),
        "uploaded": (
            "<tg-emoji emoji-id=5870570722778156940>📁</tg-emoji>"
            "<b>ファイルをアップロードしました:</b>\n<blockquote>{link}</blockquote>"
        ),
        "upload_error": (
            "<tg-emoji emoji-id=5870657884844462243>❌</tg-emoji> "
            "<b>ファイルのアップロード中にエラーが発生しました: </b>"
            "\n<blockquote>{error}</blockquote>"
        ),
        "reply_to_file": (
            "<b>Uploader にファイルをアップロード:</b> ファイル、写真、動画などに "
            "<code>{prefix}{command}</code> で返信してください。"
        ),
        "file_too_large": (
            "<b>ファイルが大きすぎます。</b> モジュールの上限: "
            "<code>{limit} MB</code>。"
        ),
    }

    GOFILE_HOSTS = (
        "upload.gofile.io",
        "upload-eu-par.gofile.io",
        "upload-na-phx.gofile.io",
        "upload-ap-sgp.gofile.io",
        "upload-ap-hkg.gofile.io",
    )

    COMMANDS = (
        ("uguu", "uguu"),
        ("quax", "quax"),
        ("tmpfiles", "tmpfiles"),
        ("tempsh", "temp"),
        ("filebin", "filebin"),
        ("waifuvault", "waifuvault"),
        ("gofile", "gofile"),
        ("file2", "file2"),
        ("tmp0", "tmp0"),
        ("tmpfile", "tmpfile"),
        ("filepost", "filepost"),
        ("storage", "storage"),
        ("tempfile", "tempfile"),
        ("easysend", "easysend"),
        ("zerostorage", "zerostorage"),
    )

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "max_size_mb",
                100,
                "Максимальный размер скачиваемого в память файла в МБ",
                validator=loader.validators.Integer(minimum=1, maximum=500),
            ),
            loader.ConfigValue(
                "timeout",
                180,
                "Тайм-аут одного загрузчика в секундах",
                validator=loader.validators.Integer(minimum=30, maximum=600),
            ),
        )

    @staticmethod
    def _short(value: object, limit: int = 360) -> str:
        value = re.sub(r"\s+", " ", str(value or "неизвестная ошибка")).strip()
        return value[:limit].rstrip() + ("…" if len(value) > limit else "")

    @classmethod
    def _error_from_body(cls, body: str) -> str:
        try:
            payload = json.loads(body)
        except (TypeError, ValueError):
            payload = None

        if isinstance(payload, dict):
            for key in ("description", "message", "error", "statusText"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return cls._short(value)

        text = re.sub(r"<[^>]+>", " ", body)
        return cls._short(text) if text.strip() else "пустой ответ сервера"

    @staticmethod
    def _json(body: str) -> dict:
        try:
            value = json.loads(body)
        except (TypeError, ValueError) as exc:
            raise UploadError("сервер вернул некорректный ответ") from exc

        if not isinstance(value, dict):
            raise UploadError("сервер вернул некорректный ответ")

        return value

    @staticmethod
    def _plain_url(body: str) -> str:
        match = re.search(r"https?://[^\s<>\"']+", body)
        if not match:
            raise UploadError("сервер не вернул ссылку")
        return match.group(0).rstrip(".,)")

    @staticmethod
    def _file_name(message: Message) -> str:
        file = getattr(message, "file", None)
        name = getattr(file, "name", None) or "upload.bin"
        name = os.path.basename(str(name)).replace("\x00", "")
        name = re.sub(r"[^\w.()\- ]", "_", name, flags=re.UNICODE).strip(". ")
        return (name or "upload.bin")[:180]

    @staticmethod
    def _mime_type(message: Message) -> str:
        return getattr(getattr(message, "file", None), "mime_type", None) or (
            "application/octet-stream"
        )

    @staticmethod
    def _file_size(message: Message) -> int:
        file = getattr(message, "file", None)
        return int(getattr(file, "size", 0) or 0)

    async def _request(self, session: aiohttp.ClientSession, method: str, url: str, **kwargs) -> str:
        try:
            async with session.request(method, url, **kwargs) as response:
                body = (await response.content.read(16_384)).decode(
                    "utf-8", errors="replace"
                )
                if not 200 <= response.status < 300:
                    raise UploadError(
                        f"HTTP {response.status}: {self._error_from_body(body)}"
                    )
                return body
        except UploadError:
            raise
        except asyncio.TimeoutError as exc:
            raise UploadError("тайм-аут соединения") from exc
        except aiohttp.ClientError as exc:
            raise UploadError(f"ошибка сети: {self._short(exc)}") from exc

    async def _multipart_upload(
        self,
        session: aiohttp.ClientSession,
        url: str,
        content: bytes,
        filename: str,
        mime_type: str,
        *,
        file_field: str = "file",
        fields: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        method: str = "POST",
    ) -> str:
        form = aiohttp.FormData()
        for key, value in (fields or {}).items():
            form.add_field(key, value)
        form.add_field(
            file_field,
            content,
            filename=filename,
            content_type=mime_type,
        )
        return await self._request(session, method, url, data=form, headers=headers)

    async def _upload_uguu(
        self,
        session: aiohttp.ClientSession,
        content: bytes,
        filename: str,
        mime_type: str,
    ) -> str:
        body = await self._multipart_upload(
            session,
            "https://uguu.se/upload",
            content,
            filename,
            mime_type,
            file_field="files[]",
        )
        payload = self._json(body)
        try:
            return payload["files"][0]["url"]
        except (KeyError, IndexError, TypeError) as exc:
            raise UploadError(self._error_from_body(body)) from exc

    async def _upload_quax(
        self,
        session: aiohttp.ClientSession,
        content: bytes,
        filename: str,
        mime_type: str,
    ) -> str:
        body = await self._multipart_upload(
            session,
            "https://qu.ax/upload.php",
            content,
            filename,
            mime_type,
            file_field="files[]",
        )
        payload = self._json(body)
        try:
            return payload["files"][0]["url"]
        except (KeyError, IndexError, TypeError) as exc:
            raise UploadError(self._error_from_body(body)) from exc

    async def _upload_tmpfiles(
        self,
        session: aiohttp.ClientSession,
        content: bytes,
        filename: str,
        mime_type: str,
    ) -> str:
        body = await self._multipart_upload(
            session,
            "https://tmpfiles.org/api/v1/upload",
            content,
            filename,
            mime_type,
        )
        payload = self._json(body)
        try:
            return payload["data"]["url"]
        except (KeyError, TypeError) as exc:
            raise UploadError(self._error_from_body(body)) from exc

    async def _upload_temp_sh(
        self,
        session: aiohttp.ClientSession,
        content: bytes,
        filename: str,
        mime_type: str,
    ) -> str:
        body = await self._multipart_upload(
            session,
            "https://temp.sh/upload",
            content,
            filename,
            mime_type,
        )
        return self._plain_url(body)

    async def _upload_filebin(
        self,
        session: aiohttp.ClientSession,
        content: bytes,
        filename: str,
        mime_type: str,
    ) -> str:
        bin_name = f"kuploader-{secrets.token_hex(8)}"
        encoded_name = quote(filename, safe="")
        url = f"https://filebin.net/{bin_name}/{encoded_name}"
        await self._request(
            session,
            "POST",
            url,
            data=content,
            headers={"Content-Type": mime_type},
        )
        return url

    async def _upload_waifuvault(
        self,
        session: aiohttp.ClientSession,
        content: bytes,
        filename: str,
        mime_type: str,
    ) -> str:
        body = await self._multipart_upload(
            session,
            "https://waifuvault.moe/rest",
            content,
            filename,
            mime_type,
            method="PUT",
        )
        payload = self._json(body)
        url = payload.get("url")
        if not isinstance(url, str) or not url.startswith("http"):
            raise UploadError(self._error_from_body(body))
        return url

    async def _upload_gofile(
        self,
        session: aiohttp.ClientSession,
        content: bytes,
        filename: str,
        mime_type: str,
    ) -> str:
        errors = []
        for host in self.GOFILE_HOSTS:
            try:
                body = await self._multipart_upload(
                    session,
                    f"https://{host}/uploadfile",
                    content,
                    filename,
                    mime_type,
                )
                payload = self._json(body)
                link = payload["data"]["downloadPage"]
                if not isinstance(link, str) or not link.startswith("http"):
                    raise UploadError(self._error_from_body(body))
                return link
            except (KeyError, TypeError, UploadError) as exc:
                errors.append(f"{host}: {self._short(exc, 90)}")

        raise UploadError("GoFile недоступен во всех регионах: " + "; ".join(errors))

    async def _upload_file2(
        self,
        session: aiohttp.ClientSession,
        content: bytes,
        filename: str,
        mime_type: str,
    ) -> str:
        body = await self._multipart_upload(
            session, "https://file2.me/api/upload", content, filename, mime_type
        )
        return self._plain_url(body)

    async def _upload_tmp0(
        self,
        session: aiohttp.ClientSession,
        content: bytes,
        filename: str,
        mime_type: str,
    ) -> str:
        body = await self._multipart_upload(
            session,
            "https://tmp0.cc/api/v1/upload",
            content,
            filename,
            mime_type,
            fields={"expires": "72h"},
        )
        payload = self._json(body)
        url = payload.get("fullUrl")
        if not isinstance(url, str) or not url.startswith("http"):
            raise UploadError(self._error_from_body(body))
        return url

    async def _upload_tmpfile(
        self,
        session: aiohttp.ClientSession,
        content: bytes,
        filename: str,
        mime_type: str,
    ) -> str:
        body = await self._multipart_upload(
            session,
            "https://tmpfile.link/api/upload",
            content,
            filename,
            mime_type,
            headers={"Accept": "application/json"},
        )
        payload = self._json(body)
        url = payload.get("downloadLink")
        if not isinstance(url, str) or not url.startswith("http"):
            raise UploadError(self._error_from_body(body))
        return url

    async def _upload_filepost(
        self,
        session: aiohttp.ClientSession,
        content: bytes,
        filename: str,
        mime_type: str,
    ) -> str:
        body = await self._multipart_upload(
            session,
            "https://filepost.dev/v1/demo-upload",
            content,
            filename,
            mime_type,
        )
        payload = self._json(body)
        url = payload.get("url")
        if not isinstance(url, str) or not url.startswith("http"):
            raise UploadError(self._error_from_body(body))
        return url

    async def _upload_storage(
        self,
        session: aiohttp.ClientSession,
        content: bytes,
        filename: str,
        mime_type: str,
    ) -> str:
        body = await self._multipart_upload(
            session,
            "https://storage.to/api/sharex/upload",
            content,
            filename,
            mime_type,
        )
        payload = self._json(body)
        url = payload.get("url")
        if not isinstance(url, str) or not url.startswith("http"):
            raise UploadError(self._error_from_body(body))
        return url

    async def _upload_tempfile(
        self,
        session: aiohttp.ClientSession,
        content: bytes,
        filename: str,
        mime_type: str,
    ) -> str:
        body = await self._multipart_upload(
            session,
            "https://tempfile.org/api/upload/local",
            content,
            filename,
            mime_type,
            file_field="files",
            fields={"expiryHours": "48"},
        )
        payload = self._json(body)
        try:
            url = payload["files"][0]["url"]
        except (KeyError, IndexError, TypeError) as exc:
            raise UploadError(self._error_from_body(body)) from exc
        if not isinstance(url, str) or not url.startswith("http"):
            raise UploadError(self._error_from_body(body))
        return url

    async def _upload_easysend(
        self,
        session: aiohttp.ClientSession,
        content: bytes,
        filename: str,
        mime_type: str,
    ) -> str:
        body = await self._multipart_upload(
            session,
            "https://easysend.co/api/v1/upload",
            content,
            filename,
            mime_type,
            file_field="files[]",
        )
        payload = self._json(body)
        url = payload.get("share_link")
        if not isinstance(url, str) or not url.startswith("http"):
            raise UploadError(self._error_from_body(body))
        return url

    async def _upload_zerostorage(
        self,
        session: aiohttp.ClientSession,
        content: bytes,
        filename: str,
        mime_type: str,
    ) -> str:
        body = await self._multipart_upload(
            session,
            "https://upload.zerostorage.net/api/upload/universal",
            content,
            filename,
            mime_type,
        )
        payload = self._json(body)
        url = payload.get("viewUrl")
        if not isinstance(url, str) or not url.startswith("http"):
            raise UploadError(self._error_from_body(body))
        return url

    async def _upload(
        self,
        session: aiohttp.ClientSession,
        provider: str,
        content: bytes,
        filename: str,
        mime_type: str,
    ) -> str:
        if provider == "gofile":
            return await self._upload_gofile(session, content, filename, mime_type)

        methods = {
            "uguu": self._upload_uguu,
            "quax": self._upload_quax,
            "tmpfiles": self._upload_tmpfiles,
            "temp": self._upload_temp_sh,
            "filebin": self._upload_filebin,
            "waifuvault": self._upload_waifuvault,
            "file2": self._upload_file2,
            "tmp0": self._upload_tmp0,
            "tmpfile": self._upload_tmpfile,
            "filepost": self._upload_filepost,
            "storage": self._upload_storage,
            "tempfile": self._upload_tempfile,
            "easysend": self._upload_easysend,
            "zerostorage": self._upload_zerostorage,
        }
        return await methods[provider](session, content, filename, mime_type)

    async def _run_provider(
        self,
        message: Message,
        provider: str,
        command: str,
    ):
        if not (reply := await message.get_reply_message()) or not reply.media:
            await utils.answer(
                message,
                self.strings["reply_to_file"].format(
                    prefix=self.get_prefix(), command=command
                ),
            )
            return

        limit = int(self.config["max_size_mb"]) * 1024 * 1024
        if size := self._file_size(reply):
            if size > limit:
                await utils.answer(
                    message,
                    self.strings["file_too_large"].format(
                        limit=self.config["max_size_mb"]
                    ),
                )
                return

        status = await utils.answer(message, self.strings["uploading"])
        try:
            content = await reply.download_media(bytes)
        except Exception as exc:
            await utils.answer(
                status,
                self.strings["upload_error"].format(
                    error=utils.escape_html(self._short(exc))
                ),
            )
            return

        if not content:
            await utils.answer(
                status,
                self.strings["upload_error"].format(
                    error="Telegram не вернул содержимое файла"
                ),
            )
            return

        content = bytes(content)
        if len(content) > limit:
            await utils.answer(
                status,
                self.strings["file_too_large"].format(
                    limit=self.config["max_size_mb"]
                ),
            )
            return

        filename = self._file_name(reply)
        mime_type = self._mime_type(reply)
        timeout = aiohttp.ClientTimeout(total=int(self.config["timeout"]))

        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                link = await self._upload(
                    session, provider, content, filename, mime_type
                )
            except (KeyError, UploadError) as exc:
                error = self._short(exc)
            except Exception as exc:
                error = self._short(exc)
            else:
                await utils.answer(
                    status,
                    self.strings["uploaded"].format(
                        link=utils.escape_html(link)
                    ),
                )
                return

        await utils.answer(
            status,
            self.strings["upload_error"].format(
                error=utils.escape_html(error)
            ),
        )

    @loader.command(ru_doc="— загрузить файл на Uguu", en_doc="— upload a file to Uguu")
    async def uguu(self, message: Message):
        """Upload a file to Uguu."""
        await self._run_provider(message, "uguu", "uguu")

    @loader.command(ru_doc="— загрузить файл на QuAx", en_doc="— upload a file to QuAx")
    async def quax(self, message: Message):
        """Upload a file to QuAx."""
        await self._run_provider(message, "quax", "quax")

    @loader.command(ru_doc="— загрузить файл на Tmpfiles", en_doc="— upload a file to Tmpfiles")
    async def tmpfiles(self, message: Message):
        """Upload a file to Tmpfiles."""
        await self._run_provider(message, "tmpfiles", "tmpfiles")

    @loader.command(ru_doc="— загрузить файл на Temp.sh", en_doc="— upload a file to Temp.sh")
    async def tempsh(self, message: Message):
        """Upload a file to Temp.sh."""
        await self._run_provider(message, "temp", "tempsh")

    @loader.command(ru_doc="— загрузить файл на Filebin", en_doc="— upload a file to Filebin")
    async def filebin(self, message: Message):
        """Upload a file to Filebin."""
        await self._run_provider(message, "filebin", "filebin")

    @loader.command(ru_doc="— загрузить файл на WaifuVault", en_doc="— upload a file to WaifuVault")
    async def waifuvault(self, message: Message):
        """Upload a file to WaifuVault."""
        await self._run_provider(message, "waifuvault", "waifuvault")

    @loader.command(ru_doc="— загрузить файл на GoFile(авторегионы)", en_doc="— upload a file to GoFile (automatic regions)")
    async def gofile(self, message: Message):
        """Upload a file to GoFile, switching regions automatically on error."""
        await self._run_provider(message, "gofile", "gofile")

    @loader.command(ru_doc="— загрузить файл на File2.me", en_doc="— upload a file to File2.me")
    async def file2(self, message: Message):
        """Upload a file to File2.me."""
        await self._run_provider(message, "file2", "file2")

    @loader.command(ru_doc="— загрузить файл на Tmp0.cc", en_doc="— upload a file to Tmp0.cc")
    async def tmp0(self, message: Message):
        """Upload a file to Tmp0.cc."""
        await self._run_provider(message, "tmp0", "tmp0")

    @loader.command(ru_doc="— загрузить файл на Tmpfile.link", en_doc="— upload a file to Tmpfile.link")
    async def tmpfile(self, message: Message):
        """Upload a file to Tmpfile.link."""
        await self._run_provider(message, "tmpfile", "tmpfile")

    @loader.command(ru_doc="— загрузить файл на FilePost", en_doc="— upload a file to FilePost")
    async def filepost(self, message: Message):
        """Upload a file to FilePost."""
        await self._run_provider(message, "filepost", "filepost")

    @loader.command(ru_doc="— загрузить файл на Storage.to", en_doc="— upload a file to Storage.to")
    async def storage(self, message: Message):
        """Upload a file to Storage.to."""
        await self._run_provider(message, "storage", "storage")

    @loader.command(ru_doc="— загрузить файл на TempFile.org", en_doc="— upload a file to TempFile.org")
    async def tempfile(self, message: Message):
        """Upload a file to TempFile.org."""
        await self._run_provider(message, "tempfile", "tempfile")

    @loader.command(ru_doc="— загрузить файл на EasySend", en_doc="— upload a file to EasySend")
    async def easysend(self, message: Message):
        """Upload a file to EasySend."""
        await self._run_provider(message, "easysend", "easysend")

    @loader.command(ru_doc="— загрузить файл на ZeroStorage", en_doc="— upload a file to ZeroStorage")
    async def zerostorage(self, message: Message):
        """Upload a file to ZeroStorage."""
        await self._run_provider(message, "zerostorage", "zerostorage")
