# Proprietary License Agreement

# Copyright (c) 2024-29 CodWiz

# Permission is hereby granted to any person obtaining a copy of this software and associated documentation files (the "Software"), to use the Software for personal and non-commercial purposes, subject to the following conditions:

# 1. The Software may not be modified, altered, or otherwise changed in any way without the explicit written permission of the author.

# 2. Redistribution of the Software, in original or modified form, is strictly prohibited without the explicit written permission of the author.

# 3. The Software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement. In no event shall the author or copyright holder be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of or in connection with the Software or the use or other dealings in the Software.

# 4. Any use of the Software must include the above copyright notice and this permission notice in all copies or substantial portions of the Software.

# 5. By using the Software, you agree to be bound by the terms and conditions of this license.
# For any inquiries or requests for permissions, please contact codwiz@yandex.ru.

# ---------------------------------------------------------------------------------
# Name: VirusTotal
# Description: Checks files for viruses using VirusTotal
# Author: @hikka_mods
# ---------------------------------------------------------------------------------
# meta developer: @hikka_mods
# scope: Api VirusTotal
# scope: Api VirusTotal 0.0.1
# requires: json aiohttp tempfile
# ---------------------------------------------------------------------------------

import asyncio
import logging
import os
import tempfile
from typing import Any, Dict, Optional

import aiohttp

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class VirusTotalMod(loader.Module):
    """Professional file scanning with VirusTotal"""

    strings = {
        "name": "VirusTotal",
        "no_file": "🚫 Reply to a file",
        "downloading": "📥 Downloading file...",
        "uploading": "📤 Uploading to VirusTotal...",
        "scanning": "🔍 Scanning in progress...",
        "waiting": "⏳ Waiting for analysis...",
        "no_key": "🚫 Set VirusTotal API key in config",
        "error": "❌ Error during scan",
        "size_limit": "📁 File exceeds 32MB limit",
        "timeout": "⏰ Scan timeout",
        "clean": "✅ File is clean",
        "suspicious": "⚠️ Suspicious file",
        "malicious": "⛔ Malicious file",
        "view_report": "📊 View full report",
        "close": "❌ Close",
        "engines": "Scan engines",
        "detections": "Detections",
        "status": "Status",
        "completed": "Completed",
        "queued": "Queued",
        "scan_date": "Scan date",
    }

    strings_ru = {
        "no_file": "🚫 Ответьте на файл",
        "downloading": "📥 Скачиваю файл...",
        "uploading": "📤 Загружаю на VirusTotal...",
        "scanning": "🔍 Сканирую...",
        "waiting": "⏳ Жду анализа...",
        "no_key": "🚫 Укажите API ключ в конфиге",
        "error": "❌ Ошибка при сканировании",
        "size_limit": "📁 Файл больше 32МБ",
        "timeout": "⏰ Таймаут сканирования",
        "clean": "✅ Файл чистый",
        "suspicious": "⚠️ Подозрительный файл",
        "malicious": "⛔ Вредоносный файл",
        "view_report": "📊 Полный отчёт",
        "close": "❌ Закрыть",
        "engines": "Антивирусов",
        "detections": "Обнаружено",
        "status": "Статус",
        "completed": "Завершён",
        "queued": "В очереди",
        "scan_date": "Дата сканирования",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_key",
                None,
                "VirusTotal API key from https://virustotal.com",
                validator=loader.validators.Hidden(),
            )
        )
        self.session: Optional[aiohttp.ClientSession] = None
        self.MAX_SIZE = 32 * 1024 * 1024  # 32MB
        self.TIMEOUT = 120  # seconds

    async def client_ready(self, client, db):
        self._client = client
        self._db = db

    async def on_unload(self):
        if self.session:
            await self.session.close()

    def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with API key"""
        if not self.session:
            headers = {"x-apikey": self.config["api_key"]}
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session

    @loader.command(
        ru_doc="[ответ] - просканировать файл через VirusTotal",
        en_doc="[reply] - scan file with VirusTotal",
    )
    async def vt(self, message):
        """Scan file with VirusTotal"""
        api_key = self.config["api_key"]
        if not api_key:
            return await utils.answer(message, self.strings["no_key"])

        reply = await message.get_reply_message()
        if not reply or not reply.document:
            return await utils.answer(message, self.strings["no_file"])

        async with self._get_session() as session:
            try:
                msg = await utils.answer(message, self.strings["downloading"])

                with tempfile.TemporaryDirectory() as tmpdir:
                    file_path = os.path.join(tmpdir, reply.file.name)
                    await reply.download_media(file_path)

                    file_size = os.path.getsize(file_path)
                    if file_size > self.MAX_SIZE:
                        return await msg.edit(self.strings["size_limit"])

                    await msg.edit(self.strings["uploading"])
                    analysis_id = await self._upload_file(session, file_path)

                    await msg.edit(self.strings["waiting"])
                    result = await self._wait_for_analysis(session, analysis_id)

                    await self._show_results(msg, analysis_id, result)

            except asyncio.TimeoutError:
                await utils.answer(message, self.strings["timeout"])
            except Exception as e:
                error_text = f"{self.strings['error']}: {str(e)[:100]}"
                await utils.answer(message, error_text)

    async def _upload_file(self, session: aiohttp.ClientSession, path: str) -> str:
        """Upload file to VirusTotal and return analysis ID"""
        with open(path, "rb") as f:
            form = aiohttp.FormData()
            form.add_field("file", f, filename=os.path.basename(path))

            async with session.post(
                "https://www.virustotal.com/api/v3/files", data=form
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data["data"]["id"]

    async def _wait_for_analysis(
        self, session: aiohttp.ClientSession, analysis_id: str
    ) -> Dict[str, Any]:
        """Poll analysis results until completion"""
        url = f"https://www.virustotal.com/api/v3/analyses/{analysis_id}"

        for _ in range(20):
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()

                status = data["data"]["attributes"]["status"]
                if status == "completed":
                    return data

                await asyncio.sleep(3)

        raise asyncio.TimeoutError()

    async def _show_results(self, message, analysis_id: str, result: Dict[str, Any]):
        """Display scan results in inline form"""
        stats = result["data"]["attributes"]["stats"]
        date = result["data"]["attributes"]["date"]

        malicious = stats.get("malicious", 0)
        suspicious = stats.get("suspicious", 0)
        undetected = stats.get("undetected", 0)
        harmless = stats.get("harmless", 0)
        total = malicious + suspicious + undetected + harmless

        if malicious > 0:
            verdict = self.strings["malicious"]
            emoji = "⛔"
        elif suspicious > 0:
            verdict = self.strings["suspicious"]
            emoji = "⚠️"
        else:
            verdict = self.strings["clean"]
            emoji = "✅"

        from datetime import datetime

        scan_date = datetime.fromtimestamp(date).strftime("%Y-%m-%d %H:%M:%S")

        text = (
            f"{emoji} <b>VirusTotal Scan Results</b>\n\n"
            f"<b>{self.strings['status']}:</b> {verdict}\n"
            f"<b>{self.strings['detections']}:</b> {malicious}\n"
            f"<b>{self.strings['engines']}:</b> {total}\n"
            f"<b>{self.strings['scan_date']}:</b> {scan_date}\n\n"
            f"<code>Malicious:  {malicious}/{total}</code>\n"
            f"<code>Suspicious: {suspicious}/{total}</code>\n"
            f"<code>Harmless:   {harmless}/{total}</code>\n"
            f"<code>Undetected: {undetected}/{total}</code>"
        )

        vt_url = f"https://www.virustotal.com/gui/file-analysis/{analysis_id}"

        await self.inline.form(
            text=text,
            message=message,
            reply_markup=[
                [{"text": f"🔗 {self.strings['view_report']}", "url": vt_url}],
                [{"text": self.strings["close"], "action": "close"}],
            ],
            ttl=300,  # 5 minutes timeout
        )
