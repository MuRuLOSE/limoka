__version__ = (1, 0, 0)

# meta developer: @FModules
# meta banner: https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/assets/FSecurity/banner.png
# scope: hikka_min 2.0.0

# ©️ Fixyres, 2024-2030
# 🌐 https://github.com/Fixyres/FModules
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 🔑 http://www.apache.org/licenses/LICENSE-2.0

import asyncio
import aiohttp
import html
import sys
import uuid
import copy
from contextlib import suppress
from .. import loader, utils


@loader.tds
class FSecurity(loader.Module):
    """Module for automatic AI-based security checks of installed modules."""

    strings = {
        "name": "FSecurity",
        "lang": "en",
        "unavailable": "AI module check is unavailable.",
        "suspicious": "AI interrupted installation of a suspicious module, reason:",
        "blocked": "AI blocked module installation, reason:",
        "continue": "Continue installation?"
    }

    strings_ru = {
        "lang": "ru",
        "_cls_doc": "Модуль для автоматической проверки устанавливаемых модулей через ИИ.",
        "unavailable": "Проверка модуля через ИИ недоступна.",
        "suspicious": "ИИ прервал установку подозрительного модуля, причина:",
        "blocked": "ИИ заблокировал установку модуля, причина:",
        "continue": "Продолжить установку?"
    }

    strings_ua = {
        "lang": "ua",
        "_cls_doc": "Модуль для автоматичної перевірки встановлюваних модулів через ШІ.",
        "unavailable": "Перевірка модуля через ШІ недоступна.",
        "suspicious": "ШІ перервав встановлення підозрілого модуля, причина:",
        "blocked": "ШІ заблокував встановлення модуля, причина:",
        "continue": "Продовжити встановлення?"
    }

    strings_de = {
        "lang": "de",
        "_cls_doc": "Modul zur automatischen Prüfung installierter Module mit KI.",
        "unavailable": "Die KI-Modulprüfung ist nicht verfügbar.",
        "suspicious": "Die KI hat die Installation eines verdächtigen Moduls unterbrochen, Grund:",
        "blocked": "Die KI hat die Modulinstallation blockiert, Grund:",
        "continue": "Installation fortsetzen?"
    }

    strings_jp = {
        "lang": "jp",
        "_cls_doc": "AIでインストールされるモジュールを自動チェックするモジュール。",
        "unavailable": "AIモジュールのチェックが利用できません。",
        "suspicious": "AIが疑わしいモジュールのインストールを中断しました、理由：",
        "blocked": "AIがモジュールのインストールをブロックしました、理由：",
        "continue": "インストールを続行しますか？"
    }

    strings_tr = {
        "lang": "tr",
        "_cls_doc": "Kurulan modülleri yapay zeka ile otomatik kontrol eden modül.",
        "unavailable": "Yapay zeka modül kontrolü kullanılamıyor.",
        "suspicious": "Yapay zeka şüpheli bir modülün kurulumunu durdurdu, sebep:",
        "blocked": "Yapay zeka modül kurulumunu engelledi, sebep:",
        "continue": "Kuruluma devam edilsin mi?"
    }

    strings_uz = {
        "lang": "uz",
        "_cls_doc": "O'rnatilayotgan modullarni AI orqali avtomatik tekshiruvchi modul.",
        "unavailable": "AI modul tekshiruvi mavjud emas.",
        "suspicious": "AI shubhali modul o'rnatilishini to'xtatdi, sabab:",
        "blocked": "AI modul o'rnatilishini blokladi, sabab:",
        "continue": "O'rnatishni davom ettirasizmi?"
    }

    strings_kz = {
        "lang": "kz",
        "_cls_doc": "Орнатылатын модульдерді ЖИ арқылы автоматты тексеретін модуль.",
        "unavailable": "AI модульін тексеру қолжетімсіз.",
        "suspicious": "AI күдікті модульді орнатуды тоқтатты, себебі:",
        "blocked": "AI модульді орнатуды бұғаттады, себебі:",
        "continue": "Орнатуды жалғастырасыз ба?"
    }

    def __init__(self):
        self.tasks = {}
        self.oreg = None
        self.oload = None

    async def client_ready(self, client, db):
        self.core = self.lookup("loader")
        self.modules = self.core.allmodules
        self.patch()

    async def on_unload(self):
        self.unpatch()

    async def check(self, code):
        try:
            form = aiohttp.FormData()
            form.add_field('file', code.encode('utf-8'), filename='module.py', content_type='text/x-python')
            form.add_field('lang', self.strings("lang") or "en")
            
            async with aiohttp.ClientSession() as session:
                async with session.post("https://api.fixyres.com/check", data=form, timeout=30) as resp:
                    if resp.status != 200:
                        return False
                    return await resp.json()
        except Exception:
            return False

    def format(self, state, reason=""):
        if state == "unavailable":
            return f'<b>{self.strings("unavailable")}</b>\n<b>{self.strings("continue")}</b>'
        if state == "suspicious":
            return f'<b>{self.strings("suspicious")}</b>\n<blockquote expandable>{utils.escape_html(reason)}</blockquote>\n<b>{self.strings("continue")}</b>'
        return f'<b>{self.strings("blocked")}</b>\n<blockquote expandable>{utils.escape_html(reason)}</blockquote>'

    def buttons(self, task):
        return [[
            {"text": "✓", "callback": self.confirm, "args": (task, "yes")},
            {"text": "✗", "callback": self.confirm, "args": (task, "no")}
        ]]

    def patch(self):
        if not self.oreg:
            self.oreg = getattr(self.modules, "register_module")
        if not self.oload:
            self.oload = self.core.load_module

        original = self.oload

        async def load(_, *args, **kwargs):
            base = utils.answer

            async def answer(message, response, *a, **k):
                if isinstance(response, str) and "😖</tg-emoji>" in response:
                    body = response.split("😖</tg-emoji>", 1)[1].strip()
                    if body in {"", "<b></b>", "<b> </b>"}:
                        with suppress(Exception):
                            if hasattr(message, "delete"):
                                await message.delete()
                        return message

                    if body.startswith("<b>") and body.endswith("</b>"):
                        decoded = html.unescape(body[3:-4])
                        response = response.split("😖</tg-emoji>", 1)[0] + f'😖</tg-emoji> {decoded}' if decoded else response.split("😖</tg-emoji>", 1)[0] + '😖</tg-emoji>'

                return await base(message, response, *a, **k)

            utils.answer = answer
            try:
                return await original(*args, **kwargs)
            finally:
                if utils.answer is answer:
                    utils.answer = base

        self.core.load_module = load.__get__(self.core, self.core.__class__)
        self.modules.register_module = self.register

    def unpatch(self):
        if self.oreg:
            self.modules.register_module = self.oreg
        if getattr(self, "core", None) and self.oload:
            self.core.load_module = self.oload

    def context(self):
        frame = sys._getframe()
        msg = None
        fmsg = None
        autoload = False

        while frame:
            locals = frame.f_locals
            if (
                frame.f_code.co_name == "load_module"
                and locals.get("self") is self.core
                and 'message' in locals
                and hasattr(locals['message'], 'edit')
            ):
                msg = locals['message']
                fmsg = locals.get('msg')
                break
            if (
                frame.f_code.co_name in {"_register_modules", "register_all"}
                and locals.get("self") is self.modules
            ):
                autoload = True
            frame = frame.f_back
            
        return msg, fmsg, autoload

    def target_chat(self, msg=None, fmsg=None):
        if msg:
            with suppress(Exception):
                target = copy.copy(msg)
                if fmsg:
                    target.reply_to_msg_id = fmsg.id
                elif not getattr(target, 'reply_to_msg_id', None):
                    target.reply_to_msg_id = target.id
                return target
        return None

    async def register(self, spec, name, origin="<core>", save_fs=False):
        if origin != "<core>" and name != self.__module__:
            code = ""
            
            if hasattr(spec.loader, "data") and spec.loader.data:
                code = spec.loader.data
                if isinstance(code, bytes):
                    code = code.decode("utf-8", errors="ignore")
            elif origin and origin.endswith(".py"):
                with suppress(Exception):
                    with open(origin, "r", encoding="utf-8") as f:
                        code = f.read()
            
            if code:
                check = await self.check(code)
                
                if check is not True:
                    msg, fmsg, autoload = self.context()
                    target = self.target_chat(msg, fmsg)

                    if isinstance(check, dict):
                        status = check.get("level", "blocked")
                        reason = check.get("reason", "")
                    else:
                        status = "unavailable"
                        reason = ""

                    if autoload:
                        return await self.oreg(spec, name, origin, save_fs=save_fs)

                    if not msg or not target:
                        raise loader.LoadError("")
                    
                    if msg:
                        with suppress(Exception):
                            msg.out = False

                    if status == "blocked":
                        text = self.format("blocked", reason)
                        raise loader.LoadError(text)
                        
                    task = str(uuid.uuid4())
                    event = asyncio.Event()
                    self.tasks[task] = {"event": event, "decision": False}
                    
                    try:
                        form = await self.inline.form(
                            text=self.format(status, reason),
                            message=target,
                            reply_markup=self.buttons(task)
                        )
                        
                        if not form:
                            raise loader.LoadError(reason)
 
                        await asyncio.wait_for(event.wait(), timeout=60.0)
                        
                        if not self.tasks.pop(task)["decision"]:
                            with suppress(Exception):
                                await form.delete()
                            raise loader.LoadError("")
                             
                    except asyncio.TimeoutError:
                        self.tasks.pop(task, None)
                        with suppress(Exception):
                            await form.delete()
                        raise loader.LoadError("")
                    except loader.LoadError:
                        raise
                    except Exception:
                        raise loader.LoadError("")
                        
        return await self.oreg(spec, name, origin, save_fs=save_fs)

    async def confirm(self, call, task, action):
        if task in self.tasks:
            self.tasks[task]["decision"] = (action == "yes")
            self.tasks[task]["event"].set()
        with suppress(Exception):
            await call.delete()
