__version__ = (1, 0, 0)

# meta developer: @NFModules

import asyncio
import aiohttp
import html
import sys
import uuid
import copy
import hashlib
import json
import re
from contextlib import suppress
from .. import loader, utils


@loader.tds
class FSecurity(loader.Module):
    """Module for automatic AI-based security checks of installed modules."""

    strings = {
        "name": "FSecurity",
        "lang": "English",
        "unavailable": "AI module{} check is unavailable.",
        "suspicious": "AI interrupted installation of a suspicious module{}, reason:",
        "blocked": "AI blocked module installation{}, reason:",
        "continue": "Continue installation?",
        "strict_mode_doc": "Block loading modules by any method (lm/dlm allowed) if the AI API is unavailable or the module is suspicious. On restart, this also applies to already installed modules.",
        "nvidia_api_key_doc": "API key from build.nvidia.com, used for AI checks. If not specified, a public key from GitHub will be used."
    }

    strings_ru = {
        "lang": "Russian",
        "_cls_doc": "Модуль для автоматической проверки устанавливаемых модулей через ИИ.",
        "unavailable": "Проверка модуля{} через ИИ недоступна.",
        "suspicious": "ИИ прервал установку подозрительного модуля{}, причина:",
        "blocked": "ИИ заблокировал установку модуля{}, причина:",
        "continue": "Продолжить установку?",
        "strict_mode_doc": "Не позволять загружать модули любым методом (lm/dlm разрешено), если API ИИ недоступен или модуль подозрителен. При перезагрузке работает даже на уже установленные модули.",
        "nvidia_api_key_doc": "API ключ от build.nvidia.com, используется для проверки через ИИ. Если вы его не укажете, будет использоваться общий ключ с GitHub."
    }

    strings_ua = {
        "lang": "Ukraine",
        "_cls_doc": "Модуль для автоматичної перевірки встановлюваних модулів через ШІ.",
        "unavailable": "Перевірка модуля{} через ШІ недоступна.",
        "suspicious": "ШІ перервав встановлення підозрілого модуля{}, причина:",
        "blocked": "ШІ заблокував встановлення модуля{}, причина:",
        "continue": "Продовжити встановлення?",
        "strict_mode_doc": "Не дозволяти завантажувати модулі будь-яким методом (lm/dlm дозволено), якщо API ШІ недоступний або модуль підозрілий. При перезавантаженні працює навіть на вже встановлені модулі.",
        "nvidia_api_key_doc": "API ключ від build.nvidia.com, використовується для перевірки через ШІ. Якщо ви його не вкажете, буде використовуватися загальний ключ з GitHub."
    }

    strings_de = {
        "lang": "Germany",
        "_cls_doc": "Modul zur automatischen Prüfung installierter Module mit KI.",
        "unavailable": "Die KI-Modulprüfung{} ist nicht verfügbar.",
        "suspicious": "Die KI hat die Installation eines verdächtigen Moduls unterbrochen{}, Grund:",
        "blocked": "Die KI hat die Modulinstallation blockiert{}, Grund:",
        "continue": "Installation fortsetzen?",
        "strict_mode_doc": "Das Laden von Modulen mit jeder Methode blockieren (lm/dlm erlaubt), wenn die KI-API nicht verfügbar ist oder das Modul verdächtig ist. Beim Neustart gilt dies auch für bereits installierte Module.",
        "nvidia_api_key_doc": "API-Schlüssel von build.nvidia.com, der für KI-Prüfungen verwendet wird. Wenn nicht angegeben, wird ein öffentlicher Schlüssel von GitHub verwendet."
    }

    strings_jp = {
        "lang": "Japanese",
        "_cls_doc": "AIでインストールされるモジュールを自動チェックするモジュール。",
        "unavailable": "AIモジュール{}のチェックが利用できません。",
        "suspicious": "AIが疑わしいモジュールのインストールを中断しました{}、理由：",
        "blocked": "AIがモジュールのインストールをブロックしました{}、理由：",
        "continue": "インストールを続行しますか？",
        "strict_mode_doc": "AI APIが利用できない場合や疑わしいモジュールの場合、すべての方法でモジュールの読み込みをブロックします（lm/dlmは許可）。再起動時にはインストール済みモジュールにも適用されます。",
        "nvidia_api_key_doc": "build.nvidia.com のAPIキー。AIチェックに使用されます。指定しない場合は、GitHubのパブリックキーが使用されます。"
    }

    strings_tr = {
        "lang": "Turkish",
        "_cls_doc": "Kurulan modülleri yapay zeka ile otomatik kontrol eden modül.",
        "unavailable": "Yapay zeka modül{} kontrolü kullanılamıyor.",
        "suspicious": "Yapay zeka şüpheli bir modülün kurulumunu durdurdu{}, sebep:",
        "blocked": "Yapay zeka modül kurulumunu engelledi{}, sebep:",
        "continue": "Kuruluma devam edilsin mi?",
        "strict_mode_doc": "AI API kullanılamıyorsa veya modül şüpheliyse, tüm yöntemlerle modül yüklenmesini engelle (lm/dlm izinli). Yeniden başlatmada zaten kurulu modüller için de geçerlidir.",
        "nvidia_api_key_doc": "Yapay zeka kontrolleri için kullanılan build.nvidia.com API anahtarı. Belirtilmezse GitHub'daki genel anahtar kullanılacaktır."
    }

    strings_uz = {
        "lang": "Uzbekistan",
        "_cls_doc": "O'rnatilayotgan modullarni AI orqali avtomatik tekshiruvchi modul.",
        "unavailable": "AI modul{} tekshiruvi mavjud emas.",
        "suspicious": "AI shubhali modul o'rnatilishini to'xtatdi{}, sabab:",
        "blocked": "AI modul o'rnatilishini blokladi{}, sabab:",
        "continue": "O'rnatishni davom ettirasizmi?",
        "strict_mode_doc": "AI API mavjud bo'lmasa yoki modul shubhali bo'lsa, barcha usullar bilan modul yuklashni bloklash (lm/dlm ruxsat etilgan). Qayta ishga tushirishda allaqachon o'rnatilgan modullarga ham ta'sir qiladi.",
        "nvidia_api_key_doc": "build.nvidia.com API kaliti, AI orqali tekshirish uchun ishlatiladi. Agar ko'rsatmasangiz, GitHub-dan umumiy kalit ishlatiladi."
    }

    strings_kz = {
        "lang": "Kazakhstan",
        "_cls_doc": "Орнатылатын модульдерді ЖИ арқылы автоматты тексеретін модуль.",
        "unavailable": "AI модуль{} тексеру қолжетімсіз.",
        "suspicious": "AI күдікті модульді орнатуды тоқтатты{}, себебі:",
        "blocked": "AI модульді орнатуды бұғаттады{}, себебі:",
        "continue": "Орнатуды жалғастырасыз ба?",
        "strict_mode_doc": "AI API қолжетімсіз болса немесе модуль күдікті болса, барлық әдістермен модуль жүктеуді бұғаттау (lm/dlm рұқсат етілген). Қайта іске қосқанда орнатылған модульдерге де қолданылады.",
        "nvidia_api_key_doc": "build.nvidia.com API кілті, ЖИ арқылы тексеру үшін қолданылады. Егер оны көрсетпесеңіз, GitHub-тан ортақ кілт пайдаланылады."
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "strict_mode",
                False,
                lambda: self.strings("strict_mode_doc"),
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "nvidia_api_key",
                "",
                lambda: self.strings("nvidia_api_key_doc"),
                validator=loader.validators.Hidden(),
            )
        )
        self.tasks = {}
        self.oreg = None
        self.oload = None

    async def client_ready(self, client, db):
        self.__origin__ = "<fsecurity>"
        self.core = self.lookup("loader")
        self.modules = self.core.allmodules
        self.restore_hooks()
        self.patch()

    async def on_unload(self):
        self.unpatch()

    def _render_prompt(self, prompt, **values):
        rendered = prompt
        for key, value in values.items():
            rendered = rendered.replace("{" + key + "}", str(value))
        return rendered

    def _split_code(self, code):
        chunk_size = 180000
        if len(code) <= chunk_size:
            return [code]

        chunks = []
        current =[]
        current_len = 0

        for line in code.splitlines(keepends=True):
            if current and current_len + len(line) > chunk_size:
                chunks.append("".join(current))
                current =[]
                current_len = 0

            if len(line) > chunk_size:
                if current:
                    chunks.append("".join(current))
                    current =[]
                    current_len = 0
                for i in range(0, len(line), chunk_size):
                    chunks.append(line[i:i + chunk_size])
                continue

            current.append(line)
            current_len += len(line)

        if current:
            chunks.append("".join(current))

        return chunks or [code]

    def _parse_ai_json(self, raw_text):
        raw_text = (raw_text or "").strip()
        if not raw_text:
            return None

        try:
            parsed = json.loads(raw_text)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        match = re.search(r"\{[\s\S]*\}", raw_text)
        if not match:
            return None

        try:
            parsed = json.loads(match.group())
        except Exception:
            return None

        return parsed if isinstance(parsed, dict) else None

    async def _fetch_prompt(self, session, url):
        async with session.get(url, timeout=10) as resp:
            if resp.status != 200:
                return None
            prompt = (await resp.text()).strip()
            return prompt or None

    async def _get_prompts(self, session):
        main_prompt = await self._fetch_prompt(session, "https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/assets/FSecurity/prompts/main.txt")
        chunk_prompt = await self._fetch_prompt(session, "https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/assets/FSecurity/prompts/chank.txt")
        final_prompt = await self._fetch_prompt(session, "https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/assets/FSecurity/prompts/final.txt")
        if not main_prompt or not chunk_prompt or not final_prompt:
            return None
        return {
            "main": main_prompt,
            "chunk": chunk_prompt,
            "final": final_prompt,
        }

    async def _nvidia_request(self, session, api_key, system_prompt, user_prompt):
        async with session.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "qwen/qwen3-coder-480b-a35b-instruct",
                "messages":[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.4,
                "max_tokens": 1000,
            },
            timeout=180,
        ) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            choices = data.get("choices") or[]
            if not choices:
                return None
            return self._parse_ai_json(choices[0].get("message", {}).get("content", ""))

    async def _local_ai_check(self, session, code, lang, api_key):
        prompts = await self._get_prompts(session)
        if not prompts:
            return None

        chunks = self._split_code(code)
        if len(chunks) == 1:
            prompt = self._render_prompt(prompts["main"], lang=lang)
            return await self._nvidia_request(
                session,
                api_key,
                prompt,
                f"Analyze this module:\n\n```python\n{code}\n```",
            )

        total = len(chunks)
        findings =[]

        for index, chunk in enumerate(chunks, start=1):
            previous_context = "; ".join(
                f"Part {i}: {finding}"
                for i, finding in enumerate(findings, start=1)
                if finding
            ) or "Previous parts: no issues found so far."

            chunk_prompt = self._render_prompt(
                prompts["chunk"],
                total=total,
                current=index,
                previous_context=previous_context,
                lang=lang,
            )
            chunk_result = await self._nvidia_request(
                session,
                api_key,
                chunk_prompt,
                f"Part {index}/{total}:\n\n```python\n{chunk}\n```",
            )
            if not chunk_result:
                return None

            chunk_verdict = str(chunk_result.get("chunk_verdict", "CLEAN")).lower()
            chunk_finding = str(chunk_result.get("findings", "") or "")

            if chunk_verdict == "blocked":
                findings_text = "\n".join(
                    f"- Part {i}: {finding}"
                    for i, finding in enumerate(findings, start=1)
                    if finding
                )
                if chunk_finding:
                    findings_text = f"{findings_text}\n- Part {index}: {chunk_finding}".strip()

                final_prompt = self._render_prompt(
                    prompts["final"],
                    total=total,
                    findings=findings_text or "No prior findings.",
                    lang=lang,
                )
                return await self._nvidia_request(
                    session,
                    api_key,
                    final_prompt,
                    "Give the final verdict based on all findings.",
                )

            findings.append(chunk_finding if chunk_verdict != "clean" else "")

        findings_text = "\n".join(
            f"- Part {i}: {finding}"
            for i, finding in enumerate(findings, start=1)
            if finding
        ) or "All parts: no issues found."

        final_prompt = self._render_prompt(
            prompts["final"],
            total=total,
            findings=findings_text,
            lang=lang,
        )
        return await self._nvidia_request(
            session,
            api_key,
            final_prompt,
            "Give the final verdict based on all findings.",
        )

    async def check(self, code):
        try:
            lang = self.strings("lang") or "en"
            module_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()

            db_cache = self.get("cache", {})
            if module_hash in db_cache:
                cached = db_cache[module_hash]
                if cached.get("level") == "safe":
                    return True
                return cached

            async with aiohttp.ClientSession() as session:
                api_keys = await self._get_api_keys(session)
                for api_key in api_keys:
                    parsed = await self._local_ai_check(session, code, lang, api_key)
                    if not isinstance(parsed, dict):
                        continue

                    verdict = str(parsed.get("verdict", "BLOCKED")).lower()
                    if verdict not in {"safe", "suspicious", "blocked"}:
                        verdict = "blocked"
                    summary = str(parsed.get("summary", "") or "")

                    result = {"level": verdict if verdict != "safe" else "safe"}
                    if verdict != "safe":
                        result["reason"] = summary

                    db_cache[module_hash] = result
                    self.set("cache", db_cache)

                    if result["level"] == "safe":
                        return True
                    return result

                return False
        except Exception:
            return False

    async def _get_api_keys(self, session):
        configured_key = self.config["nvidia_api_key"].strip()
        if configured_key:
            return [configured_key]

        try:
            async with session.get(
                "https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/assets/FSecurity/api_keys.txt",
                timeout=10,
            ) as resp:
                if resp.status != 200:
                    return[]
                raw_keys = (await resp.text()).strip()
        except Exception:
            return []

        return[key.strip() for key in raw_keys.split(",") if key.strip()]

    def format(self, state, reason="", link=""):
        link_part = f' (<code>{utils.escape_html(link)}</code>)' if link else ""
        if state == "unavailable":
            return f'<b>{self.strings("unavailable").format(link_part)}</b>\n<b>{self.strings("continue")}</b>'
        if state == "suspicious":
            return f'<b>{self.strings("suspicious").format(link_part)}</b>\n<blockquote expandable><b>{reason}</b></blockquote>\n<b>{self.strings("continue")}</b>'
        return f'<b>{self.strings("blocked").format(link_part)}</b>\n<blockquote expandable><b>{reason}</b></blockquote>'

    def buttons(self, task):
        return [[
            {"text": "✓", "callback": self.confirm, "args": (task, "yes")},
            {"text": "✗", "callback": self.confirm, "args": (task, "no")}
        ]]

    def closure_var(self, func, name):
        raw = getattr(func, "__func__", func)
        code = getattr(raw, "__code__", None)
        closure = getattr(raw, "__closure__", None)
        if not code or not closure or name not in code.co_freevars:
            return None

        with suppress(Exception):
            return closure[code.co_freevars.index(name)].cell_contents

        return None

    def restore_hooks(self):
        with suppress(Exception):
            inst_reg = getattr(self.modules, "register_module")
            owner = getattr(inst_reg, "__self__", None)
            if (
                owner
                and owner is not self
                and owner.__class__.__name__ == self.__class__.__name__
            ):
                original = getattr(owner, "oreg", None)
                if original:
                    if getattr(original, "__self__", None) is None:
                        self.modules.register_module = original.__get__(
                            self.modules,
                            self.modules.__class__,
                        )
                    else:
                        self.modules.register_module = original

        with suppress(Exception):
            inst_load = getattr(self.core, "load_module")
            raw = getattr(inst_load, "__func__", inst_load)
            if "FSecurity.patch.<locals>.load" in getattr(raw, "__qualname__", ""):
                original = self.closure_var(raw, "original")
                if original:
                    if getattr(original, "__self__", None) is None:
                        self.core.load_module = original.__get__(
                            self.core,
                            self.core.__class__,
                        )
                    else:
                        self.core.load_module = original

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

                try:
                    return await base(message, response, *a, **k)
                except Exception:
                    with suppress(Exception):
                        return await self._client.send_message(
                            utils.get_chat_id(message),
                            response,
                            reply_to=getattr(message, "reply_to_msg_id", None),
                            buttons=k.get("reply_markup"),
                        )

                    return message

            utils.answer = answer
            try:
                if getattr(original, "__self__", None) is None:
                    return await original(_, *args, **kwargs)
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
        is_dlm_lm = False

        while frame:
            locals = frame.f_locals
            if (
                frame.f_code.co_name == "load_module"
                and locals.get("self") is self.core
                and 'message' in locals
                and hasattr(locals['message'], 'edit')
            ):
                if not msg:
                    msg = locals['message']
                    fmsg = locals.get('msg')

            if frame.f_code.co_name in {"dlmod", "loadmod"}:
                is_dlm_lm = True
                if not msg and 'message' in locals and hasattr(locals['message'], 'edit'):
                    msg = locals['message']

            if frame.f_code.co_name == "download_and_install":
                if not msg and 'message' in locals and hasattr(locals['message'], 'edit'):
                    msg = locals['message']

            frame = frame.f_back

        return msg, fmsg, is_dlm_lm

    def target_chat(self, msg=None, fmsg=None):
        if not msg:
            return None

        if not fmsg:
            return msg

        with suppress(Exception):
            target = copy.copy(msg)
            target.reply_to_msg_id = fmsg.id
            return target

        return None

    async def call_oreg(self, spec, name, origin="<core>", save_fs=False):
        if getattr(self.oreg, "__self__", None) is None:
            return await self.oreg(self.modules, spec, name, origin, save_fs=save_fs)
        return await self.oreg(spec, name, origin, save_fs=save_fs)

    async def register(self, spec, name, origin="<core>", save_fs=False):
        if origin != "<core>":
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
                    msg, fmsg, is_dlm_lm = self.context()
                    target = self.target_chat(msg, fmsg)

                    if isinstance(check, dict):
                        status = check.get("level", "blocked")
                        reason = check.get("reason", "")
                    else:
                        status = "unavailable"
                        reason = ""

                    link = origin if origin.startswith("http") else ""

                    if status == "blocked":
                        if msg and target:
                            raise loader.LoadError(self.format("blocked", reason, link))
                        raise loader.LoadError("")

                    should_block = is_dlm_lm or self.config["strict_mode"]

                    if should_block and not (msg and target):
                        raise loader.LoadError("")

                    if should_block and msg and target:
                        task = str(uuid.uuid4())
                        event = asyncio.Event()
                        self.tasks[task] = {"event": event, "decision": False}

                        try:
                            form = await self.inline.form(
                                text=self.format(status, reason, link),
                                message=target,
                                reply_markup=self.buttons(task)
                            )

                            if not form:
                                raise loader.LoadError(reason)

                            await asyncio.wait_for(event.wait(), timeout=180.0)

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

        return await self.call_oreg(spec, name, origin, save_fs=save_fs)

    async def confirm(self, call, task, action):
        if task in self.tasks:
            self.tasks[task]["decision"] = (action == "yes")
            self.tasks[task]["event"].set()
        with suppress(Exception):
            await call.delete()
