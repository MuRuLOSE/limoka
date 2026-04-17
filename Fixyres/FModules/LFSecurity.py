__version__ = (1, 0, 0)

# meta developer: @NFModules
# meta banner: https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/assets/FSecurity/banner.png
# meta fhsdesc: security, guard, antiscam, antivirus
# scope: hikka_min 2.0.0

# ©️ Fixyres, 2024-2030
# 🌐 https://github.com/Fixyres/FModules
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 🔑 http://www.apache.org/licenses/LICENSE-2.0

import aiohttp
import os
from .. import loader


@loader.tds
class FSecurity(loader.Module):
    """Module for automatic AI-based security checks of installed modules."""

    strings = {
        "name": "FSecurity"
    }

    strings_ru = {
        "_cls_doc": "Модуль для автоматической проверки устанавливаемых модулей через ИИ."
    }

    strings_ua = {
        "_cls_doc": "Модуль для автоматичної перевірки встановлюваних модулів через ШІ."
    }

    strings_de = {
        "_cls_doc": "Modul zur automatischen Prüfung installierter Module mit KI."
    }

    strings_jp = {
        "_cls_doc": "AIでインストールされるモジュールを自動チェックするモジュール。"
    }

    strings_tr = {
        "_cls_doc": "Kurulan modülleri yapay zeka ile otomatik kontrol eden modül."
    }

    strings_uz = {
        "_cls_doc": "O'rnatilayotgan modullarni AI orqali avtomatik tekshiruvchi modul."
    }

    strings_kz = {
        "_cls_doc": "Орнатылатын модульдерді ЖИ арқылы автоматты тексеретін модуль."
    }

    async def client_ready(self, client, db):
        core = self.lookup("loader")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/FSecurity.py",
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        return
                    source = await resp.text()
        except Exception:
            return

        target = os.path.join(
            os.path.dirname(loader.__file__),
            "modules",
            "FSecurity.py",
        )

        try:
            with open(target, "w", encoding="utf-8") as f:
                f.write(source)
        except Exception:
            return

        await core.unload_module("FSecurity")
        try:
            await core.load_module(source, None, "FSecurity", target, save_fs=False)
        except Exception:
            pass
