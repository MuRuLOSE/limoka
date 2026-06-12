# meta developer: @limokanews
# requires: whoosh cryptography filetype


from collections import Counter, defaultdict
import shutil
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import QueryParser, OrGroup
from whoosh.query import FuzzyTerm, Wildcard
from whoosh.writing import LockError
import aiohttp
import random
import logging
import os
import html
import json
import re
import asyncio
from typing import Iterable, Union, List, Dict, Any, Optional
import hashlib
from telethon.types import Message
from telethon.errors.rpcerrorlist import WebpageMediaEmptyError
from telethon import TelegramClient
from telethon.errors.rpcerrorlist import YouBlockedUserError
from telethon import functions
import filetype

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import ast


from aiogram.exceptions import TelegramBadRequest as BadRequest

from .. import utils, loader
from ..types import BotInlineCall, InlineCall

logger = logging.getLogger("Limoka")
__version__ = (1, 5, 6)


def _parse_version_from_source(source: str):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__version__":
                    try:
                        return ast.literal_eval(node.value)
                    except (ValueError, SyntaxError):
                        return None
    return None

WEIGHTS = {
    "inline.token_obtainment": 15,
    "main": 10,
    "inline": 7,
    "translations": 5,
    "security": 3,
}

DEFAULT_WEIGHT = 1

BASE_DIR = os.getcwd()


def _get_lang_value(data: Dict[str, Any], lang: str) -> str:
    if not isinstance(data, dict):
        return str(data) if data else ""
    return data.get(lang, data.get("default", data.get("en", "")))


class SearchIndex:
    """Handles full-text search operations."""

    def __init__(self, query: str, index):
        """
        Args:
            query: Search query string
            index: Whoosh index instance
        """
        self.schema = Schema(
            title=TEXT(stored=True), path=ID(stored=True), content=TEXT(stored=True)
        )
        self.query = query
        self.index = index

    def search(self) -> List[str]:
        """Execute search and return list of module paths."""
        with self.index.searcher() as searcher:
            parser = QueryParser("content", self.index.schema, group=OrGroup.factory(0.8))
            query = parser.parse(self.query)
            wildcard_query = Wildcard("content", f"*{self.query}*")
            fuzzy_query = FuzzyTerm("content", self.query, maxdist=2, prefixlength=1)
            for search_query in [query, wildcard_query, fuzzy_query]:
                results = searcher.search(search_query)
                if results:
                    return list(set(result["path"] for result in results))
        return []


class APIClient:
    """Handles HTTP requests for fetching JSON data."""

    async def fetch_json(self, base_url: str, path: str) -> Dict[str, Any]:
        """
        Fetch JSON data from a URL.
        
        Args:
            base_url: Base URL for the API
            path: Path to append to base URL
            
        Returns:
            Parsed JSON as dictionary
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}{path}") as resp:
                if resp.status == 200:
                    return json.loads(await resp.text())
        return {}


class ModuleRepository:
    """Manages module data and filtering."""

    def __init__(self, modules: Dict[str, Any], repositories: Dict[str, Any]):
        """
        Args:
            modules: Dictionary of module definitions
            repositories: Dictionary of repository metadata
        """
        self.modules = modules
        self.repositories = repositories

    def apply_newbie_filter(self, filter_enabled: bool) -> Dict[str, Any]:
        """
        Filter out modules from repositories tagged as 'newbie'.
        
        Args:
            filter_enabled: Whether filtering is enabled
            
        Returns:
            Filtered modules dictionary
        """
        if not filter_enabled:
            return self.modules

        filtered = {}
        for path, info in self.modules.items():
            repo_key = "/".join(path.split("/")[:2]) if "/" in path else path
            repo = self.repositories.get(repo_key)
            tags = repo.get("tags", []) if repo else []
            if "newbie" not in tags:
                filtered[path] = info
        return filtered

    def get_tags_for_module(self, module_path: str) -> List[str]:
        """Get repository tags for a specific module."""
        repo_key = "/".join(module_path.split("/")[:2]) if "/" in module_path else module_path
        for repo_url in self.repositories:
            if repo_url.replace("https://github.com/", "") == repo_key:
                return self.repositories[repo_url].get("tags", [])
        return []

    def get_all_categories(self) -> List[str]:
        """Get all unique categories from modules."""
        categories = set()
        for module_data in self.modules.values():
            categories.update(module_data.get("category", ["No category"]))
        return sorted(categories)


class CommandFormatter:
    """Formats module commands and metadata."""

    def __init__(self, strings: Dict[str, Any], bot_username: str, prefix: str):
        """
        Args:
            strings: Localized strings dictionary
            bot_username: Bot username for inline handlers
            prefix: Command prefix
        """
        self.strings = strings
        self.bot_username = bot_username
        self.prefix = prefix

    def format_commands(self, module_info: Dict[str, Any], lang: str = "en") -> List[str]:
        """
        Format module commands and handlers into display strings.
        
        Args:
            module_info: Module information dictionary
            lang: Language code
            
        Returns:
            List of formatted command strings
        """
        commands = []
        for i, cmd in enumerate(module_info.get("new_commands", []), 1):
            name = cmd.get("name", "")
            desc_map = cmd.get("description", {})
            emoji = self._get_emoji_for_number(i)
            desc = _get_lang_value(desc_map, lang) or self.strings["no_info"]
            commands.append(
                self.strings["command_template"].format(
                    prefix=self.prefix,
                    command=html.escape(name),
                    emoji=emoji,
                    description=html.escape(desc),
                )
            )
        
        for handler in module_info.get("inline_handlers", []):
            name = handler.get("name", "")
            desc_map = handler.get("description", {})
            desc = _get_lang_value(desc_map, lang) or self.strings["no_info"]
            commands.append(
                self.strings["inline_handler_template"].format(
                    inline_bot=self.bot_username,
                    command=html.escape(name),
                    description=html.escape(desc),
                )
            )
        return commands

    def _get_emoji_for_number(self, num: int) -> str:
        """Get emoji representation for a number."""
        if num <= 10:
            return self.strings["emojis"].get(num, "")
        emoji = ""
        for digit in str(num):
            emoji += self.strings["emojis"].get(int(digit), "")
        return emoji


class ModuleContentBuilder:
    """Builds formatted module content for display."""

    def __init__(self, strings: Dict[str, Any], formatter: CommandFormatter, repository: ModuleRepository):
        """
        Args:
            strings: Localized strings dictionary
            formatter: CommandFormatter instance
            repository: ModuleRepository instance
        """
        self.strings = strings
        self.formatter = formatter
        self.repository = repository

    def build_content(
        self,
        module_info: Dict[str, Any],
        query: str,
        filters: Dict[str, List[str]],
        url: str,
        include_categories: bool = True,
        module_path: Optional[str] = None,
        lang: str = "en",

    ) -> tuple:
        """
        Build complete formatted module content.
        
        Returns:
            Tuple of (header, body_pages, footer, categories_text)
        """
        name = html.escape(module_info.get("name") or self.strings["no_info"])
        cls_doc = module_info.get("cls_doc", {})
        description = html.escape(
            _get_lang_value(cls_doc, lang)
            or _get_lang_value(module_info.get("description", ""), lang)
            or self.strings["no_info"]
        )
        dev_username = html.escape(module_info["meta"].get("developer") or "Unknown")
        
        if len(description) > 300:
            description = description[:297] + "…"
        
        categories_text = self._build_categories_text(filters)
        commands = self.formatter.format_commands(module_info, lang)
        header = self._build_header(query, name, description, dev_username, module_path, url)
        footer = self._build_footer(module_path)
        body_pages = self._paginate_commands(commands)
        
        return header, body_pages, footer, categories_text

    def _build_header(self, query: str, name: str, description: str, dev_username: str, module_path: Optional[str], url: str) -> str:
        """Build message header with module info and tags."""
        tags_list = self.repository.get_tags_for_module(module_path) if module_path else []
        tags_text = ", ".join(self.strings["tags"].get(tag, tag) for tag in tags_list)
        
        header_template = self.strings["found_header"]
        if not tags_text:
            # Replace the tags line but keep blockquote closure at the end
            header_template = header_template.replace(
                "\n\n<b><tg-emoji emoji-id=5418376169055602355>🏷</tg-emoji> Tags:</b> {tags}</blockquote>\n\n",
                "</blockquote>\n\n"
            )
            header_template = header_template.replace(
                "\n\n<b><tg-emoji emoji-id=5418376169055602355>🏷</tg-emoji> Теги:</b> {tags}</blockquote>\n\n",
                "</blockquote>\n\n"
            )
        
        header = header_template.format(
            query=html.escape(query),
            name=name,
            description=description,
            username=dev_username,
            tags=tags_text,
            module_path=module_path,
            url=url
        )
        
        # Remove extra newlines
        header = re.sub(r'\n+', '\n', header)
        
        return header

    def _build_footer(self, module_path: Optional[str]) -> str:
        """Build message footer with download command."""
        clean_path = (module_path or "").replace("\\", "/")
        return "" # unused for now, but may be used in the future for additional info
        return self.strings["found_footer"].format(
            url=html.escape(self.formatter.strings.get("limokaurl", "")),
            module_path=html.escape(clean_path),
            prefix=self.formatter.prefix,
        )

    def _build_categories_text(self, filters: Dict[str, List[str]]) -> str:
        """Build categories text if any are selected."""
        categories = filters.get("category", [])
        if categories:
            return "\n" + self.strings["selected_categories"].format(
                categories=", ".join(html.escape(c) for c in categories)
            )
        return ""

    def _paginate_commands(self, commands: List[str], max_length: int = 500) -> List[str]:
        """Split commands into pages based on length."""
        if not commands:
            return [""]
        
        commands_text = "".join(commands)
        if len(commands_text) <= max_length:
            return [commands_text]
        
        pages = []
        current_page = []
        current_length = 0
        
        for cmd in commands:
            if current_length + len(cmd) > max_length:
                if current_page:
                    pages.append("".join(current_page))
                    current_page = []
                    current_length = 0
            current_page.append(cmd)
            current_length += len(cmd)
        
        if current_page:
            pages.append("".join(current_page))
        
        return pages or [""]


@loader.tds
class Limoka(loader.Module):
    """Modules are now in one place with easy searching!"""

    strings = {
        "name": "Limoka",
        "wait": (
            "<blockquote>Just wait\n"
            "<tg-emoji emoji-id=5404630946563515782>🔍</tg-emoji> A search is underway among {count} modules "
            "for the query: <code>{query}</code>\n"
            "<i>{fact}</i></blockquote>"
        ),
        "found_header": (
            "<blockquote><tg-emoji emoji-id=5413334818047940135>🔍</tg-emoji> Found module <b>{name}</b> "
            "by query: <b>{query}</b>\n\n"
            "<b><tg-emoji emoji-id=5413350219800661019>🌐</tg-emoji> <a href='{url}{module_path}'>Source</a></b>\n"
            "<b><tg-emoji emoji-id=5418376169055602355>ℹ️</tg-emoji> Description:</b> {description}\n"
            "<b><tg-emoji emoji-id=5418299289141004396>🧑‍💻</tg-emoji> Developer:</b> {username}\n\n"
            "<b><tg-emoji emoji-id=5418376169055602355>🏷</tg-emoji> Tags:</b> {tags}</blockquote>\n\n"
        ),
        "found_body": ("{commands}"),
        "caption_short": (
            "<blockquote><tg-emoji emoji-id=5413334818047940135>🔍</tg-emoji> <b>{safe_name}</b>\n"
            "<b><tg-emoji emoji-id=5413350219800661019>🌐</tg-emoji> <a href='{url}{module_path}'>Source</a></b>\n"
            "<b><tg-emoji emoji-id=5418376169055602355>ℹ️</tg-emoji> Description:</b> {safe_desc}\n"
            "<b><tg-emoji emoji-id=5418299289141004396>🧑‍💻</tg-emoji> Dev:</b> {dev_username}</blockquote>\n"
        ),
        "command_template": "<blockquote>{emoji} <code>{prefix}{command}</code> — {description}</blockquote>\n",
        "inline_handler_template": "<blockquote>{inline_bot} {command} — {description}</blockquote>\n",
        "emojis": {
            1: "<tg-emoji emoji-id=5416037945909987712>1️⃣</tg-emoji>",
            2: "<tg-emoji emoji-id=5413855071731470617>2️⃣</tg-emoji>",
            3: "<tg-emoji emoji-id=5416068826724850291>3️⃣</tg-emoji>",
            4: "<tg-emoji emoji-id=5415843998071803071>4️⃣</tg-emoji>",
            5: "<tg-emoji emoji-id=5415684843763686989>5️⃣</tg-emoji>",
            6: "<tg-emoji emoji-id=5415975458430796879>6️⃣</tg-emoji>",
            7: "<tg-emoji emoji-id=5415769763857060166>7️⃣</tg-emoji>",
            8: "<tg-emoji emoji-id=5416006506749383505>8️⃣</tg-emoji>",
            9: "<tg-emoji emoji-id=5415963015910544694>9️⃣</tg-emoji>",
        },
        "404": "<blockquote><tg-emoji emoji-id=5210952531676504517>❌</tg-emoji> <b>Not found by query: <i>{query}</i></b></blockquote>",
        "noargs": "<blockquote><tg-emoji emoji-id=5210952531676504517>❌</tg-emoji> <b>No args</b></blockquote>",
        "?": "<blockquote><tg-emoji emoji-id=5951895176908640647>🔎</tg-emoji> Request too short / not found</blockquote>",
        "no_info": "No information",
        "facts": [
            "<blockquote><tg-emoji emoji-id=5472193350520021357>🛡</tg-emoji> The limoka catalog is carefully moderated!</blockquote>",
            "<blockquote><tg-emoji emoji-id=5940434198413184876>🚀</tg-emoji> Limoka performance allows you to search for modules quickly!</blockquote>",
        ],
        "inline404": "<blockquote>Not found</blockquote>",
        "inline?": "<blockquote>Request too short / not found</blockquote>",
        "inlinenoargs": "<blockquote>Please, enter query</blockquote>",
        "history": (
            "<blockquote><tg-emoji emoji-id=5879939498149679716>🔎</tg-emoji> <b>Your search history:</b>\n"
            "{history}</blockquote>"
        ),
        "filter_menu": "Choose filters",
        "filter_cat": "📑 Filter by Category",
        "apply_filters": "✅ Apply Filters",
        "clear_filters": "🗑 Clear Filters",
        "back_to_results": "🔙 Back to Results",
        "empty_history": "<blockquote><tg-emoji emoji-id=5879939498149679716>🔎</tg-emoji> <b>Your search history is empty!</b></blockquote>",
        "enter_query": "🔍 Enter new search query:",
        "global_search": "<blockquote><tg-emoji emoji-id=5413334818047940135>🔍</tg-emoji> Global search for <b>{query}</b> — found <b>{count}</b> modules</blockquote>",
        "change_query": "🔍 Change query",
        "no_modules": "<blockquote>No modules available.</blockquote>",
        "filter_title": "🏷 Filters",
        "category_title": "📂 Categories",
        "selected_categories": "<blockquote>✅ Selected categories: {categories}</blockquote>",
        "no_categories": "<blockquote>No categories found in the module database</blockquote>",
        "select_category": "<blockquote>Select categories for query: <code>{query}</code>\n(You can select multiple)</blockquote>",
        "back": "🔙 Back",
        "category": "📁 {category}",
        "no_category": "<blockquote>No category</blockquote>",
        "global_button": "🌍 Results",
        "filtered_button": "🏷️ Filtered search",
        "inline_search": "🔍 Search in Limoka",
        "install_button": "🪄 Install",
        "inline_no_results": "<blockquote>❌ No modules found</blockquote>",
        "inline_error": "<blockquote>❌ Search error occurred</blockquote>",
        "inline_short_query": "<blockquote>❌ Query too short (min 2 chars)</blockquote>",
        "inline_switch_pm": "💬 Open in chat",
        "inline_switch_pm_text": "🔍 Results for: {query}",
        "inline_start_message": "<blockquote><tg-emoji emoji-id=5413334818047940135>🔍</tg-emoji> <b>Limoka Search</b>\nType module name or keyword</blockquote>",
        "first_page": "<blockquote>This is the first page!</blockquote>",
        "last_page": "<blockquote>This is the last page!</blockquote>",
        "display_error": "<blockquote>Error displaying module. Please try again.</blockquote>",
        "error_occurred": "<blockquote>An error occurred. Please try again.</blockquote>",
        "start_search_form": "<blockquote><tg-emoji emoji-id=5413334818047940135>🔍</tg-emoji> <b>Limoka Search</b>\nEnter your query to search for modules:</blockquote>",
        "global_search_form": "<blockquote><tg-emoji emoji-id=5413334818047940135>🔍</tg-emoji> <b>Global Search</b>\nEnter your query to search ALL modules without filters:</blockquote>",
        "history_cleared": "<blockquote><tg-emoji emoji-id=5427009710268689068>🧹</tg-emoji> <b>Search history cleared!</b></blockquote>",
        "invalid_history_arg": "<blockquote><tg-emoji emoji-id=5210952531676504517>❌</tg-emoji> <b>Invalid argument for history command. Use:</b>\n<code>.lshistory</code> - show history\n<code>.lshistory clear</code> - clear history</blockquote>",
        "close": "❌ Close",
        "watcher_no_tag": "<blockquote>❌ Invalid message format. No #limoka tag found.</blockquote>",
        "watcher_invalid_format": "<blockquote>❌ Invalid format. Expected: #limoka:path:signature</blockquote>",
        "watcher_signature_invalid": "<blockquote>❌ Signature invalid! Installation aborted.</blockquote>",
        "watcher_loader_missing": "<blockquote>❌ Loader module not found.</blockquote>",
        "watcher_module_not_found": "<blockquote>❌ Module not found in Limoka database: <code>{path}</code></blockquote>",
        "watcher_critical": "<blockquote>❌ Critical error: {error}</blockquote>",
        "tags": {
            "herokutrusted": "Heroku Trusted",
            "hikkatrusted": "Hikka Trusted",
            "nonactive": "Non-Active Repository",
            "nonlongermaintained": "No Longer Maintained Repository",
            "newbie": "Newbie",
        },
        "indexing_in_progress": (
            "<blockquote>⚠️ Database is busy, "
            "try again later. "
            "If issue persists, try "
            "removing limoka_index in the userbot's root folder. "
            "If error persists again, report to developers</blockquote>"
        ),
        "body_page": "Commands",
        "install_failed": "Installation failed. Check logs for details.",
        "install_succeeded": "Module installed successfully!",
        "update_available": (
            "🔔 <b>New update available!</b>\n\n"
            "New Limoka Version {version} already available. Please update for better performance, bug fixes, and new features.\n"
            "Press the button below to update the module."
        ),
        "no_updates_available": "<blockquote>❌ No updates available. You are using the latest version of Limoka.</blockquote>",
        "module_update_available": "<blockquote>🔔 Notification about module update has been sent, check @{bot}.</blockquote>",
        "index_update_started": "<blockquote>🔄 Limoka module index update has started. This may take a few minutes. Please wait...</blockquote>",
        "index_update_failed": "<blockquote>❌ Failed to update Limoka module index. Please try again later. If the error persists, report to developers</blockquote>",
        "index_update_success": "<blockquote>✅ Limoka module index updated successfully!</blockquote>",
        "update_check_started": "<blockquote>🔍 Checking for Limoka updates...</blockquote>",
    }
    strings_ru = {
        "name": "Limoka",
        "wait": (
            "<blockquote>Подождите\n"
            "<tg-emoji emoji-id=5404630946563515782>🔍</tg-emoji> Идёт поиск среди {count} модулей по запросу: <code>{query}</code>\n"
            "<i>{fact}</i></blockquote>"
        ),
        "found_header": (
            "<blockquote><tg-emoji emoji-id=5413334818047940135>🔍</tg-emoji> Найден модуль <b>{name}</b> "
            "по запросу: <b>{query}</b>\n\n"
            "<b><tg-emoji emoji-id=5413350219800661019>🌐</tg-emoji> <a href='{url}{module_path}'>Исходный код</a></b>\n"
            "<b><tg-emoji emoji-id=5418376169055602355>ℹ️</tg-emoji> Описание:</b> {description}\n"
            "<b><tg-emoji emoji-id=5418299289141004396>🧑‍💻</tg-emoji> Разработчик:</b> {username}\n\n"
            "<b><tg-emoji emoji-id=5418376169055602355>🏷</tg-emoji> Теги:</b> {tags}</blockquote>\n\n"
        ),
        "found_body": ("{commands}"),
        "caption_short": (
            "<blockquote><tg-emoji emoji-id=5413334818047940135>🔍</tg-emoji> <b>{safe_name}</b>\n"
            "<b><tg-emoji emoji-id=5413350219800661019>🌐</tg-emoji> <a href='{url}{module_path}'>Исходный код</a></b>\n"
            "<b><tg-emoji emoji-id=5418376169055602355>ℹ️</tg-emoji> Описание:</b> {safe_desc}\n"
            "<b><tg-emoji emoji-id=5418299289141004396>🧑‍💻</tg-emoji> Разработчик:</b> {dev_username}</blockquote>\n"
        ),
        "command_template": "<blockquote>{emoji} <code>{prefix}{command}</code> — {description}</blockquote>\n",
        "inline_handler_template": "<blockquote>{inline_bot} {command} — {description}</blockquote>\n",
        "emojis": {
            1: "<tg-emoji emoji-id=5416037945909987712>1️⃣</tg-emoji>",
            2: "<tg-emoji emoji-id=5413855071731470617>2️⃣</tg-emoji>",
            3: "<tg-emoji emoji-id=5416068826724850291>3️⃣</tg-emoji>",
            4: "<tg-emoji emoji-id=5415843998071803071>4️⃣</tg-emoji>",
            5: "<tg-emoji emoji-id=5415684843763686989>5️⃣</tg-emoji>",
            6: "<tg-emoji emoji-id=5415975458430796879>6️⃣</tg-emoji>",
            7: "<tg-emoji emoji-id=5415769763857060166>7️⃣</tg-emoji>",
            8: "<tg-emoji emoji-id=5416006506749383505>8️⃣</tg-emoji>",
            9: "<tg-emoji emoji-id=5415963015910544694>9️⃣</tg-emoji>",
            10: "<tg-emoji emoji-id=5415642160378696377>🔟</tg-emoji>"
        },
        "404": "<blockquote><tg-emoji emoji-id=5210952531676504517>❌</tg-emoji> <b>Не найдено по запросу: <i>{query}</i></b></blockquote>",
        "noargs": "<blockquote><tg-emoji emoji-id=5210952531676504517>❌</tg-emoji> <b>Нет аргументов</b></blockquote>",
        "?": "<blockquote><tg-emoji emoji-id=5951895176908640647>🔎</tg-emoji> Запрос слишком короткий / не найден</blockquote>",
        "no_info": "Нет информации",
        "facts": [
            "<blockquote><tg-emoji emoji-id=5472193350520021357>🛡</tg-emoji> Каталог Limoka тщательно модерируется!</blockquote>",
            "<blockquote><tg-emoji emoji-id=5940434198413184876>🚀</tg-emoji> Limoka позволяет искать модули с невероятной скоростью!</blockquote>",
            (
                "<blockquote><tg-emoji emoji-id=5188311512791393083>🔎</tg-emoji> Limoka имеет лучший поиск*!\n"
                "<i>* В сравнении с предыдущей версией Limoka</i></blockquote>"
            ),
        ],
        "inline404": "<blockquote>Не найдено</blockquote>",
        "inline?": "<blockquote>Запрос слишком короткий / не найден</blockquote>",
        "inlinenoargs": "<blockquote>Введите запрос</blockquote>",
        "history": (
            "<blockquote><tg-emoji emoji-id=5879939498149679716>🔎</tg-emoji> <b>История поиска:</b>\n"
            "{history}</blockquote>"
        ),
        "filter_menu": "Выберите фильтры",
        "filter_cat": "📑 Фильтр по категориям",
        "apply_filters": "✅ Применить фильтры",
        "clear_filters": "🗑 Очистить фильтры",
        "back_to_results": "🔙 Вернуться к результатам",
        "empty_history": "<blockquote><tg-emoji emoji-id=5879939498149679716>🔎</tg-emoji> <b>История поиска пуста!</b></blockquote>",
        "enter_query": "🔍 Введите новый поисковый запрос:",
        "global_search": "<blockquote><tg-emoji emoji-id=5413334818047940135>🔍</tg-emoji> Глобальный поиск по <b>{query}</b> — найдено <b>{count}</b> модулей</blockquote>",
        "change_query": "🔍 Изменить запрос",
        "no_modules": "<blockquote>Модули недоступны.</blockquote>",
        "filter_title": "🏷 Фильтры",
        "category_title": "📂 Категории",
        "selected_categories": "<blockquote>✅ Выбранные категории: {categories}</blockquote>",
        "no_categories": "<blockquote>Категории не найдены в базе модулей</blockquote>",
        "select_category": "<blockquote>Выберите категории для запроса: <code>{query}</code>\n(Можно выбрать несколько)</blockquote>",
        "back": "🔙 Назад",
        "category": "📁 {category}",
        "no_category": "<blockquote>Без категории</blockquote>",
        "global_button": "🌍 Результаты",
        "filtered_button": "🏷️ Поиск с фильтрами",
        "inline_search": "🔍 Поиск в Limoka",
        "install_button": "🪄 Установить",
        "inline_no_results": "<blockquote>❌ Модули не найдены</blockquote>",
        "inline_error": "<blockquote>❌ Ошибка поиска</blockquote>",
        "inline_short_query": "<blockquote>❌ Запрос слишком короткий (мин. 2 символа)</blockquote>",
        "inline_switch_pm": "💬 Открыть в чате",
        "inline_switch_pm_text": "🔍 Результаты для: {query}",
        "inline_start_message": "<blockquote><tg-emoji emoji-id=5413334818047940135>🔍</tg-emoji> <b>Limoka Поиск</b>\nВведите название модуля или ключевое слово</blockquote>",
        "first_page": "<blockquote>Это первая страница!</blockquote>",
        "last_page": "<blockquote>Это последняя страница!</blockquote>",
        "display_error": "<blockquote>Ошибка отображения модуля. Пожалуйста, попробуйте еще раз.</blockquote>",
        "error_occurred": "<blockquote>Произошла ошибка. Пожалуйста, попробуйте еще раз.</blockquote>",
        "start_search_form": "<blockquote><tg-emoji emoji-id=5413334818047940135>🔍</tg-emoji> <b>Limoka Поиск</b>\nВведите ваш запрос для поиска модулей:</blockquote>",
        "global_search_form": "<blockquote><tg-emoji emoji-id=5413334818047940135>🔍</tg-emoji> <b>Глобальный Поиск</b>\nВведите запрос для поиска ВСЕХ модулей без фильтров:</blockquote>",
        "history_cleared": "<blockquote><tg-emoji emoji-id=5427009710268689068>🧹</tg-emoji> <b>История поиска очищена!</b></blockquote>",
        "invalid_history_arg": "<blockquote><tg-emoji emoji-id=5210952531676504517>❌</tg-emoji> <b>Неверный аргумент для команды истории. Используйте:</b>\n<code>.lshistory</code> - показать историю\n<code>.lshistory clear</code> - очистить историю</blockquote>",
        "close": "❌ Закрыть",
        "watcher_no_tag": "<blockquote>❌ Неверный формат сообщения. Тег #limoka не найден.</blockquote>",
        "watcher_invalid_format": "<blockquote>❌ Неверный формат. Ожидается: #limoka:path:signature</blockquote>",
        "watcher_signature_invalid": "<blockquote>❌ Неверная подпись! Установка отменена.</blockquote>",
        "watcher_loader_missing": "<blockquote>❌ Модуль загрузчика не найден.</blockquote>",
        "watcher_module_not_found": "<blockquote>❌ Модуль не найден в базе Limoka: <code>{path}</code></blockquote>",
        "watcher_critical": "<blockquote>❌ Критическая ошибка: {error}</blockquote>",
        "tags": {
            "herokutrusted": "Heroku Trusted",
            "hikkatrusted": "Hikka Trusted",
            "nonactive": "Неактивный репозиторий",
            "nonlongermaintained": "Неподдерживаемый репозиторий",
            "newbie": "Новичок",
        },
        "indexing_in_progress": (
            "<blockquote>\u26a0\ufe0f База данных занята, "
            "попробуйте снова через несколько секунд. "
            "Если ошибка сохраняется, попробуйте "
            "удалить limoka_index в корневой папке юзербота. "
            "Если ошибка сохраняется снова, сообщите разработчикам</blockquote>"
        ),
        "body_page": "Команды",
        "install_failed": "Установка не удалась. Проверьте логи для деталей.",
        "install_succeeded": "Модуль успешно установлен!",
        "update_available": (
            "🔔 <b>Доступно новое обновление!</b>\n\n"
            "Новая версия Limoka {version} уже доступна. Пожалуйста, обновитесь для лучшей производительности, исправления багов и новых функций.\n"
            "Нажмите кнопку ниже, чтобы обновить модуль."
        ),
        "no_updates_available": "<blockquote>❌ Нет доступных обновлений. У вас установлена последняя версия Limoka.</blockquote>",
        "module_update_available": "<blockquote>🔔 Уведомление об обновлении модуля было отправлено, проверьте @{bot}.</blockquote>",
        "index_update_started": "<blockquote>🔄 Обновление индекса модулей Limoka началось. Это может занять несколько минут. Пожалуйста, подождите...</blockquote>",
        "index_update_failed": "<blockquote>❌ Не удалось обновить индекс модулей Limoka. Пожалуйста, попробуйте снова позже. Если ошибка сохраняется, сообщите разработчикам</blockquote>",
        "index_update_success": "<blockquote>✅ Индекс модулей Limoka успешно обновлен!</blockquote>",
        "update_check_started": "<blockquote>🔍 Проверка обновлений Limoka...</blockquote>",
        "_cls_doc": "Модули теперь в одном месте с простым и удобным поиском!",
    }

    def __init__(self):
        self.api = APIClient()
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "limokaurl",
                "https://raw.githubusercontent.com/MuRuLOSE/limoka/refs/heads/main/",
                lambda: "Mirror (doesn't work): https://raw.githubusercontent.com/MuRuLOSE/limoka-mirror/refs/heads/main/",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "external_install_allowed",
                True,
                lambda: "If enabled, module installation can be handled via external Limoka bot (@limoka_bbot) for better reliability.",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "filter_newbies_modules",
                False,
                lambda: "If enabled, modules from developers with newbies tag will be not shown.",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "auto_update_check",
                True,
                lambda: "If enabled, Limoka will periodically check for updates and notify you when a new version is available.",
                validator=loader.validators.Boolean(),
            )
        )
        self.name = self.strings["name"]
        self._invalid_banners = set()
        self._bot_username = "limoka_bbot"
        self._base_url = self.config["limokaurl"]
        self._self_bot_username = None

        self.SEARCH_STATES = {
            "no_banner": "no_banner",
            "global_search": "global_search",
            "not_found": "not_found",
            "filter_select": "filter_select",
        }

        self.state_banners = {
            "no_banner": "https://raw.githubusercontent.com/MuRuLOSE/hikka-assets/refs/heads/main/Limoka%20-%20No%20banner.png",
            "global_search": "https://raw.githubusercontent.com/MuRuLOSE/hikka-assets/main/Limoka%20-%20Global%20Search.png",
            "not_found": "https://raw.githubusercontent.com/MuRuLOSE/hikka-assets/main/Limoka%20-%20Not%20Found.png",
            "filter_select": "https://raw.githubusercontent.com/MuRuLOSE/hikka-assets/main/Limoka%20-%20Categories.png",
        }

    def _filter_newbies(self, modules: Dict[str, Any]) -> Dict[str, Any]:
        """[DEPRECATED] Use ModuleRepository.apply_newbie_filter instead."""
        return self.repository.apply_newbie_filter(self.config.get("filter_newbies_modules", False))
    
    @loader.loop(interval=3600*24)
    async def periodic_update_check(self):
        """Periodically check for module updates if auto_update_check is enabled."""
        if self.config["auto_update_check"]:
            await self.check_for_module_update()
    
    async def check_for_module_update(self):
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(self._base_url + "Limoka.py", timeout=10) as response:
                        if response.status == 200:
                            version = _parse_version_from_source(await response.text())
                            if version is not None and version > __version__:
                                markup = InlineKeyboardMarkup(
                                    inline_keyboard=[
                                        [
                                            InlineKeyboardButton(
                                                text=self.strings.get("install_button", "Install"),
                                                callback_data="limoka:update_module"
                                            )
                                        ]
                                    ]
                                )
                                await self.inline.bot.send_message(
                                    self._tg_id,
                                    self.strings["update_available"].format(version='.'.join(str(v) for v in version)),
                                    reply_markup=markup
                                )
                                return True
                            return False
                except Exception as e:
                    logger.error(f"Error checking for module update: {e}")

    @loader.callback_handler()
    async def callback_handler(self, call: BotInlineCall):
        if call.data == "limoka:update_module":
            result = await self._install_module_limoka()
            call.as_(self.inline.bot)
            if result:
                await call.answer(f"✅ {self.strings['install_succeeded']}")
            else:
                await call.answer(f"❌ {self.strings['install_failed']}")


    def _create_search_session(
        self,
        state: str,
        query: str = "",
        filters: Optional[Dict[str, List[str]]] = None,
        results: Optional[List[str]] = None,
        current_index: int = 0,
    ) -> Dict[str, Any]:
        """Create a search session dictionary to track state across callbacks.

        Args:
            state: Current search state (one of SEARCH_STATES values)
            query: Current search query
            filters: Active category filters
            results: Search results list
            current_index: Index of current result being displayed
            banner_url: Banner image URL for current state

        Returns:
            Dictionary containing the complete session state
        """
        return {
            "state": state,
            "query": query,
            "filters": filters or {},
            "results": results or [],
            "current_index": current_index,
        }

    def _get_banner_for_state(self, state: str) -> str:
        return self.state_banners.get(state)

    async def client_ready(self, client, db):
        """Initialize client and load data."""
        self.client: TelegramClient = client
        self.db = db
        self.api = APIClient()
        self.schema = Schema(
            title=TEXT(stored=True), path=ID(stored=True), content=TEXT(stored=True)
        )
        os.makedirs("limoka_search", exist_ok=True)
        if not os.path.exists("limoka_search/index"):
            self.ix = create_in("limoka_search", self.schema)
        else:
            self.ix = open_dir("limoka_search")
        
        self._history = self.pointer("history", [])
        raw_modules = (await self.api.fetch_json(self._base_url, "modules.json")).get("modules", {})
        raw_repos = (await self.api.fetch_json(self._base_url, "repositories.json")).get("repositories", [])
        
        repositories = {repo["url"]: repo for repo in raw_repos}
        self.repository = ModuleRepository(raw_modules, repositories)
        self.modules = self.repository.apply_newbie_filter(self.config["filter_newbies_modules"])
        
        self._self_bot_username = (await self.inline.bot.get_me()).username
        self.formatter = CommandFormatter(self.strings, self._self_bot_username, self.get_prefix())
        self.content_builder = ModuleContentBuilder(self.strings, self.formatter, self.repository)
        
        self._service_bot_id = (await self.client.get_entity(self._bot_username)).id

        loop = asyncio.get_running_loop()
        self.ix_task = loop.run_in_executor(None, lambda: asyncio.run(self._update_index()))
        
        if self.config["external_install_allowed"]:
            try:
                message = await self.client.get_messages(self._bot_username, limit=1)
                if not message:
                    message = await self.client.send_message(self._bot_username, "/start")
                    await message.delete()
                    await self.client(
                        functions.messages.DeleteHistoryRequest(
                            peer=self._bot_username,
                            max_id=0,
                            just_clear=True,
                            revoke=True,
                        )
                    )
            except YouBlockedUserError:
                logger.warning(
                    f"Please unblock {self._bot_username} to enable external installation feature."
                )

    @loader.loop(interval=3600)
    async def _update_modules_loop(self):
        """Periodically update modules list and rebuild index."""
        await self.api.fetch_json(self._base_url, "modules.json")
        self.modules = self.repository.apply_newbie_filter(
            self.config.get("filter_newbies_modules", False)
        )
        await self._update_index()

    async def _update_index(self):
        """Rebuild full-text search index from modules."""
        try:
            writer = self.ix.writer()
            for module_path, module_data in self.modules.items():
                writer.add_document(
                    title=module_data["name"],
                    path=module_path,
                    content=module_data["name"]
                    + " "
                    + (
                        module_data.get("description", "")
                        + " "
                        + (
                            (module_data.get("meta", {}).get("developer") or "")
                        )
                    ),
                )
                for func in module_data.get("commands", []):
                    for command, description in func.items():
                        writer.add_document(
                            title=module_data["name"],
                            path=module_path,
                            content=f"{command} {description}",
                        )
            writer.commit()
        except LockError:
            folder = os.path.join(BASE_DIR, "limoka_search")
            if os.path.commonpath([folder, BASE_DIR]) == BASE_DIR and os.path.exists(folder):
                shutil.rmtree(folder)
                await self._update_index()
            else:
                logger.error(f"Skipping unsafe rmtree for {folder}")

    async def _validate_url(self, url: str) -> Optional[str]:
        logger.debug(f"_validate_url called with: {url}")
        if not url:
            logger.warning("_validate_url: URL is empty, returning None")
            return None
        if url in self._invalid_banners:
            logger.debug(f"_validate_url: URL already in invalid_banners: {url}, returning None")
            return None
        
        # Headers to mimic a browser request
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        try:
            logger.debug(f"_validate_url: Starting validation for {url}")
            async with aiohttp.ClientSession() as session:
                ct = None
                response_status = None
                
                # Try HEAD first (more efficient)
                try:
                    logger.debug(f"_validate_url: Attempting HEAD request for {url}")
                    async with session.head(
                        url, timeout=5, allow_redirects=True, headers=headers
                    ) as response:
                        response_status = response.status
                        logger.debug(f"_validate_url: HEAD request returned status {response.status} for {url}")
                        if response.status == 200:
                            ct = response.headers.get("Content-Type", "").lower()
                            logger.debug(f"_validate_url: Content-Type from HEAD: '{ct}' for {url}")
                except (aiohttp.ClientError, asyncio.TimeoutError) as head_error:
                    logger.debug(f"_validate_url: HEAD failed ({type(head_error).__name__}), will try GET for {url}")
                
                def _is_supported_media(content_type: str) -> bool:
                    return content_type.startswith("image/") or content_type.startswith("video/mp4")

                # If HEAD didn't work or returned non-200, try GET
                if ct is None:
                    max_retries = 2
                    for attempt in range(max_retries):
                        try:
                            async with session.get(
                                url, timeout=10, headers=headers, allow_redirects=True
                            ) as response:
                                if response.status != 200:
                                    self._invalid_banners.add(url)
                                    return None
                                ct = response.headers.get("Content-Type", "").lower()
                                
                                # Try to get MIME if Content-Type is missing
                                if not ct:
                                    try:
                                        data = await response.content.read(2048)
                                        mime = filetype.guess_mime(data, mime=True)
                                        if mime and _is_supported_media(mime):
                                            return url
                                        else:
                                            self._invalid_banners.add(url)
                                            return None
                                    except Exception as mime_error:
                                        logger.error(f"_validate_url: Error reading content for MIME detection: {mime_error}")
                                break  # Success, exit retry loop
                        except (aiohttp.ClientError, asyncio.TimeoutError) as get_error:
                            if attempt < max_retries - 1:
                                await asyncio.sleep(1)  # Wait before retry
                            else:
                                self._invalid_banners.add(url)
                                return None
                
                # Check Content-Type from successful request
                if ct and _is_supported_media(ct):
                    return url
                elif ct:
                    self._invalid_banners.add(url)
                    return None
                else:
                    self._invalid_banners.add(url)
                    return None
                    
        except Exception as e:
            if url:
                self._invalid_banners.add(url)
            return None
        
    def find_userbot(self, keys: Iterable[str]) -> str | None:
        scores = defaultdict(int)

        for key in keys:
            parts = key.split(".")

            for i in range(1, len(parts)):
                prefix = ".".join(parts[:i])
                suffix = ".".join(parts[i:])

                weight = WEIGHTS.get(suffix, DEFAULT_WEIGHT)

                scores[prefix] += weight

        if not scores:
            return None

        return max(scores, key=scores.get)


    @property
    def user_lang(self) -> str:

        userbot = self.find_userbot(self.db.keys())

        if not userbot:
            logger.warning(
                "Cannot determine userbot type. "
                "Probably not FTG-like Userbot? "
                "Defaulting language to English. "
                "If this is unexpected, please report to the module developer."
            )
            return "en"
        
        return self.db.get(f"{userbot}.translations", "lang")

    def generate_commands(self, module_info, lang: str = "en"):
        """[DEPRECATED] Use CommandFormatter.format_commands instead."""
        return self.formatter.format_commands(module_info, lang)

    def _format_module_content(
        self,
        module_info: Dict[str, Any],
        query: str,
        filters: Dict[str, List[str]],
        url: str,
        include_categories: bool = True,
        module_path: Optional[str] = None,
        lang: str = "en"

    ) -> tuple:
        """[DEPRECATED] Use ModuleContentBuilder.build_content instead."""
        return self.content_builder.build_content(
            module_info, query, filters, url, include_categories, module_path, lang
        )

    def _build_navigation_markup(self, session: Dict[str, Any]) -> list:
        result = session["results"]
        index = session["current_index"]

        page = index + 1
        markup = [
            [
                {
                    "text": "⏪" if index > 0 else "🚫",
                    "callback": self._previous_page if index > 0 else self._inline_void,
                    "args": (session,) if index > 0 else (),
                },
                {"text": f"{page}/{len(result)}", "callback": self._inline_void},
                {
                    "text": "⏩" if index + 1 < len(result) else "🚫",
                    "callback": (
                        self._next_page
                        if index + 1 < len(result)
                        else self._inline_void
                    ),
                    "args": (session,) if index + 1 < len(result) else (),
                },
            ],
            [
                {
                    "text": "🔍 " + self.strings["filter_menu"].split(":")[0],
                    "callback": self._display_filter_menu,
                    "args": (session,),
                },
                {
                    "text": "🔄 " + self.strings["change_query"],
                    "callback": self._enter_query,
                },
            ],
            [
                {
                    "text": self.strings["global_button"],
                    "callback": self._show_global_results,
                    "args": (session,),
                },
            ],
        ]
        markup.append(
            [{"text": self.strings.get("close", "❌ Close"), "action": "close", "style": "danger"}]
        )
        return markup

    def _build_module_markup(
        self,
        session: Dict[str, Any],
        body_pages: List[str],
        page_body: int,
        module_path: str,
    ) -> list:
        result = session["results"]
        index = session["current_index"]

        markup = []
        if len(body_pages) > 1:
            markup.append(
                [
                    {
                        "text": "◀️" if page_body > 0 else "🚫",
                        "callback": (
                            self._previous_body_page
                            if page_body > 0
                            else self._inline_void
                        ),
                        "args": (
                            (session, module_path, page_body) if page_body > 0 else ()
                        ),
                    },
                    {
                        "text": f"{self.strings['body_page']} {page_body + 1}/{len(body_pages)}",
                        "callback": self._inline_void,
                    },
                    {
                        "text": "▶️" if page_body + 1 < len(body_pages) else "🚫",
                        "callback": (
                            self._next_body_page
                            if page_body + 1 < len(body_pages)
                            else self._inline_void
                        ),
                        "args": (
                            (session, module_path, page_body)
                            if page_body + 1 < len(body_pages)
                            else ()
                        ),
                    },
                ]
            )
        page = index + 1
        markup.append(
            [
                {
                    "text": "⏪" if index > 0 else "🚫",
                    "callback": self._previous_page if index > 0 else self._inline_void,
                    "args": (session,) if index > 0 else (),
                },
                {"text": f"{page}/{len(result)}", "callback": self._inline_void},
                {
                    "text": "⏩" if index + 1 < len(result) else "🚫",
                    "callback": (
                        self._next_page
                        if index + 1 < len(result)
                        else self._inline_void
                    ),
                    "args": (session,) if index + 1 < len(result) else (),
                },
            ]
        )
        markup.append(
            [
                {
                    "text": "🔍 " + self.strings["filter_menu"].split(":")[0],
                    "callback": self._display_filter_menu,
                    "args": (session,),
                },
                {
                    "text": "🔄 " + self.strings["change_query"],
                    "callback": self._enter_query,
                },
            ]
        )
        markup.append(
            [
                {
                    "text": self.strings["global_button"],
                    "callback": self._show_global_results,
                    "args": (session,),
                },
            ]
        )
        markup.append(
            [
                {
                    "text": self.strings["install_button"],
                    "callback": self._install_module,
                    "args": (session,),
                },
            ]
        )
        markup.append(
            [{"text": self.strings.get("close", "❌ Close"), "action": "close", "style": "danger"}]
        )
        return markup

    async def _safe_display(
        self,
        message_or_call: Union[Message, InlineCall],
        text: str,
        markup: list,
        photo: Optional[Any] = None,
    ):
        try:
            if message_or_call is None:
                logger.error("message_or_call is None in _safe_display")
                return
            if isinstance(message_or_call, Message):
                # WORKAROUND: Telegram doesn't show premium emojis in first call,
                # until it's edited. Firstly sending something, than fixing.
                if photo is not None:
                    msg = await self.inline.form(
                        text="🍋",
                        message=message_or_call,
                        reply_markup=[[{"text": "🍋", "action": "close"}]],
                        photo=photo,
                    )
                    await msg.edit(text=text, reply_markup=markup, photo=photo)
                else:
                    msg = await self.inline.form(
                        text="🍋", message=message_or_call, reply_markup=[[{"text": "🍋", "action": "close"}]]
                    )
                    await msg.edit(text=text, reply_markup=markup)
            else:
                if photo is not None:
                    await message_or_call.edit(
                        text=text, reply_markup=markup, photo=photo
                    )
                else:
                    await message_or_call.edit(text=text, reply_markup=markup)
        except (BadRequest, WebpageMediaEmptyError) as e:
            logger.exception(f"Error in _safe_display: {e}")
            if isinstance(message_or_call, Message):
                await utils.answer(message_or_call, self.strings["display_error"])
            elif hasattr(message_or_call, "edit"):
                await message_or_call.edit(self.strings["display_error"])

    async def _display_module(
        self,
        message_or_call: Union[Message, InlineCall],
        module_info: Dict[str, Any],
        module_path: str,
        session: Dict[str, Any],
        page_body: int = 0,
    ):
        try:
            query = session["query"]
            filters = session["filters"]

            lang = self.user_lang
            module_banner_raw = module_info.get("meta", {}).get("banner")
            photo = await self._validate_url(module_banner_raw)

            if not photo:
                state_banner_raw = self._get_banner_for_state("no_banner")
                photo = await self._validate_url(state_banner_raw)

            header, body_pages, footer, categories_text = self._format_module_content(
                module_info,
                query,
                filters,
                include_categories=True,
                module_path=module_path,
                lang=lang,
                url=self._base_url
            )
            current_body = body_pages[min(page_body, len(body_pages) - 1)]
            full_message = header + current_body + footer + categories_text

            markup = self._build_module_markup(
                session, body_pages, page_body, module_path
            )

            await self._safe_display(message_or_call, full_message, markup, photo)
        except Exception as e:
            logger.exception(f"Error in _display_module: {e}")
            if isinstance(message_or_call, Message):
                await utils.answer(message_or_call, self.strings["error_occurred"])
            elif hasattr(message_or_call, "edit"):
                await message_or_call.edit(self.strings["error_occurred"])

    async def _previous_body_page(
        self,
        call: InlineCall,
        session: Dict[str, Any],
        module_path: str,
        page_body: int,
    ):
        module_info = self.modules[module_path]
        new_page_body = max(page_body - 1, 0)
        await self._display_module(
            call, module_info, module_path, session, page_body=new_page_body
        )

    async def _next_body_page(
        self,
        call: InlineCall,
        session: Dict[str, Any],
        module_path: str,
        page_body: int,
    ):
        module_info = self.modules[module_path]
        query = session["query"]
        filters = session["filters"]
        header, body_pages, footer, categories_text = self._format_module_content(
            module_info,
            query,
            filters,
            include_categories=True,
            module_path=module_path,
            lang=self.user_lang,
            url=self.config["limokaurl"]
        )
        new_page_body = min(page_body + 1, len(body_pages) - 1)
        await self._display_module(
            call, module_info, module_path, session, page_body=new_page_body
        )

    async def _install_module(self, call: InlineCall, session: Dict[str, Any]):
        try:
            loader = self.lookup("Loader")
            await loader.download_and_install(f"{self.config['limokaurl']}{session['results'][session['current_index']]}")
            if getattr(loader, "fully_loaded", False):
                loader.update_modules_in_db()

        except Exception:
            await call.answer(f"❌ {self.strings['install_failed']}", alert=True)
        else:
            await call.answer(f"✅ {self.strings['install_succeeded']}", alert=True)

    async def _install_module_limoka(self):
        try:
            loader = self.lookup("Loader")
            await loader.download_and_install(f"{self.config['limokaurl']}Limoka.py")
            if getattr(loader, "fully_loaded", False):
                loader.update_modules_in_db()
            return True
        except Exception as e:
            logger.exception(f"Error updating Limoka module: {e}")
            return False

    async def _display_filter_menu(self, call: InlineCall, session: Dict[str, Any]):
        query = session["query"]
        current_filters = session["filters"]

        categories = current_filters.get("category", [])
        filters_text = self.strings["selected_categories"].format(
            categories=(
                ", ".join(categories) if categories else self.strings["no_category"]
            )
        )
        markup = [
            [
                {
                    "text": self.strings["filter_cat"],
                    "callback": self._select_category,
                    "args": (session,),
                },
            ],
            [
                {
                    "text": self.strings["apply_filters"],
                    "callback": self._apply_filters,
                    "args": (session,),
                },
                {
                    "text": self.strings["clear_filters"],
                    "callback": self._clear_filters,
                    "args": (session,),
                },
            ],
            [
                {
                    "text": self.strings["back_to_results"],
                    "callback": self._show_results,
                    "args": (session, True),
                },
            ],
            [{"text": self.strings.get("close", "❌ Close"), "action": "close", "style": "danger"}],
        ]
        text = self.strings["filter_menu"].format(query=query) + f"\n{filters_text}"
        await call.edit(
            text, reply_markup=markup, photo=self._get_banner_for_state("filter_select")
        )

    async def _select_category(self, call: InlineCall, session: Dict[str, Any]):
        """Display category selection menu."""
        query = session["query"]
        current_filters = session["filters"]

        categories = self.repository.get_all_categories()
        if not categories:
            await call.edit(
                self.strings["no_categories"],
                reply_markup=[
                    [
                        {
                            "text": self.strings["back"],
                            "callback": self._display_filter_menu,
                            "args": (session,),
                        }
                    ]
                ],
            )
            return
        selected_categories = current_filters.get("category", [])
        buttons = []
        row = []
        for i, cat in enumerate(categories):
            button_text = (
                self.strings["category"].format(category=cat)
                if "category" in self.strings
                else f"📁 {cat}"
            )
            if cat in selected_categories:
                button_text = "✅ " + button_text

            row.append(
                {
                    "text": button_text,
                    "callback": self._toggle_category,
                    "args": (session, cat),
                }
            )
            if (i + 1) % 3 == 0 or i == len(categories) - 1:
                buttons.append(row)
                row = []
        buttons.append(
            [
                {
                    "text": self.strings["back"],
                    "callback": self._display_filter_menu,
                    "args": (session,),
                }
            ]
        )
        buttons.append(
            [{"text": self.strings.get("close", "❌ Close"), "action": "close", "style": "danger"}]
        )
        text = self.strings["select_category"].format(query=query)
        await call.edit(text, reply_markup=buttons)

    async def _toggle_category(
        self, call: InlineCall, session: Dict[str, Any], category: str
    ):
        query = session["query"]
        current_filters = session["filters"]

        new_filters = current_filters.copy()
        selected_categories = new_filters.get("category", [])
        if category in selected_categories:
            selected_categories.remove(category)
        else:
            selected_categories.append(category)
        if selected_categories:
            new_filters["category"] = selected_categories
        else:
            new_filters.pop("category", None)
        new_session = session.copy()
        new_session["filters"] = new_filters
        await self._select_category(call, new_session)

    async def _apply_filters(self, call: InlineCall, session: Dict[str, Any]):
        await self._show_results(call, session, from_filters=True)

    async def _clear_filters(self, call: InlineCall, session: Dict[str, Any]):
        new_session = session.copy()
        new_session["filters"] = {}
        await self._show_results(call, new_session, from_filters=True)

    async def _show_results(
        self, call: InlineCall, session: Dict[str, Any], from_filters: bool = False
    ):
        """Display search results with optional category filtering."""
        query = session["query"]
        filters = session["filters"]

        searcher = SearchIndex(query.lower(), self.ix)
        try:
            result = searcher.search()
        except Exception:
            await call.edit(self.strings["?"], reply_markup=[])

            return
        if not result:
            markup = (
                [
                    [
                        {
                            "text": self.strings["back"],
                            "callback": self._display_filter_menu,
                            "args": (session,),
                        }
                    ]
                ]
                if from_filters
                else []
            )
            markup.append(
                [{"text": self.strings.get("close", "❌ Close"), "action": "close", "style": "danger"}]
            )
            await call.edit(
                self.strings["404"].format(query=query), reply_markup=markup
            )
            return
        if filters.get("category"):
            filtered_result = [
                path
                for path in result
                if any(
                    cat in self.modules.get(path, {}).get("category", ["No category"])
                    for cat in filters["category"]
                )
            ]
        else:
            filtered_result = result
        if not filtered_result:
            markup = (
                [
                    [
                        {
                            "text": self.strings["back"],
                            "callback": self._display_filter_menu,
                            "args": (session,),
                        }
                    ]
                ]
                if from_filters
                else []
            )
            markup.append(
                [{"text": self.strings.get("close", "❌ Close"), "action": "close", "style": "danger"}]
            )
            await call.edit(
                self.strings["404"].format(query=query), reply_markup=markup
            )
            return
        module_path = filtered_result[0]
        module_info = self.modules[module_path]

        display_session = self._create_search_session(
            state=self.SEARCH_STATES["global_search"],
            query=query,
            filters=filters,
            results=filtered_result,
            current_index=0,
        )
        await self._display_module(call, module_info, module_path, display_session, 0)

    async def _enter_query_handler(
        self, call_or_query, query: Optional[str] = None, *args, **kwargs
    ):
        call = None
        if query is None and isinstance(call_or_query, str):
            query = call_or_query
            for a in args:
                if hasattr(a, "edit") or isinstance(a, Message):
                    call = a
                    break
        else:
            call = call_or_query
        if call is None:
            logger.error("_enter_query_handler: missing call/context")
            return
        if not query:
            await call.edit(
                self.strings["?"],
                reply_markup=[
                    [
                        {
                            "text": "🔄 " + self.strings["change_query"],
                            "callback": self._enter_query,
                        }
                    ]
                ],
            )
            return
        if len(query) <= 1:
            await call.edit(
                self.strings["?"],
                reply_markup=[
                    [
                        {
                            "text": "🔄 " + self.strings["change_query"],
                            "callback": self._enter_query,
                        }
                    ]
                ],
            )
            return
        try:
            result = SearchIndex(query.lower(), self.ix).search()
        except Exception:
            await call.edit(
                self.strings["?"],
                reply_markup=[
                    [
                        {
                            "text": "🔄 " + self.strings["change_query"],
                            "callback": self._enter_query,
                        }
                    ]
                ],
            )
            return
        if not result:
            await call.edit(
                self.strings["404"].format(query=query),
                reply_markup=[
                    [
                        {
                            "text": "🔄 " + self.strings["change_query"],
                            "callback": self._enter_query,
                        }
                    ],
                    [
                        {
                            "text": self.strings.get("close", "❌ Close"),
                            "action": "close",
                            "style": "danger",
                        }
                    ],
                ],
            )
            return
        module_path = result[0]
        module_info = self.modules[module_path]

        # Create session for displaying module
        display_session = self._create_search_session(
            state=self.SEARCH_STATES["global_search"],
            query=query,
            filters={},
            results=result,
            current_index=0,
        )
        await self._display_module(call, module_info, module_path, display_session, 0)

    async def _enter_query(self, call: InlineCall, query: Optional[str] = None):
        markup = [
            [
                {
                    "text": "✍️ " + self.strings["enter_query"],
                    "input": self.strings["enter_query"],
                    "handler": self._enter_query_handler,
                }
            ],
            [
                {
                    "text": self.strings["back_to_results"],
                    "callback": self._show_results,
                    "args": (
                        self._create_search_session(
                            state=self.SEARCH_STATES["global_search"],
                            query=query or "",
                            filters={},
                        ),
                    ),
                }
            ],
            [
                {
                    "text": self.strings.get("close", "❌ Close"),
                    "action": "close",
                    "style": "danger",
                }
            ],
        ]
        await call.edit(self.strings["enter_query"], reply_markup=markup)

    async def _show_global_results(self, call: InlineCall, session: Dict[str, Any]):
        query = session["query"]

        try:
            result = SearchIndex(query.lower(), self.ix).search()
        except Exception:
            await call.edit(self.strings["?"], reply_markup=[])
            return
        if not result:
            await call.edit(
                self.strings["404"].format(query=query),
                reply_markup=[
                    [
                        {
                            "text": "🔄 " + self.strings["change_query"],
                            "callback": self._enter_query,
                        }
                    ]
                ],
            )
            return
        text = self.strings["global_search"].format(
            query=html.escape(query), count=len(result)
        )
        buttons = []
        for i, path in enumerate(result[:15]):
            info = self.modules.get(path)
            if not info:
                continue
            name = info.get("name", "Unknown")

            global_session = self._create_search_session(
                state=self.SEARCH_STATES["global_search"],
                query=query,
                filters={},
                results=result,
                current_index=i,
            )
            buttons.append(
                [
                    {
                        "text": f"{i+1}. {name}",
                        "callback": self._display_module_from_global,
                        "args": (path, global_session),
                    }
                ]
            )
        buttons.append(
            [{"text": self.strings["change_query"], "callback": self._enter_query}]
        )
        await call.edit(text=text[:4096], reply_markup=buttons)

    async def _display_module_from_global(
        self, call: InlineCall, module_path: str, session: Dict[str, Any]
    ):
        module_info = self.modules[module_path]
        await self._display_module(call, module_info, module_path, session, 0)

    async def _next_page(self, call: InlineCall, session: Dict[str, Any]):
        result = session["results"]
        index = session["current_index"]

        if index + 1 >= len(result):
            await call.answer(self.strings["last_page"])
            return
        index += 1
        module_path = result[index]
        module_info = self.modules[module_path]

        new_session = session.copy()
        new_session["current_index"] = index
        await self._display_module(call, module_info, module_path, new_session, 0)

    async def _previous_page(self, call: InlineCall, session: Dict[str, Any]):
        result = session["results"]
        index = session["current_index"]

        if index - 1 < 0:
            await call.answer(self.strings["first_page"])
            return
        index -= 1
        module_path = result[index]
        module_info = self.modules[module_path]

        new_session = session.copy()
        new_session["current_index"] = index
        await self._display_module(call, module_info, module_path, new_session, 0)

    async def _inline_void(self, call: InlineCall):
        await call.answer()

    @loader.command(ru_doc="[запрос / ничего] — Поиск модулей")
    async def limokacmd(self, message: Message):
        """[query / nothing] - Search modules"""
        args = utils.get_args_raw(message)
        lock_path = os.path.join(BASE_DIR, "limoka_search", "index.lock")

        if os.path.exists(lock_path):
            await utils.answer(message, self.strings["indexing_in_progress"])
            return
        if not args:
            markup = [
                [
                    {
                        "text": "✍️ " + self.strings["enter_query"],
                        "input": self.strings["enter_query"],
                        "handler": self._enter_query_handler,
                    }
                ],
                [
                    {
                        "text": self.strings["global_button"],
                        "callback": self._show_global_form,
                        "args": (message,),
                    }
                ],
            ]
            markup.append(
                [{"text": self.strings.get("close", "❌ Close"), "action": "close", "style": "danger"}]
            )
            # WORKAROUND: Telegram doesnt show emojis in inline forms as expected,
            # until the form is edited. Sending with lemon, then fixing.
            workaround_markup = [
                [
                    {
                        "text": "🍋 Enter query",
                        "input": "Enter query",
                        "handler": self._enter_query_handler,
                    }
                ],
                [
                    {
                        "text": "🍋 Results",
                        "callback": self._show_global_form,
                        "args": (message,),
                    }
                ],
            ]
            workaround_markup.append(
                [{"text": "🍋 Close", "action": "close", "style": "danger"}]
            )
            msg = await self.inline.form(
                text="🍋 Limoka\n🍋 Enter query",
                message=message,
                reply_markup=workaround_markup,
            )
            await msg.edit(
                text=self.strings["start_search_form"],
                reply_markup=markup,
            )
            return
        history = self.get("history", [])
        if len(history) >= 10:
            history = history[-9:]
        history.append(args)
        self.set("history", history)
        await utils.answer(
            message,
            self.strings["wait"].format(
                count=len(self.modules),
                fact=random.choice(self.strings["facts"]),
                query=args,
            ),
        )
        try:
            result = SearchIndex(args.lower(), self.ix).search()
        except Exception as e:
            logger.exception(f"Error occurred while searching: {e}")
            return await utils.answer(message, self.strings["?"])
        if not result:
            return await utils.answer(message, self.strings["404"].format(query=args))
        module_path = result[0]
        module_info = self.modules[module_path]

        # Create session for displaying module
        display_session = self._create_search_session(
            state=self.SEARCH_STATES["global_search"],
            query=args,
            filters={},
            results=result,
            current_index=0,
        )
        await self._display_module(
            message, module_info, module_path, display_session, 0
        )

    @loader.command(ru_doc="— Обновить индекс ")
    async def updateindex(self, message: Message):
        """— Update search index"""
        await utils.answer(message, self.strings["index_update_started"])
        try:
            await self._update_index()
        except Exception as e:
            logger.exception(f"Error updating index: {e}")
            await utils.answer(message, self.strings["index_update_failed"])
        else:
            await utils.answer(message, self.strings["index_update_success"])

    @loader.command(ru_doc="— Проверить наличие обновлений модуля")
    async def limokaupdatecmd(self, message: Message):
        """— Check for module updates"""
        await utils.answer(message, self.strings["checking_for_updates"])

        is_update_available = await self.check_for_module_update()
        if is_update_available:
            await utils.answer(message, self.strings["module_update_available"].format(bot=self._self_bot_username))
        else:
            await utils.answer(message, self.strings["no_updates_available"])

    async def _show_global_form(self, call: InlineCall, message: Message):
        markup = [
            [
                {
                    "text": "✍️ " + self.strings["enter_query"],
                    "input": self.strings["enter_query"],
                    "handler": self._global_search_handler,
                    "args": (message,),
                }
            ],
            [
                {
                    "text": "🔙 " + self.strings["back"],
                    "callback": self._inline_void,
                }
            ],
            [
                {
                    "text": self.strings.get("close", "❌ Close"),
                    "action": "close",
                    "style": "danger",
                }
            ],
        ]
        await call.edit(self.strings["global_search_form"], reply_markup=markup)

    async def _global_search_handler(
        self, call: InlineCall, query: str, message: Message, *args, **kwargs
    ):
        global_session = self._create_search_session(
            state=self.SEARCH_STATES["global_search"],
            query=query,
            filters={},
            results=[],
            current_index=0,
        )  # idk what is that crap but it works lol
        if len(query) <= 1:
            await call.edit(
                self.strings["?"],
                reply_markup=[
                    [
                        {
                            "text": "🔄 " + self.strings["change_query"],
                            "callback": lambda c: self._show_global_form(c, message),
                        }
                    ],
                    [
                        {
                            "text": self.strings.get("close", "❌ Close"),
                            "action": "close",
                            "style": "danger",
                        }
                    ],
                ],
            )
            return
        try:
            result = SearchIndex(query.lower(), self.ix).search()
        except Exception:
            await call.edit(
                self.strings["?"],
                reply_markup=[
                    [
                        {
                            "text": "🔄 " + self.strings["change_query"],
                            "callback": lambda c: self._show_global_form(c, message),
                        }
                    ],
                    [
                        {
                            "text": self.strings.get("close", "❌ Close"),
                            "action": "close",
                            "style": "danger",
                        }
                    ],
                ],
            )
            return
        if not result:
            await call.edit(
                self.strings["404"].format(query=query),
                reply_markup=[
                    [
                        {
                            "text": "🔄 " + self.strings["change_query"],
                            "callback": lambda c: self._show_global_form(c, message),
                        }
                    ],
                    [
                        {
                            "text": self.strings.get("close", "❌ Close"),
                            "action": "close",
                            "style": "danger",
                        }
                    ],
                ],
            )
            return
        text = self.strings["global_search"].format(
            query=html.escape(query), count=len(result)
        )
        buttons = []
        for i, path in enumerate(result[:15]):
            info = self.modules.get(path)
            if not info:
                continue
            name = info.get("name", "Unknown")
            buttons.append(
                [
                    {
                        "text": f"{i+1}. {name}",
                        "callback": self._display_module_from_global,
                        "args": (path, global_session),
                    }
                ]
            )
        buttons.append(
            [
                {
                    "text": "🔄 " + self.strings["change_query"],
                    "callback": lambda c: self._show_global_form(c, message),
                }
            ]
        )
        buttons.append(
            [{"text": self.strings.get("close", "❌ Close"), "action": "close", "style": "danger"}]
        )
        await call.edit(text=text[:4096], reply_markup=buttons)

    @loader.command(ru_doc="[clear] — Показать или очистить историю поиска")
    async def lshistorycmd(self, message: Message):
        """[clear] - Show or clear search history"""
        args = utils.get_args_raw(message).strip().lower()
        if args == "clear":
            self.set("history", [])
            await utils.answer(message, self.strings["history_cleared"])
            return
        if args:
            await utils.answer(message, self.strings["invalid_history_arg"])
            return
        history = self.get("history", [])
        if not history:
            await utils.answer(message, self.strings["empty_history"])
            return
        formatted_history = [
            f"{i+1}. <code>{utils.escape_html(h)}</code>"
            for i, h in enumerate(history[-10:])
        ]
        await utils.answer(
            message,
            self.strings["history"].format(history="\n".join(formatted_history)),
        )

    # @loader.watcher(from_dl=False)
    # async def secure_install_watcher(self, message: Message):
    #     if not message.text:
    #         return
    #     if not hasattr(message, "from_id") or not message.from_id:
    #         return
    #     sender_id = None
    #     if hasattr(message.from_id, "user_id"):
    #         sender_id = message.from_id.user_id
    #     elif hasattr(message.from_id, "channel_id"):
    #         sender_id = message.from_id.channel_id
    #     if sender_id != self._service_bot_id:
    #         # logger.debug("Message not from official bot, ignoring")
    #         return
    #     if not self.config["external_install_allowed"]:
    #         return
    #     try:
    #         clean_text = (
    #             getattr(message, "raw_text", None)
    #             or getattr(message, "message", None)
    #             or message.text
    #             or ""
    #         )
    #         if message.entities:
    #             from html import unescape

    #             clean_text = unescape(clean_text)
    #         clean_text = re.sub(r"<[^>]+>", "", clean_text)
    #         match = re.search(r"#limoka:([^\s\"'<>]+)", clean_text)
    #         if not match:
    #             logger.debug(
    #                 "No #limoka tag found in cleaned text; leaving original message intact"
    #             )
    #             return
    #         tag_content = match.group(1)
    #         parts = tag_content.split(":", 1)
    #         if len(parts) != 2:
    #             logger.error("Invalid tag format after cleaning")
    #             await utils.answer(message, self.strings["watcher_invalid_format"])
    #             return
    #         module_path, signature_hex = parts
    #         module_path = re.sub(r"[<>\"']", "", module_path).strip()
    #         if module_path.startswith("href="):
    #             module_path = module_path[5:].strip('"').strip("'")
    #         if module_path not in self.modules:
    #             found = False
    #             for db_path in self.modules.keys():
    #                 if module_path in db_path or db_path in module_path:
    #                     module_path = db_path
    #                     found = True
    #                     break
    #             if not found:
    #                 logger.warning(f"Module not found after cleanup: {module_path}")
    #                 await utils.answer(
    #                     message,
    #                     self.strings["watcher_module_not_found"].format(
    #                         path=html.escape(module_path)
    #                     ),
    #                 )
    #                 return
    #         try:
    #             import base64
    #             from cryptography.hazmat.primitives.asymmetric import ed25519

    #             PUB_KEY_B64 = (
    #                 "MCowBQYDK2VwAyEA1ltSnqtf3pGBuctuAYqHivCXsaRtKOVxavai7yin7ZE="
    #             )
    #             der_bytes = base64.b64decode(PUB_KEY_B64)
    #             raw_pubkey = der_bytes[-32:]
    #             module_url = self.config["limokaurl"] + module_path
    #             async with aiohttp.ClientSession() as session:
    #                 async with session.get(module_url, timeout=10) as resp:
    #                     if resp.status != 200:
    #                         logger.error(
    #                             f"Failed to fetch module for verification: {module_url} (HTTP {resp.status})"
    #                         )
    #                         await utils.answer(
    #                             message, self.strings["watcher_loader_missing"]
    #                         )
    #                         return
    #                     module_bytes = await resp.read()
    #                     sha256 = hashlib.sha256(module_bytes).hexdigest()
    #                     public_key = ed25519.Ed25519PublicKey.from_public_bytes(
    #                         raw_pubkey
    #                     )
    #                     signature = bytes.fromhex(signature_hex)
    #                     signed_payload = f"{module_path}|{sha256}".encode()
    #                     public_key.verify(signature, signed_payload)
    #         except Exception as e:
    #             logger.error(f"Signature verification failed for {module_path}: {e}")
    #             await utils.answer(message, self.strings["watcher_signature_invalid"])
    #             return
    #         loader_mod = self.lookup("loader")
    #         if not loader_mod:
    #             logger.error("Loader module not found")
    #             await utils.answer(message, self.strings["watcher_loader_missing"])
    #             return
    #         module_url = self.config["limokaurl"] + module_path
    #         status = await loader_mod.download_and_install(module_url, None)
    #         if getattr(loader_mod, "fully_loaded", False):
    #             loader_mod.update_modules_in_db()
    #         try:
    #             await message.delete()
    #         except Exception as e:
    #             logger.error(f"Failed to delete message: {e}")
    #         if status:
    #             try:
    #                 bot_peer = await self.client.get_entity(self._service_bot_id)
    #                 await self.client.send_message(
    #                     bot_peer, f"#limoka:sucsess:{message.id}"
    #                 )
    #             except Exception as e:
    #                 logger.error(f"Failed to send success confirmation: {e}")
    #         else:
    #             logger.error(f"Installation failed with status: {status}")
    #             try:
    #                 bot_peer = await self.client.get_entity(self._service_bot_id)
    #                 await self.client.send_message(
    #                     bot_peer, f"#limoka:failed:{message.id}"
    #                 )
    #             except Exception as e:
    #                 logger.error(f"Failed to send failure notification: {e}")
    #     except Exception as e:
    #         logger.exception(f"CRITICAL ERROR in secure_install_watcher: {e}")
    #         try:
    #             await utils.answer(
    #                 message, self.strings["watcher_critical"].format(error=str(e)[:100])
    #             )
    #             await asyncio.sleep(5)
    #             await message.delete()
    #         except Exception:
    #             pass