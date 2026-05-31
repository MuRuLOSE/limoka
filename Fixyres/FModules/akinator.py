__version__ = (1, 1, 0)

# ©️ Fixyres, 2026-2030
# 🌐 https://github.com/Fixyres/FModules
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# 🔑 http://www.apache.org/licenses/LICENSE-2.0

# meta banner: https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/assets/akinator/banner.png
# meta developer: @NFModules
# meta fhsdesc: game, funny, guess, question game

# requires: curl_cffi

import html
import re
import inspect
from curl_cffi import requests
from .. import loader, utils
from telethon.tl.functions.messages import TranslateTextRequest
from telethon.tl.types import TextWithEntities


class AsyncAki:
    def __init__(self, lang="en", cm=False):
        self.user_lang = lang
        aki_langs =[
            "en", "ar", "cn", "de", "es", "fr", "il", "it", 
            "jp", "kr", "nl", "pl", "pt", "ru", "tr", "id"
        ]
        
        if lang in aki_langs:
            self.aki_lang = lang
        elif lang in ["uk", "uz", "kk", "be"]:
            self.aki_lang = "ru"
        else:
            self.aki_lang = "en"
            
        self.cm = str(cm).lower()
        self.uri = f"https://{self.aki_lang}.akinator.com"
        
        self.session = requests.AsyncSession(impersonate="chrome120")
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        })
        
        self.win = False
        self.prog = "0.0"
        self.step = "0"
        self.slp = ""
        self.name = None
        self.desc = ""
        self.photo = "https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/assets/akinator/banner.png"
        self.q = ""

    async def _req(self, ep, data=None):
        method = "POST" if data else "GET"
        url = f"{self.uri}/{ep}"
        
        headers = {}
        if data:
            headers["x-requested-with"] = "XMLHttpRequest"
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        r = await self.session.request(method, url, data=data, headers=headers)
        
        if r.status_code != 200:
            raise Exception(f"AE{r.status_code}")
            
        try:
            return r.json()
        except Exception:
            return r.text
            
    async def start(self):
        t = await self._req("game", {"sid": 1, "cm": self.cm})
        
        if "technical problem" in (t if isinstance(t, str) else "").lower():
            raise Exception("ATP")

        ses_m = re.search(r"session['\"]\)\.val\(['\"](.+?)['\"]", t if isinstance(t, str) else str(t))
        sig_m = re.search(r"signature['\"]\)\.val\(['\"](.+?)['\"]", t if isinstance(t, str) else str(t))
        q_m = re.search(r'class="question-text".*?>(.+?)</p>', t if isinstance(t, str) else str(t), re.S)

        if not ses_m or not sig_m or not q_m:
            raise Exception("AECF")

        self.ses = ses_m.group(1)
        self.sig = sig_m.group(1)
        self.q = html.unescape(q_m.group(1)).strip()

    async def answer(self, a):
        data = {
            "step": self.step, "progression": self.prog, "sid": 1, 
            "cm": self.cm, "answer": a, "step_last_proposition": self.slp, 
            "session": self.ses, "signature": self.sig
        }
        res = await self._req("answer", data)
        self._upd(res)

    async def exclude(self):
        data = {
            "step": self.step, "progression": self.prog, "sid": 1, 
            "cm": self.cm, "session": self.ses, "signature": self.sig, 
            "forward_answer": "1"
        }
        try:
            res = await self._req("exclude", data)
            
            if isinstance(res, dict) and res.get("question"):
                self.win = False
                self.name = None
                self._upd(res)
            else:
                self.win = False
                self.name = None
                self.q = None
        except Exception:
            self.win, self.name, self.q = False, None, None

    def _upd(self, d):
        if not isinstance(d, dict): 
            return
        
        if d.get("id_proposition"):
            self.win = True
            self.name = html.unescape(d.get("name_proposition", ""))
            self.desc = html.unescape(d.get("description_proposition", ""))
            self.photo = d.get("photo", "https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/assets/akinator/banner.png")
            
            self.step = str(d.get("step", self.step))
            self.slp = self.step
            
            if "progression" in d and d["progression"] is not None:
                self.prog = str(d["progression"])
                
        elif d.get("question"):
            self.win = False
            self.q = html.unescape(d.get("question", ""))
            self.prog = str(d.get("progression", "0"))
            self.step = str(d.get("step", "0"))
            self.slp = str(d.get("step_last_proposition", self.slp))
        else:
            self.win = False
            self.name = None
            self.q = None

    async def close(self):
        try:
            if inspect.iscoroutinefunction(self.session.close):
                await self.session.close()
            else:
                res = self.session.close()
                if inspect.isawaitable(res):
                    await res
        except Exception:
            pass


@loader.tds
class Akinator(loader.Module):
    '''Akinator will guess any character you have in mind, you just need to answer a couple of questions.'''

    strings = {
        "name": "Akinator",
        "lang": "en",
        "child_mode": "Child mode. If enabled, it will be easier to guess 18+ heroes.",
        "start": "Start",
        "text": "<b>Guess any character you have in mind, and click on the Start button.</b>",
        "yes": "Yes",
        "no": "No",
        "idk": "I don't know",
        "probably": "Probably",
        "probably_not": "Probably not",
        "this_is": "<b>This is <code>{name}</code>\n<code>{description}</code></b>",
        "this_is_no_desc": "<b>This is <code>{name}</code></b>",
        "not_right": "Not right",
        "failed": "<b>Failed to guess the character.</b>"
    }
    
    strings_ru = {
        "lang": "ru",
        "_cls_doc": "Акинатор угадает любого вами загаданного персонажа.",
        "child_mode": "Детский режим. Сложнее отгадать 18+ героев.",
        "start": "Начать",
        "text": "<b>Задумайте персонажа, и нажмите начать.</b>",
        "yes": "Да",
        "no": "Нет",
        "idk": "Не знаю",
        "probably": "Возможно",
        "probably_not": "Скорее нет",
        "this_is": "<b>Это <code>{name}</code>\n<code>{description}</code></b>",
        "this_is_no_desc": "<b>Это <code>{name}</code></b>",
        "not_right": "Это не он",
        "failed": "<b>Не удалось угадать персонажа.</b>"
    }
    
    strings_ua = {
        "lang": "uk",
        "_cls_doc": "Акінатор вгадає будь-якого персонажа.",
        "child_mode": "Дитячий режим. Складніше відгадати 18+ героїв.",
        "start": "Почати",
        "text": "<b>Загадайте персонажа, і натисніть почати.</b>",
        "yes": "Так",
        "no": "Ні",
        "idk": "Не знаю",
        "probably": "Можливо",
        "probably_not": "Швидше ні",
        "this_is": "<b>Це <code>{name}</code>\n<code>{description}</code></b>",
        "this_is_no_desc": "<b>Це <code>{name}</code></b>",
        "not_right": "Це не він",
        "failed": "<b>Не вдалося вгадати персонажа.</b>"
    }

    strings_de = {
        "lang": "de",
        "_cls_doc": "Akinator errät jeden Charakter, den du dir vorstellst.",
        "child_mode": "Kindermodus. Wenn aktiviert, wird es schwieriger sein, 18+ Helden zu erraten.",
        "start": "Start",
        "text": "<b>Denk dir einen Charakter aus und klicke auf Start.</b>",
        "yes": "Ja",
        "no": "Nein",
        "idk": "Ich weiß nicht",
        "probably": "Wahrscheinlich",
        "probably_not": "Wahrscheinlich nicht",
        "this_is": "<b>Das ist <code>{name}</code>\n<code>{description}</code></b>",
        "this_is_no_desc": "<b>Das ist <code>{name}</code></b>",
        "not_right": "Das ist er nicht",
        "failed": "<b>Charakter konnte nicht erraten werden.</b>"
    }

    strings_fr = {
        "lang": "fr",
        "_cls_doc": "Akinator devinera n'importe quel personnage.",
        "child_mode": "Mode enfant. Héros 18+ plus difficiles à deviner.",
        "start": "Commencer",
        "text": "<b>Pensez à un personnage et cliquez sur Commencer.</b>",
        "yes": "Oui",
        "no": "Non",
        "idk": "Je ne sais pas",
        "probably": "Probablement",
        "probably_not": "Probablement pas",
        "this_is": "<b>C'est <code>{name}</code>\n<code>{description}</code></b>",
        "this_is_no_desc": "<b>C'est <code>{name}</code></b>",
        "not_right": "Ce n'est pas lui",
        "failed": "<b>Impossible de deviner.</b>"
    }

    strings_jp = {
        "lang": "ja",
        "_cls_doc": "アキネーターはあなたが考えているキャラクターを当てます。",
        "child_mode": "子供モード。有効にすると、18歳以上のキャラクターを推測するのが難しくなります。",
        "start": "開始",
        "text": "<b>キャラクターを思い浮かべて開始。</b>",
        "yes": "はい",
        "no": "いいえ",
        "idk": "わかりません",
        "probably": "おそらく",
        "probably_not": "おそらく違う",
        "this_is": "<b>これは <code>{name}</code>\n<code>{description}</code></b>",
        "this_is_no_desc": "<b>これは <code>{name}</code></b>",
        "not_right": "違います",
        "failed": "<b>推測できませんでした。</b>"
    }

    strings_uz = {
        "lang": "uz",
        "_cls_doc": "Akinator siz o'ylagan har qanday qahramonni topadi.",
        "child_mode": "Bolalar rejimi. Yoqilgan bo'lsa, 18+ qahramonlarni topish qiyinroq bo'ladi.",
        "start": "Boshlash",
        "text": "<b>Qahramonni o'ylang va Boshlash tugmasini bosing.</b>",
        "yes": "Ha",
        "no": "Yo'q",
        "idk": "Bilmayman",
        "probably": "Ehtimol",
        "probably_not": "Ehtimol yo'q",
        "this_is": "<b>Bu <code>{name}</code>\n<code>{description}</code></b>",
        "this_is_no_desc": "<b>Bu <code>{name}</code></b>",
        "not_right": "Bu u emas",
        "failed": "<b>Qahramonni topib bo'lmadi.</b>"
    }

    strings_kz = {
        "lang": "kk",
        "_cls_doc": "Акинатор сіз ойлаған кез келген кейіпкерді табады.",
        "child_mode": "Балалар режимі. Қосылған болса, 18+ кейіпкерлерді табу қиынырақ болады.",
        "start": "Бастау",
        "text": "<b>Кейіпкерді ойлаңыз және Бастау түймесін басыңыз.</b>",
        "yes": "Иә",
        "no": "Жоқ",
        "idk": "Білмеймін",
        "probably": "Мүмкін",
        "probably_not": "Мүмкін емес",
        "this_is": "<b>Бұл <code>{name}</code>\n<code>{description}</code></b>",
        "this_is_no_desc": "<b>Бұл <code>{name}</code></b>",
        "not_right": "Бұл ол емес",
        "failed": "<b>Кейіпкерді таба алмадық.</b>"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "child_mode",
                False,
                lambda: self.strings["child_mode"],
                validator=loader.validators.Boolean()
            )
        )
        self.games = {}

    async def _tr(self, client, text, to_lang):
        if not text: 
            return text
        try:
            request = TranslateTextRequest(
                to_lang=to_lang,
                text=[TextWithEntities(text=text, entities=[])]
            )
            result = await client(request)
            return result.result[0].text
        except Exception:
            return text

    @loader.command(
        ru_doc="- начать игру.",
        ua_doc="- почати гру.",
        de_doc="- Spiel starten.",
        fr_doc="- commencer le jeu.",
        jp_doc="- ゲームを開始します。",
        uz_doc="- o'yinni boshlash.",
        kz_doc="- ойынды бастау.",
    )
    async def akinator(self, message):
        '''- start the game.'''
        try:
            aki = AsyncAki(self.strings["lang"], self.config["child_mode"])
            await aki.start()
            
            self.games.setdefault(message.chat_id, {})[message.id] = aki
            
            await self.inline.form(
                text=self.strings["text"],
                message=message,
                photo="https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/assets/akinator/banner.png",
                reply_markup={
                    "text": self.strings["start"],
                    "callback": self._cb,
                    "args": (message,)
                }
            )
        except Exception as e:
            await utils.answer(message, f"<code>{e}</code>")

    async def _cb(self, call, message):
        aki = self.games.get(message.chat_id, {}).get(message.id)
        if aki:
            await self._sq(call, aki, message)

    async def _sq(self, call, aki, message):
        if aki.aki_lang != aki.user_lang:
            question = await self._tr(message.client, aki.q, aki.user_lang)
        else:
            question = aki.q
        
        markup = [[
                {"text": self.strings["yes"], "callback": self._ans, "args": (0, message)},
                {"text": self.strings["no"], "callback": self._ans, "args": (1, message)},
                {"text": self.strings["idk"], "callback": self._ans, "args": (2, message)}
            ],[
                {"text": self.strings["probably"], "callback": self._ans, "args": (3, message)},
                {"text": self.strings["probably_not"], "callback": self._ans, "args": (4, message)}
            ]
        ]
        
        await call.edit(
            f"<b>{question}</b>", 
            photo="https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/assets/akinator/banner.png", 
            reply_markup=markup
        )

    async def _show_guess(self, call, aki, message):
        if aki.aki_lang != aki.user_lang:
            name = await self._tr(message.client, aki.name, aki.user_lang)
            desc = await self._tr(message.client, aki.desc, aki.user_lang) if aki.desc else aki.desc
        else:
            name = aki.name
            desc = aki.desc
        
        if desc:
            text = self.strings["this_is"].format(name=name, description=desc)
        else:
            text = self.strings["this_is_no_desc"].format(name=name)
        
        markup = [[
                {"text": self.strings["yes"], "callback": self._fin, "args": (True, message, text, aki.photo)},
                {"text": self.strings["not_right"], "callback": self._rej, "args": (message,)}
            ]
        ]
        
        await call.edit(
            text, 
            photo=aki.photo, 
            reply_markup=markup
        )

    async def _ans(self, call, answer_id, message):
        aki = self.games.get(message.chat_id, {}).get(message.id)
        if not aki: 
            return
        
        await aki.answer(answer_id)
        
        if aki.win:
            await self._show_guess(call, aki, message)
        elif getattr(aki, 'q', None):
            await self._sq(call, aki, message)
        else:
            await self._fin(call, False, message, "", "")

    async def _rej(self, call, message):
        aki = self.games.get(message.chat_id, {}).get(message.id)
        if not aki: 
            return
     
        try: 
            await aki.exclude()
        except Exception: 
            pass
            
        if aki.win:
            await self._show_guess(call, aki, message)
        elif getattr(aki, 'q', None):
            await self._sq(call, aki, message)
        else:
            await self._fin(call, False, message, "", "")

    async def _fin(self, call, won, message, text, photo):
        aki = self.games.get(message.chat_id, {}).pop(message.id, None)
        
        if aki: 
            await aki.close()
            
        if won: 
            await call.edit(text, photo=photo, reply_markup=[])
        else: 
            await call.edit(
                self.strings["failed"],
                photo="https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/assets/akinator/idk.png",
                reply_markup=[]
        )
