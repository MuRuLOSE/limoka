__version__ = (9, 4, 0)

# meta developer: @NFModules
# meta pic: https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/assets/FHeta/logo.png
# meta banner: https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/assets/FHeta/logo.png
# scope: hikka_min 2.1.0

# ©️ Fixyres, 2024-2030
# 🌐 https://github.com/Fixyres/FModules
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 🔑 http://www.apache.org/licenses/LICENSE-2.0

import asyncio
import aiohttp
import re
import uuid
import inspect
import logging
from typing import Optional, Dict, List, Union, Tuple, Any
from urllib.parse import unquote

import telethon
from .. import loader, utils
from herokutl.tl.functions.contacts import UnblockRequest


class FHetaAPI:
    def __init__(self) -> None:
        self.token: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None

    async def connect(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def fetch(self, path: str, **params: Any) -> Dict[str, Any]:
        session = await self.connect()
        try:
            async with session.get(
                f"https://api.fixyres.com/{path}",
                params=params,
                headers={"Authorization": self.token},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    return await response.json()
                return {}
        except Exception:
            return {}

    async def send(self, path: str, payload: Optional[Dict[str, Any]] = None, **params: Any) -> Dict[str, Any]:
        session = await self.connect()
        try:
            async with session.post(
                f"https://api.fixyres.com/{path}",
                json=payload,
                params=params,
                headers={"Authorization": self.token},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    return await response.json()
                return {}
        except Exception:
            return {}


class FHetaUI:
    def __init__(self, main: 'FHeta') -> None:
        self.main = main

    def emoji(self, key: str) -> str:
        return self.main.THEMES[self.main.config["theme"]][key]

    def format(self, data: Dict[str, Any], query: str = "", index: int = 1, total: int = 1, inline: bool = False) -> str:
        version = data.get("version", "?.?.?")
        limit = 3700
        name = utils.escape_html(data.get("name", ""))
        author = utils.escape_html(data.get("author", "???"))
        
        text = f"{self.emoji('module')} <code>{name}</code> <b>{self.main.strings['author']}</b> <code>{author}</code>"
        if version != "?.?.?":
            text += f" (<code>v{version}</code>)"

        description = data.get("description")
        if description:
            if isinstance(description, dict):
                string = description.get(self.main.strings["lang"]) or description.get("doc") or next(iter(description.values()), "")
            else:
                string = description
            text += f"\n\n{self.emoji('description')} <b>{self.main.strings['description']}:</b>\n<blockquote expandable>{utils.escape_html(str(string))}</blockquote>"

        text += self.render(data.get("commands", []), "cmd", limit - len(re.sub(r'<[^>]+>', '', text)))
        text += self.render(data.get("placeholders", []), "ph", limit - len(re.sub(r'<[^>]+>', '', text)))
        
        return text

    def render(self, items: List[Dict[str, Any]], kind: str, limit: int) -> str:
        if not items:
            return ""
            
        lines = []
        language = self.main.strings["lang"]
        
        title = "commands" if kind == "cmd" else "placeholders"
        more = "morecommands" if kind == "cmd" else "moreplaceholders"
        
        for index, item in enumerate(items):
            description = item.get("description", {})
            if isinstance(description, dict):
                description = description.get(language) or description.get("doc") or ""
            
            description = utils.escape_html(description).split('\n')[0] if description else ""
            name = utils.escape_html(item.get("name", ""))
            
            if item.get('inline'):
                character = '@' + self.main.inline.bot_username + ' '
                display_name = name
            elif kind == "ph":
                character = ""
                display_name = f"{{{name}}}"
            else:
                character = self.main.get_prefix()
                display_name = name
                
            row = f"<code>{character}{display_name}</code> {description}".strip()
            
            extra = f"<i>{self.main.strings[more].format(remaining=len(items) - index)}</i>"
            test = "\n".join(lines + [row, extra])
            
            if len(re.sub(r'<[^>]+>', '', test)) > limit and index > 0:
                lines.append(extra)
                break
                
            lines.append(row)
            
        return f"\n\n{self.emoji('command' if kind == 'cmd' else 'placeholder')} <b>{self.main.strings[title]}:</b>\n<blockquote expandable>{chr(10).join(lines)}</blockquote>"

    def buttons(self, link: str, stats: Dict[str, Any], index: int, modules: Optional[List[Dict[str, Any]]] = None, query: str = "") -> List[List[Dict[str, Any]]]:
        buttons = []
        decoded = unquote(link.replace('%20', '___SPACE___')).replace('___SPACE___', '%20')
        url = decoded[4:] if decoded.startswith('dlm ') else decoded
        
        if query:
            buttons.append([
                {"text": self.main.strings["query"], "copy": query},
                {"text": self.main.strings["install"], "callback": self.main.install, "args": (url, index, modules, query)},
                {"text": self.main.strings["code"], "url": url}
            ])
            
        buttons.append([
            {"text": f"↑ {stats.get('likes', 0)}", "callback": self.main.rate, "args": (link, "like", index, modules, query)},
            {"text": f"↓ {stats.get('dislikes', 0)}", "callback": self.main.rate, "args": (link, "dislike", index, modules, query)}
        ])
        
        if modules and len(modules) > 1:
            count = {"text": self.main.strings["counter"].format(idx=index+1, total=len(modules)), "callback": self.main.show, "args": (index, modules, query)}
            buttons[-1].insert(1, count)
            
            navigation = []
            if index > 0:
                navigation.append({"text": "←", "callback": self.main.navigate, "args": (index - 1, modules, query)})
            if index < len(modules) - 1:
                navigation.append({"text": "→", "callback": self.main.navigate, "args": (index + 1, modules, query)})
                
            if navigation:
                buttons.append(navigation)
                
        return buttons

    def pagination(self, modules: List[Dict[str, Any]], query: str, page: int = 0, current: int = 0) -> List[List[Dict[str, Any]]]:
        buttons = []
        start = page * 8
        end = min(start + 8, len(modules))
        
        for index in range(start, end):
            name = modules[index].get('name', 'Unknown')
            author = modules[index].get('author', '???')
            buttons.append([
                {"text": f"{index + 1}. {name} by {author}", "callback": self.main.navigate, "args": (index, modules, query)}
            ])
            
        navigation = []
        if page > 0:
            navigation.append({"text": "←", "callback": self.main.page, "args": (page - 1, modules, query, current)})
        if page < (len(modules) + 7) // 8 - 1:
            navigation.append({"text": "→", "callback": self.main.page, "args": (page + 1, modules, query, current)})
            
        if navigation:
            buttons.append(navigation)
            
        buttons.append([{"text": "✘", "callback": self.main.navigate, "args": (current, modules, query)}])
        return buttons


@loader.tds
class FHeta(loader.Module):
    '''Module for searching modules! Watch all FHeta news in @NFHeta_Updates!'''

    strings = {
        "name": "FHeta",
        "lang": "en",
        "author": "by",
        "description": "Description",
        "commands": "Commands",
        "placeholders": "Placeholders",
        "morecommands": "...and {remaining} more commands.",
        "moreplaceholders": "...and {remaining} more placeholders.",
        "list": "All found modules:",
        "search": "Searching for {query}...",
        "noquery": "You didn't enter a search query, example: {prefix}fheta your query",
        "notfound": "Nothing found for query {query}.",
        "toolong": "Your query is too big, please try reducing it to 168 characters.",
        "added": "✔ Rating submitted!",
        "changed": "✔ Rating has been changed!",
        "deleted": "✔ Rating deleted!",
        "prompt": "Enter a query to search.",
        "hint": "Name, command, description, author.",
        "retry": "Try another query.",
        "query": "Query",
        "install": "Install",
        "counter": "{idx}/{total}",
        "code": "Code",
        "success": "✔ Module successfully installed!",
        "error": "✘ Error, perhaps the module is broken!",
        "overwrite": "✘ Error, module tried to overwrite built-in module!",
        "dependency": "✘ Dependencies installation error!",
        "docdevs": "Use only modules from official Heroku developers when searching?",
        "doctheme": "Theme for emojis.",
        "channel": "This is the channel with all updates in FHeta!",
        "install_via_fheta": "Enable Install via FHeta?"
    }
    
    strings_ru = {
        "_cls_doc": "Модуль для поиска модулей! Следите за всеми новостями FHeta в @NFHeta_Updates!",
        "lang": "ru",
        "author": "от",
        "description": "Описание",
        "commands": "Команды",
        "placeholders": "Плейсхолдеры",
        "morecommands": "...и еще {remaining} команд.",
        "moreplaceholders": "...и еще {remaining} плейсхолдеров.",
        "list": "Все найденные модули:",
        "search": "Поиск по запросу {query}...",
        "noquery": "Вы не ввели запрос для поиска, пример: {prefix}fheta ваш запрос",
        "notfound": "Ничего не найдено по запросу {query}.",
        "toolong": "Ваш запрос слишком большой, пожалуйста, сократите его до 168 символов.",
        "added": "✔ Оценка добавлена!",
        "changed": "✔ Оценка изменена!",
        "deleted": "✔ Оценка удалена!",
        "prompt": "Введите запрос для поиска.",
        "hint": "Название, команда, описание, автор.",
        "retry": "Попробуйте другой запрос.",
        "query": "Запрос",
        "install": "Установить",
        "counter": "{idx}/{total}",
        "code": "Код",
        "success": "✔ Модуль успешно установлен!",
        "error": "✘ Ошибка, возможно, модуль сломан!",
        "overwrite": "✘ Ошибка, модуль пытался перезаписать встроенный модуль!",
        "dependency": "✘ Ошибка установки зависимостей!",
        "docdevs": "Использовать только модули от официальных разработчиков Heroku при поиске?",
        "doctheme": "Тема для эмодзи.",
        "channel": "Это канал со всеми обновлениями в FHeta!",
        "install_via_fheta": "Включить Install via FHeta?"
    }
    
    strings_ua = {
        "_cls_doc": "Модуль для пошуку модулів! Слідкуйте за всіма новинами FHeta в @NFHeta_Updates!",
        "lang": "ua",
        "author": "від",
        "description": "Опис",
        "commands": "Команды",
        "placeholders": "Плейсхолдери",
        "morecommands": "...і ще {remaining} команд.",
        "moreplaceholders": "...і ще {remaining} плейсхолдерів.",
        "list": "Всі знайдені модули:",
        "search": "Пошук за запитом {query}...",
        "noquery": "Ви не ввели запит для пошуку, приклад: {prefix}fheta ваш запит",
        "notfound": "Нічого не знайдено за запитом {query}.",
        "toolong": "Ваш запит занадто великий, будь ласка, скоротіть його до 168 символів.",
        "added": "✔ Оцінку додано!",
        "changed": "✔ Оцінку змінено!",
        "deleted": "✔ Оцінку видалено!",
        "prompt": "Введіть запит для пошуку.",
        "hint": "Назва, команда, опис, автор.",
        "retry": "Спробуйте інший запит.",
        "query": "Запит",
        "install": "Встановити",
        "counter": "{idx}/{total}",
        "code": "Код",
        "success": "✔ Модуль успішно встановлено!",
        "error": "✘ Помилка, можливо, модуль поламаний!",
        "overwrite": "✘ Помилка, модуль намагався перезаписати вбудований модуль!",
        "dependency": "✘ Помилка встановлення залежностей!",
        "docdevs": "Використовувати тільки модулі від офіційних розробників Heroku при пошуку?",
        "doctheme": "Тема для емодзі.",
        "channel": "Це канал з усіма оновленнями в FHeta!",
        "install_via_fheta": "Увімкнути Install via FHeta?"
    }
    
    strings_kz = {
        "_cls_doc": "Модульдерді іздеу модулі! FHeta барлық жаңалықтарын @NFHeta_Updates арнасында қадағалаңыз!",
        "lang": "kz",
        "author": "авторы",
        "description": "Сипаттама",
        "commands": "Командалар",
        "placeholders": "Плейсхолдерлер",
        "morecommands": "...және тағы {remaining} команда.",
        "moreplaceholders": "...және тағы {remaining} плейсхолдер.",
        "list": "Барлық табылған модульдер:",
        "search": "{query} сұрауы бойынша іздеу...",
        "noquery": "Сіз іздеу сұрауын енгізбедіңіз, мысал: {prefix}fheta сіздің сұрауыңыз",
        "notfound": "{query} сұрауы бойынша ештеңе табылмады.",
        "toolong": "Сіздің сұрауыңыз тым үлкен, оны 168 таңбаға до қысқартыңыз.",
        "added": "✔ Бағалау қосылды!",
        "changed": "✔ Бағалау өзгертілді!",
        "deleted": "✔ Бағалау жойылды!",
        "prompt": "Іздеу үшін сұрау енгізіңіз.",
        "hint": "Атауы, команда, сипаттама, автор.",
        "retry": "Басқа сұрауды қолданып көріңіз.",
        "query": "Сұрау",
        "install": "Орнату",
        "counter": "{idx}/{total}",
        "code": "Код",
        "success": "✔ Модуль сәтті орнатылды!",
        "error": "✘ Қате, мүмкін модуль бұзылған!",
        "overwrite": "✘ Қате, модуль кіріктірілген модульді қайта жазуға тырысты!",
        "dependency": "✘ Тәуелділіктерді орнату қатесі!",
        "docdevs": "Іздеу кезінде тек ресми Heroku әзірлеушілерінің модульдерін пайдалану керек пе?",
        "doctheme": "Эмодзилер үшін тақырып.",
        "channel": "Бұл FHeta-дағы барлық жаңартулары бар арна!",
        "install_via_fheta": "Install via FHeta қосу керек пе?"
    }
    
    strings_uz = {
        "_cls_doc": "Modullarni qidirish moduli! FHeta barcha yangilanishlarini @NFHeta_Updates kanalida kuzatib boring!",
        "lang": "uz",
        "author": "muallif",
        "description": "Tavsif",
        "commands": "Buyruqlar",
        "placeholders": "Pleysholderlar",
        "morecommands": "...va yana {remaining} ta buyruq.",
        "moreplaceholders": "...va yana {remaining} ta pleysholder.",
        "list": "Barcha topilgan modullar:",
        "search": "{query} so'rovi bo'yicha qidiruv...",
        "noquery": "Siz qidiruv so'rovini kiritmadingiz, misol: {prefix}fheta sizning sorovingiz",
        "notfound": "{query} so'rovi bo'yicha hech narsa topilmadi.",
        "toolong": "Sizning so'rovingiz juda katta, iltimos uni 168 belgigacha qisqartiring.",
        "added": "✔ Reyting qo'shildi!",
        "changed": "✔ Reyting o'zgartirildi!",
        "deleted": "✔ Reyting o'chirildi!",
        "prompt": "Qidirish o'rniga so'rov kiritish.",
        "hint": "Nomi, buyruq, tavsif, muallif.",
        "retry": "Boshqa so'rovni sinab ko'ring.",
        "query": "So'rov",
        "install": "O'rnatish",
        "counter": "{idx}/{total}",
        "code": "Kod",
        "success": "✔ Modul muvaffaqiyatli o'rnatildi!",
        "error": "✘ Xatolik, ehtimol modul buzilgan!",
        "overwrite": "✘ Xatolik, modul o'rnatilgan modulni qayta yozishga harakat qildi!",
        "dependency": "✘ Bog'liqliklarni o'rnatish xatosi!",
        "docdevs": "Qidiruv paytida faqat rasmiy Heroku ishlab chiquvchilarining modullaridan foydalanish kerakmi?",
        "doctheme": "Emojilar uchun mavзу.",
        "channel": "Bu FHeta-dagi barcha yangilanishlari bo'lgan kanal!",
        "install_via_fheta": "Install via FHeta yoqilsinmi?"
    }
    
    strings_fr = {
        "_cls_doc": "Module de recherche de modules! Suivez toutes les actualités FHeta sur @NFHeta_Updates!",
        "lang": "fr",
        "author": "par",
        "description": "Description",
        "commands": "Commandes",
        "placeholders": "Espaces réservés",
        "morecommands": "...et {remaining} commandes supplémentaires.",
        "moreplaceholders": "...et {remaining} espaces réservés supplémentaires.",
        "list": "Tous les modules trouvés:",
        "search": "Recherche pour {query}...",
        "noquery": "Vous n'avez pas entré de requête de recherche, exemple: {prefix}fheta votre requête",
        "notfound": "Rien trouvé for query {query}.",
        "toolong": "Votre requête est too long, please try reducing it to 168 characters.",
        "added": "✔ Note ajoutée!",
        "changed": "✔ Note modifiée!",
        "deleted": "✔ Note supprimée!",
        "prompt": "Entrez une requête pour rechercher.",
        "hint": "Nom, commande, description, auteur.",
        "retry": "Essayez une autre requête.",
        "query": "Requête",
        "install": "Installer",
        "counter": "{idx}/{total}",
        "code": "Code",
        "success": "✔ Module installé com succès!",
        "error": "✘ Erreur, le module est peut-être cassé!",
        "overwrite": "✘ Erreur, le module a tenté d'écraser le module intégré!",
        "dependency": "✘ Erreur d'installation des dépendances!",
        "docdevs": "Utiliser uniquement les modules des développeurs Heroku officiels lors de la recherche?",
        "doctheme": "Thème pour les emojis.",
        "channel": "Voici le canal avec toutes les mises à jour dans FHeta!",
        "install_via_fheta": "Activer Install via FHeta ?"
    }
    
    strings_de = {
        "_cls_doc": "Modul zur Suche nach Modulen! Verfolgen Sie alle FHeta-Neuigkeiten auf @NFHeta_Updates!",
        "lang": "de",
        "author": "von",
        "description": "Beschreibung",
        "commands": "Befehle",
        "placeholders": "Platzhalter",
        "morecommands": "...und {remaining} weitere Befehle.",
        "moreplaceholders": "...und {remaining} weitere Platzhalter.",
        "list": "Alle gefundenen Module:",
        "search": "Suche nach {query}...",
        "noquery": "Sie haben keine Suchanfrage eingegeben, Beispiel: {prefix}fheta ihre anfrage",
        "notfound": "Nichts gefunden für Anfrage {query}.",
        "toolong": "Ihre Anfrage ist zu groß, bitte reduzieren Sie sie auf 168 Zeichen.",
        "added": "✔ Bewertung hinzugefügt!",
        "changed": "✔ Bewertung geändert!",
        "deleted": "✔ Bewertung gelöscht!",
        "prompt": "Geben Sie eine Suchanfrage ein.",
        "hint": "Name, Befehl, Beschreibung, Autor.",
        "retry": "Versuchen Sie eine другая запрос.",
        "query": "Anfrage",
        "install": "Installieren",
        "counter": "{idx}/{total}",
        "code": "Code",
        "success": "✔ Modul erfolgreich installiert!",
        "error": "✘ Fehler, vielleicht ist das Modul kaputt!",
        "overwrite": "✘ Fehler, Modul hat versucht, das integrierte Modul zu überschreiben!",
        "dependency": "✘ Fehler bei der Installation von Abhängigkeiten!",
        "docdevs": "Nur Module von offiziellen Heroku-Entwicklern bei की खोज में उपयोग करें?",
        "doctheme": "Theма für эмодзи.",
        "channel": "Dies ist der Kanal with all updates in FHeta!",
        "install_via_fheta": "Install via FHeta aktivieren?"
    }
    
    strings_jp = {
        "_cls_doc": "モジュール検索用モジュール！@NFHeta_UpdatesでFHetaのすべてのニュースをフォローしてください！",
        "lang": "jp",
        "author": "作成者",
        "description": "説明",
        "commands": "コマンド",
        "placeholders": "プレースホルダー",
        "morecommands": "...さらに {remaining} 個のコマンド。",
        "moreplaceholders": "...さらに {remaining} 個のプレースホルダー。",
        "list": "見つかったすべてのモジュール:",
        "search": "{query}を検索中...",
        "noquery": "検索クエリを入力していません、例: {prefix}fheta あなたのクエリ",
        "notfound": "クエリ{query}で何も見つかりませんでした。",
        "toolong": "クエリが大きすぎます。168文字に短縮してください。",
        "added": "✔ 評価が追加されました！",
        "changed": "✔ 評価が変更されました！",
        "deleted": "✔ 評価が削除されました！",
        "prompt": "検索するクエリを入力してください。",
        "hint": "名前、コマンド、説明、作成者。",
        "retry": "別のクエリを試してください。",
        "query": "クエリ",
        "install": "インストール",
        "counter": "{idx}/{total}",
        "code": "コード",
        "success": "✔ モジュールが正常にインストールされました!",
        "error": "✘ エラー, モジュールが壊れている可能性があります!",
        "overwrite": "✘ エラー, モジュールが組み込みモジュールを上書きしようとしました!",
        "dependency": "✘ 依存関係のインストールエラー!",
        "docdevs": "検索時に公式Heroku開発者のモジュールのみを使用しますか？",
        "doctheme": "絵文字のテーマ。",
        "channel": "これはFHetaのすべての更新を含むチャンネルです！",
        "install_via_fheta": "Install via FHetaを有効にしますか？"
    }
    
    THEMES = {
        "default": {
            "search": '<tg-emoji emoji-id="5188217332748527444">🔍</tg-emoji>',
            "error": '<tg-emoji emoji-id="5465665476971471368">❌</tg-emoji>',
            "warn": '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji>',
            "description": '<tg-emoji emoji-id="5334882760735598374">📝</tg-emoji>',
            "command": '<tg-emoji emoji-id="5341715473882955310">⚙️</tg-emoji>',
            "placeholder": '<tg-emoji emoji-id="5359785904535774578">🗒️</tg-emoji>',
            "module": '<tg-emoji emoji-id="5454112830989025752">📦</tg-emoji>',
            "channel": '📢',
            "modules_list": '<tg-emoji emoji-id="5197269100878907942">📋</tg-emoji>'
        },
        "winter": {
            "search": '<tg-emoji emoji-id="5431895003821513760">❄️</tg-emoji>',
            "error": '<tg-emoji emoji-id="5404728536810398694">🧊</tg-emoji>',
            "warn": '<tg-emoji emoji-id="5447644880824181073">🌨️</tg-emoji>',
            "description": '<tg-emoji emoji-id="5255850496291259327">📜</tg-emoji>',
            "command": '<tg-emoji emoji-id="5199503707938505333">🎅</tg-emoji>',
            "placeholder": '<tg-emoji emoji-id="5204046675236109418">🗒️</tg-emoji>',
            "module": '<tg-emoji emoji-id="5197708768091061888">🎁</tg-emoji>',
            "channel": '📢',
            "modules_list": '<tg-emoji emoji-id="5345935030143196497">🎄</tg-emoji>'
        },
        "summer": {
            "search": '<tg-emoji emoji-id="5188217332748527444">🔍</tg-emoji>',
            "error": '<tg-emoji emoji-id="5470049770997292425">🌡️</tg-emoji>',
            "warn": '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji>',
            "description": '<tg-emoji emoji-id="5361684086807076580">🍹</tg-emoji>',
            "command": '<tg-emoji emoji-id="5442644589703866634">🏄</tg-emoji>',
            "placeholder": '<tg-emoji emoji-id="5434121252874756456">🗒️</tg-emoji>',
            "module": '<tg-emoji emoji-id="5433645645376264953">🏖️</tg-emoji>',
            "channel": '📢',
            "modules_list": '<tg-emoji emoji-id="5472178859300363509">🏖️</tg-emoji>'
        },
        "spring": {
            "search": '<tg-emoji emoji-id="5449885771420934013">🌱</tg-emoji>',
            "error": '<tg-emoji emoji-id="5208923808169222461">🥀</tg-emoji>',
            "warn": '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji>',
            "description": '<tg-emoji emoji-id="5251524493561569780">🍃</tg-emoji>',
            "command": '<tg-emoji emoji-id="5449850741667668411">🦋</tg-emoji>',
            "placeholder": '<tg-emoji emoji-id="5434121252874756456">🗒️</tg-emoji>',
            "module": '<tg-emoji emoji-id="5440911110838425969">🌿</tg-emoji>',
            "channel": '📢',
            "modules_list": '<tg-emoji emoji-id="5440748683765227563">🌺</tg-emoji>'
        },
        "autumn": {
            "search": '<tg-emoji emoji-id="5253944419870062295">🍂</tg-emoji>',
            "error": '<tg-emoji emoji-id="5281026503658728615">🍁</tg-emoji>',
            "warn": '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji>',
            "description": '<tg-emoji emoji-id="5406631276042002796">📜</tg-emoji>',
            "command": '<tg-emoji emoji-id="5212963577098417551">🍂</tg-emoji>',
            "placeholder": '<tg-emoji emoji-id="5363965354391388799">🗒️</tg-emoji>',
            "module": '<tg-emoji emoji-id="5249157915041865558">🍄</tg-emoji>',
            "channel": '📢',
            "modules_list": '<tg-emoji emoji-id="5305495722618010655">🍂</tg-emoji>'
        }
    }
    
    def __init__(self) -> None:
        self.fheta_cache: Dict[str, Dict[str, Any]] = {}
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "only_official_developers",
                False,
                lambda: self.strings["docdevs"],
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "install_via_fheta",
                True,
                lambda: self.strings["install_via_fheta"],
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "theme",
                "default",
                lambda: self.strings["doctheme"],
                validator=loader.validators.Choice(["default", "winter", "summer", "spring", "autumn"])
            )
        )
    
    async def on_unload(self) -> None:
        if hasattr(self, "api") and self.api.session and not self.api.session.closed:
            await self.api.session.close()
        if hasattr(self, "inline") and hasattr(self.inline, "unregister_bot_update_handler"):
            self.inline.unregister_bot_update_handler("fheta_chosen")
            
    async def client_ready(self, client: 'telethon.TelegramClient', database: 'loader.Database') -> None:
        await client(UnblockRequest("@FHeta_robot"))
        await utils.dnd(client, "@FHeta_robot", archive=True)
        
        self.identifier = (await client.get_me()).id
        self.token = database.get("FHeta", "token")
        
        self.api = FHetaAPI()
        self.ui = FHetaUI(self)
        
        await self.request_join(
            "NFHeta_Updates",
            f"{self.ui.emoji('channel')} {self.strings['channel']}"
        )
        
        self.api.token = self.token

        self.fheta_cache: Dict[str, Dict[str, Any]] = {}

        if hasattr(self.inline, "register_bot_update_handler"):
            async def fheta_chosen(event: Any) -> None:
                if isinstance(event, telethon.tl.types.UpdateBotInlineSend) and getattr(event, "id", "").startswith("fh_"):
                    await self.chosen(event)
            self.inline.register_bot_update_handler("fheta_chosen", "chosen_inline_result", fheta_chosen)

        if self.token and not await self.api.fetch("validatetkn", user_id=str(self.identifier)):
            self.token = None
            self.api.token = None
        
        if not self.token:
            async with client.conversation("@FHeta_robot") as conversation:
                await conversation.send_message('/token')
                self.token = (await conversation.get_response(timeout=5)).text.strip()
                database.set("FHeta", "token", self.token)
                self.api.token = self.token

    @loader.loop(interval=1, autostart=True)
    async def sync_loop(self):
        cl = self.strings["lang"]
        if cl != getattr(self, "_last_lang", None):
            await self.api.send("dataset", user_id=self.identifier, lang=cl)
            self._last_lang = cl

    async def answer(self, callback: Any, text: Optional[str] = None, alert: bool = False) -> None:
        if not hasattr(callback, "answer"):
            return
        await callback.answer(text=text or "", show_alert=alert)

    async def edit(self, target: Any, text: str, buttons: List[List[Dict[str, Any]]], banner: Optional[str] = None) -> None:
        markup = self.inline.generate_markup(buttons)

        if banner and banner not in text:
            text = f'<a href="{banner}">&#8204;</a>' + text
        
        inline_msg_id = target.inline_message_id if hasattr(target, "inline_message_id") else None

        await self.inline.bot.edit_message(
            inline_msg_id or target.chat_id,
            None if inline_msg_id else target.message_id,
            text,
            parse_mode="HTML",
            buttons=markup,
            link_preview=banner is not None,
            invert_media=banner is not None
        )

    async def chosen(self, event: Any) -> None:
        parts = getattr(event, "id", "").split("_")
        if len(parts) != 3:
            return
        queryid, index = parts[1], int(parts[2])
        saved = self.fheta_cache.get(queryid)
        if not saved:
            return
        query = saved.get("query", "")
        modules = saved.get("mods", [])
        if not modules or index >= len(modules):
            return
        data = modules[index]
        text = self.ui.format(data, query, 1, 1, True)
        buttons = self.ui.buttons(data.get("install", ""), data, 0, [data], query)
        banner = data.get("banner")
        if banner and banner not in text:
            text = f'<a href="{banner}">&#8204;</a>' + text
        await self.inline.bot.edit_message(
            event.msg_id,
            None,
            text,
            parse_mode="HTML",
            buttons=self.inline.generate_markup(buttons),
            link_preview=banner is not None,
            invert_media=banner is not None
        )

    async def show(self, callback: Any, index: int, modules: List[Dict[str, Any]], query: str) -> None:
        await self.answer(callback)
        text = f"{self.ui.emoji('modules_list')} <b>{self.strings['list']}</b>"
        await self.edit(callback, text, self.ui.pagination(modules, query, 0, index))

    async def page(self, callback: Any, current: int, modules: List[Dict[str, Any]], query: str, index: int) -> None:
        await self.answer(callback)
        text = f"{self.ui.emoji('modules_list')} <b>{self.strings['list']}</b>"
        await self.edit(callback, text, self.ui.pagination(modules, query, current, index))

    async def navigate(self, callback: Any, index: int, modules: List[Dict[str, Any]], query: str = "") -> None:
        await self.answer(callback)
        if 0 <= index < len(modules):
            data = modules[index]
            text = self.ui.format(data, query, index + 1, len(modules))
            buttons = self.ui.buttons(data.get('install', ''), data, index, modules, query)
            await self.edit(callback, text, buttons, data.get("banner"))

    async def rate(self, callback: Any, link: str, action: str, index: int, modules: Optional[List[Dict[str, Any]]], query: str = "") -> None:
        response = await self.api.send(f"rate/{self.identifier}/{link}/{action}")
        
        request = await self.api.send("get", payload=[unquote(link)])
        stats = request.get(unquote(link), {"likes": 0, "dislikes": 0})
        
        if modules and 0 <= index < len(modules):
            modules[index].update(stats)
            await self.edit(callback, self.ui.format(modules[index], query, index + 1, len(modules)), self.ui.buttons(link, stats, index, modules, query), modules[index].get("banner"))
            
        if response and response.get("status"):
            status = response.get("status")
            if status == "added":
                text = self.strings["added"]
            elif status == "changed":
                text = self.strings["changed"]
            elif status == "removed":
                text = self.strings["deleted"]
            else:
                text = ""
            await self.answer(callback, text, True)

    def get_logs(self) -> str:
        return "\n".join(
            [
                "\n".join(
                    handler.dumps(0, client_id=getattr(self, "client", self._client).tg_id)
                    if "client_id" in inspect.signature(handler.dumps).parameters
                    else handler.dumps(0)
                )
                for handler in logging.getLogger().handlers
                if hasattr(handler, "dumps")
            ]
        )

    @staticmethod
    def parse_deps(logs: str) -> str:
        found = []
        for pattern in (
            r"could not find a version that satisfies the requirement ([^\s,]+)",
            r"no matching distribution found for ([^\s,]+)",
        ):
            found += re.findall(pattern, logs)
        if not found:
            m = re.search(
                r"--no-warn-script-location\s+(.+?)\) with exit code",
                logs,
                re.S,
            )
            if m:
                found = m.group(1).split()
        return ", ".join(dict.fromkeys(found))

    async def install(self, callback: Any, link: str, index: int, modules: Optional[List[Dict[str, Any]]], query: str = "") -> None:
        ologs = self.get_logs()
        
        res = await self.lookup("loader").download_and_install(link)
        
        if res == 1:
            await self.answer(callback, self.strings["success"], True)
            return

        alogs = self.get_logs()
        nlogs = alogs[len(ologs):].lower()

        if "overwrite" in nlogs:
            await self.answer(callback, self.strings["overwrite"], True)
        elif any(x in nlogs for x in ("requir", "depend", "package")):
            deps = self.parse_deps(nlogs)
            text = self.strings["dependency"] + (f" ({deps})" if deps else "")
            await self.answer(callback, text, True)
        else:
            await self.answer(callback, self.strings["error"], True)

    @loader.inline_handler(
        ru_doc="(запрос) - поиск модулей.",
        ua_doc="(запит) - пошук модулів.",
        kz_doc="(сұрау) - модульдерді іздеу.",
        uz_doc="(so'rov) - modullarni qidirish.",
        fr_doc="(requête) - rechercher des modules.",
        de_doc="(anfrage) - module suchen.",
        jp_doc="(クエリ) - モジュールを検索します。"
    )
    async def fheta(self, event: 'loader.InlineCall') -> Union[Dict[str, str], None]:
        '''(query) - search modules.'''
        query = event.args
        
        if not query:
            return {
                "title": self.strings["prompt"],
                "description": self.strings["hint"],
                "message": f"{self.ui.emoji('error')} <b>{self.strings['noquery'].format(prefix=f'<code>@{self.inline.bot_username} ')}</code></b>",
                "thumb": "https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/assets/FHeta/magnifying_glass.png"
            }
            
        if len(query) > 168:
            return {
                "title": self.strings["toolong"],
                "description": self.strings["retry"],
                "message": f"{self.ui.emoji('warn')} <b>{self.strings['toolong']}</b>",
                "thumb": "https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/assets/FHeta/try_other_query.png"
            }
        
        modules = await self.api.fetch("search", query=query, inline="true", token=self.token, user_id=self.identifier, ood=str(self.config["only_official_developers"]).lower())
        
        if not modules or not isinstance(modules, list):
            return {
                "title": self.strings["retry"],
                "description": self.strings["hint"],
                "message": f"{self.ui.emoji('error')} <b>{self.strings['notfound'].format(query=f'<code>{utils.escape_html(query)}</code>')}</b>",
                "thumb": "https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/assets/FHeta/try_other_query.png"
            }

        queryid = str(uuid.uuid4())[:8]
        self.fheta_cache[queryid] = {"query": query, "mods": modules[:50]}
        results = []
        
        for index, data in enumerate(modules[:50]):
            description = data.get("description", "")
            if isinstance(description, dict):
                description = description.get(self.strings["lang"]) or description.get("doc") or next(iter(description.values()), "")
            
            markup = self.inline.generate_markup(self.ui.buttons(data.get("install", ""), data, index, modules, query))
                
            thumb_url = data.get("pic") or "https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/assets/FHeta/empty_pic.png"
            thumb = self.inline._web_document(thumb_url)
            
            results.append(
                await event.builder.article(
                    id=f"fh_{queryid}_{index}",
                    title=utils.escape_html(data.get("name", "")),
                    description=utils.escape_html(str(description)[:250] + ("..." if len(str(description)) > 250 else "")),
                    thumb=thumb,
                    text="🪐",
                    parse_mode="HTML",
                    buttons=markup
                )
            )
            
        await event.answer(results, cache_time=0)

    @loader.command(
        ru_doc="(запрос) - поиск модулей.",
        ua_doc="(запит) - пошук модулів.",
        kz_doc="(сұрау) - модульдерді іздеу.",
        uz_doc="(so'rov) - modullarni qidirish.",
        fr_doc="(requête) - rechercher des modules.",
        de_doc="(anfrage) - module suchen.",
        jp_doc="(クエリ) - モジュールкоторого префикс."
    )
    async def fhetacmd(self, message: 'telethon.types.Message') -> Any:
        '''(query) - search modules.'''
        query = utils.get_args_raw(message)
        
        if not query:
            return await utils.answer(message, f"{self.ui.emoji('error')} <b>{self.strings['noquery'].format(prefix=f'<code>{self.get_prefix()}')}</code></b>")
            
        if len(query) > 168:
            return await utils.answer(message, f"{self.ui.emoji('warn')} <b>{self.strings['toolong']}</b>")

        message = await utils.answer(message, f"{self.ui.emoji('search')} <b>{self.strings['search'].format(query=f'<code>{utils.escape_html(query)}</code>')}</b>")
        
        modules = await self.api.fetch("search", query=query, inline="false", token=self.token, user_id=self.identifier, ood=str(self.config["only_official_developers"]).lower())
        
        if not modules or not isinstance(modules, list):
            return await utils.answer(message, f"{self.ui.emoji('error')} <b>{self.strings['notfound'].format(query=f'<code>{utils.escape_html(query)}</code>')}</b>")
            
        data = modules[0]
        buttons = self.ui.buttons(data.get("install", ""), data, 0, modules, query)
        text = self.ui.format(data, query, 1, len(modules))
        banner = data.get("banner")
        
        if banner and banner not in text:
            text = f'<a href="{banner}">&#8204;</a>' + text
            
        msg = await self.inline.form(
            text,
            message,
            reply_markup=buttons,
            silent=True
        )
        
        if banner and msg:
            await asyncio.sleep(0.4)
            await self.edit(msg, text, buttons, banner)

    @loader.watcher(chat_id=7575472403)
    async def watcher(self, message: 'telethon.types.Message') -> None:
        if not self.config["install_via_fheta"]:
            return
            
        url = message.raw_text.strip()
        
        if not url.startswith("https://api.fixyres.com/module/"):
            return
            
        ologs = self.get_logs()
        
        res = await self.lookup("loader").download_and_install(url)
        
        if res == 1:
            reply = await message.respond("✅")
        else:
            alogs = self.get_logs()
            nlogs = alogs[len(ologs):].lower()
            
            if "overwrite" in nlogs:
                reply = await message.respond("😨")
            elif any(x in nlogs for x in ("requir", "depend", "package")):
                deps = self.parse_deps(nlogs)
                reply = await message.respond(f"📋{','.join(deps.split(', ')[:5])}" if deps else "📋")
            else:
                reply = await message.respond("❌")
                
        await asyncio.sleep(1)
        await reply.delete()
        await message.delete()
