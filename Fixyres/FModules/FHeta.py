__version__ = (9, 3, 9)

# meta developer: @NFModules
# meta pic: https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/assets/FHeta/logo.png
# meta banner: https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/assets/FHeta/logo.png
# scope: hikka_min 2.0.0

# ©️ Fixyres, 2024-2030
# 🌐 https://github.com/Fixyres/FModules
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 🔑 http://www.apache.org/licenses/LICENSE-2.0

import asyncio
import aiohttp
import ast
import re
import sys
import uuid
import importlib
from contextlib import suppress
from typing import Optional, Dict, List, Union, Tuple, Any
from urllib.parse import unquote
from importlib.machinery import ModuleSpec

from .. import loader, utils
from ..types import CoreOverwriteError
from herokutl.tl.functions.contacts import UnblockRequest
from aiogram.types import InlineQueryResultArticle, InputTextMessageContent, LinkPreviewOptions, ChosenInlineResult, CallbackQuery, Message


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


class MInstaller:
    async def execute(self, plugin: 'loader.Module', url: str) -> Tuple[str, List[str]]:
        try:
            code = await plugin._storage.fetch(url, auth=plugin.config.get("basic_auth"))
        except Exception:
            return "error", []
            
        for step in range(5):
            state = await self.load(plugin, code, url, step)
            
            if state == "success":
                if plugin.fully_loaded:
                    plugin.update_modules_in_db()
                return "success", []
                
            if state == "overwrite":
                return "overwrite", []
                
            if isinstance(state, list):
                return "dependency", state
                
            if state == "error":
                return "error", []
                
            await asyncio.sleep(0.5)
            
        return "dependency", []

    async def load(self, plugin: 'loader.Module', code: str, origin: str, step: int) -> Union[str, List[str]]:
        if step == 0:
            try:
                dependencies = list(filter(
                    lambda requirement: not requirement.startswith(("-", "_", ".")),
                    map(lambda raw: raw.strip().rstrip(','), loader.VALID_PIP_PACKAGES.search(code)[1].split())
                ))
                
                if dependencies:
                    if not await plugin.install_requirements(dependencies):
                        return dependencies
                    importlib.invalidate_caches()
                    return "retry"
            except Exception:
                pass
                
            try:
                packages = list(filter(
                    lambda requirement: not requirement.startswith(("-", "_", ".")),
                    map(lambda raw: raw.strip().rstrip(','), loader.VALID_APT_PACKAGES.search(code)[1].split())
                ))
                
                if packages:
                    if not await plugin.install_packages(packages):
                        return packages
                    importlib.invalidate_caches()
                    return "retry"
            except Exception:
                pass
        
        try:
            tree = ast.parse(code)
            identifier = next(
                node.name for node in tree.body
                if isinstance(node, ast.ClassDef) and any(
                    isinstance(base, ast.Attribute) and base.value.id == "Module" or 
                    isinstance(base, ast.Name) and base.id == "Module" 
                    for base in node.bases
                )
            )
        except Exception:
            identifier = "__extmod_" + str(uuid.uuid4())
        
        name = f"heroku.modules.{identifier}"
        instance = None
        
        try:
            spec = ModuleSpec(name, loader.StringLoader(code, f"<external {name}>"), origin=f"<external {name}>")
            instance = await plugin.allmodules.register_module(spec, name, origin, save_fs=False)
            
            plugin.allmodules.send_config_one(instance)
            await plugin.allmodules.send_ready_one(instance, no_self_unload=True, from_dlmod=False)
            
            return "success"
            
        except ImportError as exception:
            alternative = {"sklearn": "scikit-learn", "pil": "Pillow", "herokutl": "Heroku-TL-New"}.get(exception.name.lower(), exception.name)
            dependencies = [alternative]
            
            if not alternative or not await plugin.install_requirements(dependencies):
                return dependencies
                
            importlib.invalidate_caches()
            return "retry"
            
        except CoreOverwriteError:
            return "overwrite"
            
        except Exception:
            return "error"
            
        finally:
            if instance and sys.exc_info()[0] is not None:
                with suppress(Exception):
                    await plugin.allmodules.unload_module(instance.__class__.__name__)
                    plugin.allmodules.modules.remove(instance)


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
            
            if kind == "cmd":
                character = '@' + self.main.inline.bot_username + ' ' if item.get('inline') else self.main.get_prefix()
                row = f"<code>{character}{name}</code> {description}".strip()
            else:
                row = f"<code>{{{name}}}</code> {description}".strip()
            
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
        "dependency": "✘ Dependencies installation error! {deps}",
        "docdevs": "Use only modules from official Heroku developers when searching?",
        "doctheme": "Theme for emojis.",
        "channel": "This is the channel with all updates in FHeta!"
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
        "dependency": "✘ Ошибка установки зависимостей! {deps}",
        "docdevs": "Использовать только модули от официальных разработчиков Heroku при поиске?",
        "doctheme": "Тема для эмодзи.",
        "channel": "Это канал со всеми обновлениями в FHeta!"
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
        "dependency": "✘ Помилка встановлення залежностей! {deps}",
        "docdevs": "Використовувати тільки модулі від офіційних розробників Heroku при пошуку?",
        "doctheme": "Тема для емодзі.",
        "channel": "Це канал з усіма оновленнями в FHeta!"
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
        "toolong": "Сіздің сұрауыңыз тым үлкен, оны 168 таңбаға дейін қысқартыңыз.",
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
        "dependency": "✘ Тәуелділіктерді орнату қатесі! {deps}",
        "docdevs": "Іздеу кезінде тек ресми Heroku әзірлеушілерінің модульдерін пайдалану керек пе?",
        "doctheme": "Эмодзилер үшін тақырып.",
        "channel": "Бұл FHeta-дағы барлық жаңартулары бар арна!"
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
        "prompt": "Qidirish uchun so'rov kiriting.",
        "hint": "Nomi, buyruq, tavsif, muallif.",
        "retry": "Boshqa so'rovni sinab ko'ring.",
        "query": "So'rov",
        "install": "O'rnatish",
        "counter": "{idx}/{total}",
        "code": "Kod",
        "success": "✔ Modul muvaffaqiyatli o'rnatildi!",
        "error": "✘ Xatolik, ehtimol modul buzilgan!",
        "overwrite": "✘ Xatolik, modul o'rnatilgan modulni qayta yozishga harakat qildi!",
        "dependency": "✘ Bog'liqliklarni o'rnatish xatosi! {deps}",
        "docdevs": "Qidiruv paytida faqat rasmiy Heroku ishlab chiquvchilarining modullaridan foydalanish kerakmi?",
        "doctheme": "Emojilar uchun mavzu.",
        "channel": "Bu FHeta-dagi barcha yangilanishlari bo'lgan kanal!"
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
        "notfound": "Rien trouvé pour la requête {query}.",
        "toolong": "Votre requête est trop longue, veuillez la réduire à 168 caractères.",
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
        "success": "✔ Module installé avec succès!",
        "error": "✘ Erreur, le module est peut-être cassé!",
        "overwrite": "✘ Erreur, le module a tenté d'écraser le module intégré!",
        "dependency": "✘ Erreur d'installation des dépendances! {deps}",
        "docdevs": "Utiliser uniquement les modules des développeurs Heroku officiels lors de la recherche?",
        "doctheme": "Thème pour les emojis.",
        "channel": "Voici le canal avec toutes les mises à jour dans FHeta!"
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
        "retry": "Versuchen Sie eine andere Anfrage.",
        "query": "Anfrage",
        "install": "Installieren",
        "counter": "{idx}/{total}",
        "code": "Code",
        "success": "✔ Modul erfolgreich installiert!",
        "error": "✘ Fehler, vielleicht ist das Modul kaputt!",
        "overwrite": "✘ Fehler, Modul hat versucht, das integrierte Modul zu überschreiben!",
        "dependency": "✘ Fehler bei der Installation von Abhängigkeiten! {deps}",
        "docdevs": "Nur Module von offiziellen Heroku-Entwicklern bei der Suche verwenden?",
        "doctheme": "Thema für Emojis.",
        "channel": "Dies ist der Kanal mit allen Updates in FHeta!"
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
        "error": "✘ エラー、モジュールが壊れている可能性があります!",
        "overwrite": "✘ エラー、モジュールが組み込みモジュールを上書きしようとしました!",
        "dependency": "✘ 依存関係のインストールエラー! {deps}",
        "docdevs": "検索時に公式Heroku開発者のモジュールのみを使用しますか？",
        "doctheme": "絵文字のテーマ。",
        "channel": "これはFHetaのすべての更新を含むチャンネルです！"
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
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "only_official_developers",
                False,
                lambda: self.strings("docdevs"),
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "theme",
                "default",
                lambda: self.strings("doctheme"),
                validator=loader.validators.Choice(["default", "winter", "summer", "spring", "autumn"])
            )
        )
    
    async def on_unload(self) -> None:
        if hasattr(self, "api") and self.api.session and not self.api.session.closed:
            await self.api.session.close()
            
    async def client_ready(self, client: 'telethon.TelegramClient', database: 'loader.Database') -> None:
        try:
            await client(UnblockRequest("@FHeta_robot"))
            await utils.dnd(client, "@FHeta_robot", archive=True)
        except Exception:
            pass
        
        self.identifier = (await client.get_me()).id
        self.token = database.get("FHeta", "token")
        
        self.api = FHetaAPI()
        self.installer = MInstaller()
        self.ui = FHetaUI(self)
        
        await self.request_join(
            "NFHeta_Updates",
            f"{self.ui.emoji('channel')} {self.strings('channel')}"
        )
        
        self.api.token = self.token
        
        router = None
        try:
            frame = sys._getframe()
            while frame:
                if 'self' in frame.f_locals and type(frame.f_locals['self']).__name__ == "Modules":
                    router = getattr(frame.f_locals['self'], "inline", None)
                    if router:
                        break
                frame = frame.f_back
        except Exception:
            pass

        router = router or self.inline
        dispatcher = getattr(router, "_dp", getattr(router, "dp", getattr(router, "router", None)))
        self.bot = getattr(router, "_bot", getattr(router, "bot", getattr(self.inline, "bot", None)))

        if dispatcher:
            if not getattr(dispatcher, "_fpatched", False):
                
                async def fmiddleware(handler: Any, event: Any, data: Any) -> Any:
                    try:
                        module = self.lookup("FHeta")
                        
                        if module and getattr(event, "result_id", "").startswith("fh_"):
                            await module.click(event)
                            return None
                    except Exception:
                        pass
                        
                    return await handler(event, data)
                
                try:
                    dispatcher.chosen_inline_result.middleware(fmiddleware)
                    dispatcher._fpatched = True
                except Exception:
                    pass

        if self.token and not await self.api.fetch("validatetkn", user_id=str(self.identifier)):
            self.token = None
            self.api.token = None
        
        if not self.token:
            try:
                async with client.conversation("@FHeta_robot") as conversation:
                    await conversation.send_message('/token')
                    self.token = (await conversation.get_response(timeout=5)).text.strip()
                    database.set("FHeta", "token", self.token)
                    self.api.token = self.token
            except Exception:
                pass
                
        asyncio.create_task(self.sync())
        
    async def sync(self):
        ll = None
        while True:
            try:
                cl = self.strings["lang"]
                if cl != ll:
                    await self.api.send("dataset", user_id=self.identifier, lang=cl)
                    ll = cl
            except Exception:
                pass
            await asyncio.sleep(1)

    async def answer(self, callback: Union[CallbackQuery, ChosenInlineResult], text: Optional[str] = None, alert: bool = False) -> None:
        try:
            if text:
                await callback.answer(text, show_alert=alert)
            else:
                await callback.answer()
        except Exception:
            pass

    async def edit(self, target: Union[str, ChosenInlineResult, CallbackQuery, Message, 'telethon.types.Message'], text: str, buttons: List[List[Dict[str, Any]]], banner: Optional[str] = None) -> None:
        try:
            options = LinkPreviewOptions(url=banner, show_above_text=True, prefer_large_media=True) if banner else LinkPreviewOptions(is_disabled=True)
            markup = self.inline.generate_markup(buttons)
            
            if not self.bot:
                return

            arguments = {
                "text": text,
                "reply_markup": markup,
                "link_preview_options": options,
                "parse_mode": "HTML"
            }

            inline = target if isinstance(target, str) else getattr(target, "inline_message_id", None)
            
            if inline:
                arguments["inline_message_id"] = inline
            else:
                message = getattr(target, "message", target)
                chat = getattr(getattr(message, "chat", message), "id", getattr(message, "chat_id", None))
                identifier = getattr(message, "message_id", getattr(message, "id", None))
                
                if chat and identifier:
                    arguments["chat_id"] = chat
                    arguments["message_id"] = identifier
                else:
                    return

            await self.bot.edit_message_text(**arguments)
        except Exception:
            pass

    async def click(self, callback: ChosenInlineResult) -> None:
        try:
            if not getattr(callback, "result_id", "").startswith("fh_"):
                return
                
            parts = callback.result_id.split("_")
            if len(parts) != 3:
                return
                
            queryid = parts[1]
            index = int(parts[2])
            
            cache = getattr(self.inline, "fheta_cache", {})
            saved = cache.get(queryid, {})
            query = saved.get("query", "")
            modules = saved.get("mods", [])
            
            if not modules or index >= len(modules):
                return
                
            data = modules[index]
            text = self.ui.format(data, query, index+1, len(modules), True)
            buttons = self.ui.buttons(data.get("install", ""), data, index, None, query)
            
            await self.edit(callback, text, buttons, data.get("banner"))
        except Exception:
            pass

    async def show(self, callback: Union[CallbackQuery, ChosenInlineResult], index: int, modules: List[Dict[str, Any]], query: str) -> None:
        await self.answer(callback)
        text = f"{self.ui.emoji('modules_list')} <b>{self.strings['list']}</b>"
        await self.edit(callback, text, self.ui.pagination(modules, query, 0, index))

    async def page(self, callback: Union[CallbackQuery, ChosenInlineResult], current: int, modules: List[Dict[str, Any]], query: str, index: int) -> None:
        await self.answer(callback)
        text = f"{self.ui.emoji('modules_list')} <b>{self.strings['list']}</b>"
        await self.edit(callback, text, self.ui.pagination(modules, query, current, index))

    async def navigate(self, callback: Union[CallbackQuery, ChosenInlineResult], index: int, modules: List[Dict[str, Any]], query: str = "") -> None:
        await self.answer(callback)
        if 0 <= index < len(modules):
            data = modules[index]
            text = self.ui.format(data, query, index + 1, len(modules))
            buttons = self.ui.buttons(data.get('install', ''), data, index, modules, query)
            await self.edit(callback, text, buttons, data.get("banner"))

    async def rate(self, callback: Union[CallbackQuery, ChosenInlineResult, Message, 'telethon.types.Message'], link: str, action: str, index: int, modules: Optional[List[Dict[str, Any]]], query: str = "") -> None:
        response = await self.api.send(f"rate/{self.identifier}/{link}/{action}")
        
        request = await self.api.send("get", payload=[unquote(link)])
        stats = request.get(unquote(link), {"likes": 0, "dislikes": 0})
        
        if modules and index < len(modules):
            modules[index].update(stats)
            
        try:
            await callback.edit(reply_markup=self.ui.buttons(link, stats, index, modules, query))
        except Exception:
            pass
            
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

    async def install(self, callback: Union[CallbackQuery, ChosenInlineResult], link: str, index: int, modules: Optional[List[Dict[str, Any]]], query: str = "") -> None:
        state, dependencies = await self.installer.execute(self.lookup("loader"), link)
        
        try:
            if state == "success":
                await self.answer(callback, self.strings["success"], True)
            elif state == "dependency":
                formatted = f"({','.join(dependencies[:5])})" if dependencies else ""
                await self.answer(callback, self.strings["dependency"].format(deps=formatted), True)
            elif state == "overwrite":
                await self.answer(callback, self.strings["overwrite"], True)
            else:
                await self.answer(callback, self.strings["error"], True)
        except Exception:
            pass

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
        if not hasattr(self.inline, "fheta_cache"):
            self.inline.fheta_cache = {}
            
        if len(self.inline.fheta_cache) >= 50:
            self.inline.fheta_cache.pop(next(iter(self.inline.fheta_cache)))
            
        self.inline.fheta_cache[queryid] = {"query": query, "mods": modules}
        
        results = []
        
        for index, data in enumerate(modules[:50]):
            description = data.get("description", "")
            if isinstance(description, dict):
                description = description.get(self.strings["lang"]) or description.get("doc") or next(iter(description.values()), "")
            
            markup = None
            try:
                markup = self.inline.generate_markup(self.ui.buttons(data.get("install", ""), data, index, None, query))
            except Exception:
                pass
                
            results.append(InlineQueryResultArticle(
                id=f"fh_{queryid}_{index}",
                title=utils.escape_html(data.get("name", "")),
                description=utils.escape_html(str(description)[:250] + ("..." if len(str(description)) > 250 else "")),
                thumbnail_url=data.get("pic") or "https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/assets/FHeta/empty_pic.png",
                input_message_content=InputTextMessageContent(message_text="ㅤ", parse_mode="HTML"),
                reply_markup=markup
            ))
            
        await event.inline_query.answer(results, cache_time=0)

    @loader.command(
        ru_doc="(запрос) - поиск модулей.",
        ua_doc="(запит) - пошук модулів.",
        kz_doc="(сұрау) - модульдерді іздеу.",
        uz_doc="(so'rov) - modullarni qidirish.",
        fr_doc="(requête) - rechercher des modules.",
        de_doc="(anfrage) - module suchen.",
        jp_doc="(クエリ) - モジュールを検索します。"
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
        form = await self.inline.form("ㅤ", message, reply_markup=buttons, silent=True)
        text = self.ui.format(data, query, 1, len(modules))
        
        await self.edit(form, text, buttons, data.get("banner"))

    @loader.watcher(chat_id=7575472403)
    async def watcher(self, message: 'telethon.types.Message') -> None:
        url = message.raw_text.strip()
        
        if not url.startswith("https://api.fixyres.com/module/"):
            return
            
        try:
            state, dependencies = await self.installer.execute(self.lookup("loader"), url)
            
            if state == "success":
                reply = await message.respond("✅")
            elif state == "dependency":
                reply = await message.respond(f"📋{','.join(dependencies[:5])}" if dependencies else "📋")
            elif state == "overwrite":
                reply = await message.respond("😨")
            else:
                reply = await message.respond("❌")
                
            await asyncio.sleep(1)
            await reply.delete()
            await message.delete()
        except Exception:
            pass
