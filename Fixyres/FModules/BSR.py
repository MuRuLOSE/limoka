__version__ = (1, 0, 0)

# ©️ Fixyres, 2026-2030
# 🌐 https://github.com/Fixyres/FModules
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# 🔑 http://www.apache.org/licenses/LICENSE-2.0

# meta banner: https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/assets/BSR/banner.png
# meta developer: @NFModules
# meta fhsdesc: brawlstars, game, funny

from .. import loader, utils
from urllib.parse import urlparse, parse_qs

async def extract_code(value: str) -> str:
    if value.startswith("http"):
        tags = parse_qs(urlparse(value).query).get("tag")
        return tags[0] if tags else value
    return value

async def to_id(code: str) -> int:
    code = code.strip().upper()
    if not code.startswith("X"):
        return 0
    val = 0
    for ch in code[1:]:
        i = "QWERTYUPASDFGHJKLZCVBNM23456789".find(ch)
        if i == -1:
            return 0
        val = val * 31 + i
    return val >> 8

async def to_code(n: int) -> str:
    if n < 0:
        return "X"
    n_shifted = n << 8
    res = []
    chars = "QWERTYUPASDFGHJKLZCVBNM23456789"
    while n_shifted > 0:
        res.append(chars[n_shifted % 31])
        n_shifted //= 31
    return "X" + "".join(reversed(res))


@loader.tds
class BSR(loader.Module):
    '''Module for finding nearby game rooms in BrawlStars.'''

    strings = {
        "name": "BSR",
        "invalid_args": "<b>Usage:</b> <code>{prefix}bsr (room code/link) (previous) (next)</code>",
        "invalid_code": "<b>Invalid room code!</b>",
        "at_least_one": "<b>At least one argument (previous or next) must be greater than 0!</b>",
        "prev_block": "<b>Previous:</b>\n<blockquote expandable>{prev_list}</blockquote>",
        "next_block": "<b>Next:</b>\n<blockquote expandable>{next_list}</blockquote>",
        "btn_target": "Target Room"
    }

    strings_ru = {
        "_cls_doc": "Модуль для поиска ближайших игровых комнат в BrawlStars.",
        "invalid_args": "<b>Использование:</b> <code>{prefix}bsr (код комнаты/ссылка) (предыдущие) (следующие)</code>",
        "invalid_code": "<b>Неверный код комнаты!</b>",
        "at_least_one": "<b>Хотя бы один аргумент (предыдущие или следующие) должен быть больше 0!</b>",
        "prev_block": "<b>Предыдущие:</b>\n<blockquote expandable>{prev_list}</blockquote>",
        "next_block": "<b>Следующие:</b>\n<blockquote expandable>{next_list}</blockquote>",
        "btn_target": "Целевая комната"
    }

    strings_ua = {
        "_cls_doc": "Модуль для пошуку найближчих ігрових кімнат у BrawlStars.",
        "invalid_args": "<b>Використання:</b> <code>{prefix}bsr (код кімнати/посилання) (попередні) (наступні)</code>",
        "invalid_code": "<b>Невірний код кімнати!</b>",
        "at_least_one": "<b>Хоча б один аргумент (попередні або наступні) повинен бути більшим за 0!</b>",
        "prev_block": "<b>Попередні:</b>\n<blockquote expandable>{prev_list}</blockquote>",
        "next_block": "<b>Наступні:</b>\n<blockquote expandable>{next_list}</blockquote>",
        "btn_target": "Цільова кімната"
    }

    strings_kz = {
        "_cls_doc": "BrawlStars ойынында жақын маңдағы ойын бөлмелерін табуға арналған модуль.",
        "invalid_args": "<b>Қолдану:</b> <code>{prefix}bsr (бөлме коды/сілтеме) (алдыңғы) (келесі)</code>",
        "invalid_code": "<b>Қате бөлме коды!</b>",
        "at_least_one": "<b>Кем дегенде бір аргумент (алдыңғы немесе келесі) 0-ден үлкен болуы керек!</b>",
        "prev_block": "<b>Алдыңғы:</b>\n<blockquote expandable>{prev_list}</blockquote>",
        "next_block": "<b>Келесі:</b>\n<blockquote expandable>{next_list}</blockquote>",
        "btn_target": "Мақсатты бөлме"
    }

    strings_uz = {
        "_cls_doc": "BrawlStars'da eng yaqin o'yin xonalarini topish uchun modul.",
        "invalid_args": "<b>Qo'llanilishi:</b> <code>{prefix}bsr (xona kodi/havolasi) (oldingi) (keyingi)</code>",
        "invalid_code": "<b>Noto'g'ri xona kodi!</b>",
        "at_least_one": "<b>Kamida bitta argument (oldingi yoki keyingi) 0 dan katta bo'lishi kerak!</b>",
        "prev_block": "<b>Oldingi:</b>\n<blockquote expandable>{prev_list}</blockquote>",
        "next_block": "<b>Keyingi:</b>\n<blockquote expandable>{next_list}</blockquote>",
        "btn_target": "Maqsadli xona"
    }

    strings_fr = {
        "_cls_doc": "Module pour trouver des salles de jeu à proximité dans BrawlStars.",
        "invalid_args": "<b>Utilisation:</b> <code>{prefix}bsr (code/lien) (précédents) (suivants)</code>",
        "invalid_code": "<b>Code de salle invalide!</b>",
        "at_least_one": "<b>Au moins un argument doit être supérieur à 0 !</b>",
        "prev_block": "<b>Précédents:</b>\n<blockquote expandable>{prev_list}</blockquote>",
        "next_block": "<b>Suivants:</b>\n<blockquote expandable>{next_list}</blockquote>",
        "btn_target": "Salle cible"
    }

    strings_de = {
        "_cls_doc": "Modul zum Finden von nahegelegenen Spielräumen in BrawlStars.",
        "invalid_args": "<b>Verwendung:</b> <code>{prefix}bsr (Raumcode/Link) (vorherige) (nächste)</code>",
        "invalid_code": "<b>Ungültiger Raumcode!</b>",
        "at_least_one": "<b>Mindestens ein argument muss größer als 0 sein!</b>",
        "prev_block": "<b>Vorherige:</b>\n<blockquote expandable>{prev_list}</blockquote>",
        "next_block": "<b>Nächste:</b>\n<blockquote expandable>{next_list}</blockquote>",
        "btn_target": "Zielraum"
    }

    strings_jp = {
        "_cls_doc": "BrawlStarsで近くのゲームルームを検索するためのモジュール。",
        "invalid_args": "<b>使用法:</b> <code>{prefix}bsr (コード/リンク) (前) (次)</code>",
        "invalid_code": "<b>無効なルームコード！</b>",
        "at_least_one": "<b>少なくとも1つの引数は0より大きくなければなりません！</b>",
        "prev_block": "<b>前:</b>\n<blockquote expandable>{prev_list}</blockquote>",
        "next_block": "<b>次:</b>\n<blockquote expandable>{next_list}</blockquote>",
        "btn_target": "ターゲットルーム"
    }

    @loader.command(
        ru_doc="(код комнаты/ссылка) (предыдущие) (следующие) - найти комнаты.",
        ua_doc="(код кімнати/посилання) (попередні) (наступні) - знайти кімнати.",
        kz_doc="(бөлме коды/сілтеме) (алдыңғы) (келесі) - бөлмелерді табу.",
        uz_doc="(xona kodi/havolasi) (oldingi) (keyingi) - xonalarni topish.",
        fr_doc="(code/lien) (précédents) (suivants) - trouver des salles.",
        de_doc="(Raumcode/Link) (vorherige) (nächste) - Räume finden.",
        jp_doc="(コード/リンク) (前) (次) - ルームを検索します。"
    )
    async def bsr(self, message):
        '''(room code/link) (previous) (next) - find rooms.'''
        args = utils.get_args_raw(message).split()
        if not args:
            return await utils.answer(message, self.strings["invalid_args"].format(prefix=self.get_prefix()))

        raw_input = args[0]
        before = 0
        nxt = 10

        if len(args) >= 2:
            try:
                before = int(args[1])
            except ValueError:
                pass
        
        if len(args) >= 3:
            try:
                nxt = int(args[2])
            except ValueError:
                pass

        before = max(0, min(before, 5000))
        nxt = max(0, min(nxt, 5000))

        if before == 0 and nxt == 0:
            return await utils.answer(message, self.strings["at_least_one"])

        clean_tag = await extract_code(raw_input)
        base_id = await to_id(clean_tag)

        if base_id == 0:
            return await utils.answer(message, self.strings["invalid_code"])

        text, page, total_pages = await self.get_page_content(base_id, before, nxt, 0)
        kb = self.build_keyboard(base_id, before, nxt, page, total_pages, clean_tag)

        await self.inline.form(
            message=message,
            text=text,
            photo="https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/assets/BSR/banner.png",
            reply_markup=kb
        )

    async def get_page_content(self, base_id: int, before: int, nxt: int, page: int):
        actual_before = min(before, base_id)
        total_pages = max(1, (actual_before + 9) // 10, (nxt + 9) // 10)
        
        if page < 0:
            page = total_pages - 1
        if page >= total_pages:
            page = 0
            
        start = page * 10
        
        prev_list = []
        for i in range(start + 1, min(start + 10, actual_before) + 1):
            c = await to_code(base_id - i)
            link = f'<a href="https://link.brawlstars.com/invite/gameroom/en?tag={c}">{c}</a>'
            prev_list.append(link)
            
        next_list = []
        for i in range(start + 1, min(start + 10, nxt) + 1):
            c = await to_code(base_id + i)
            link = f'<a href="https://link.brawlstars.com/invite/gameroom/en?tag={c}">{c}</a>'
            next_list.append(link)
        
        blocks = []
        
        if prev_list:
            blocks.append(self.strings["prev_block"].format(prev_list="\n".join(prev_list)))
            
        if next_list:
            blocks.append(self.strings["next_block"].format(next_list="\n".join(next_list)))
            
        res = "\n\n".join(blocks)
        if not res.strip():
            res = " "
            
        return res, page, total_pages

    def build_keyboard(self, base_id: int, before: int, nxt: int, page: int, total_pages: int, clean_tag: str):
        kb = [
            [
                {
                    "text": self.strings["btn_target"],
                    "copy": clean_tag
                }
            ]
        ]
        
        if total_pages > 1:
            nav_row = []
            if page > 0:
                nav_row.append({"text": "←", "callback": self.page_cb, "args": (base_id, before, nxt, page - 1, clean_tag)})
                
            nav_row.append({"text": f"{page + 1} / {total_pages}", "callback": self.dummy_cb, "args": ()})
            
            if page < total_pages - 1:
                nav_row.append({"text": "→", "callback": self.page_cb, "args": (base_id, before, nxt, page + 1, clean_tag)})
                
            kb.append(nav_row)
            
        return kb

    async def dummy_cb(self, call):
        await call.answer()

    async def page_cb(self, call, base_id: int, before: int, nxt: int, page: int, clean_tag: str):
        text, new_page, total_pages = await self.get_page_content(base_id, before, nxt, page)
        kb = self.build_keyboard(base_id, before, nxt, new_page, total_pages, clean_tag)
        
        await call.edit(
            text=text,
            photo="https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/assets/BSR/banner.png",
            reply_markup=kb
        )
