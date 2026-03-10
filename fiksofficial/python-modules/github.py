#         ______     ___  ___          _       _      
#    ____ | ___ \    |  \/  |         | |     | |     
#   / __ \| |_/ /   _| .  . | ___   __| |_   _| | ___ 
#  / / _` |  __/ | | | |\/| |/ _ \ / _` | | | | |/ _ \
# | | (_| | |  | |_| | |  | | (_) | (_| | |_| | |  __/
#  \ \__,_\_|   \__, \_|  |_/\___/ \__,_|\__,_|_|\___|
#   \____/       __/ |                                
#               |___/                                  

# На модуль распространяется лицензия "GNU General Public License v3.0"
# https://github.com/all-licenses/GNU-General-Public-License-v3.0

# meta developer: @pymodule
# requires: aiohttp

import contextlib
import logging
from datetime import datetime, timezone

import aiohttp
from herokutl.tl.functions.channels import EditAdminRequest, InviteToChannelRequest
from herokutl.tl.types import Channel, Chat, ChatAdminRights, Message

from .. import loader, utils

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
HEADERS_BASE = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

E = {
    "push":        "🔨",
    "issue_open":  "🟢",
    "issue_close": "🔴",
    "pr_open":     "🟢",
    "pr_merge":    "🟣",
    "pr_close":    "🔴",
    "release":     "🚀",
    "prerelease":  "⚠️",
}

EVENT_LABELS = {
    "push":         "🔨 Push",
    "issues":       "🐛 Issues",
    "pull_request": "🔀 Pull Requests",
    "release":      "🚀 Releases",
    "star":         "⭐ Stars",
}


@loader.tds
class GitHubMod(loader.Module):
    """GitHub repository monitor — commits, issues, PRs, releases and stars"""

    strings = {
        "name": "GitHubMonitor",
        "setup_welcome": (
            "🐙 <b>GitHub Monitor</b>\n\n"
            "Choose a destination to configure.\n"
            "Each channel/group has its own repository list and settings.\n"
            "Notifications are sent on behalf of the bot."
        ),
        "enter_dest": (
            "{icon} <b>{label} setup</b>\n\n"
            "Enter the <b>@username or ID</b> of the {label_lc}.\n"
            "The bot will be added as admin automatically."
        ),
        "dest_not_found": (
            "❌ <b>Chat not found.</b>\n\n"
            "Check the @username or ID and try again.\n"
            "Make sure you are an admin of that chat."
        ),
        "dest_configured": (
            "✅ <b>{label}</b> configured: <b>{title}</b>\n\n"
            "Now add the first repository to track\n"
            "in <code>owner/repo</code> format:"
        ),
        "bot_invite_fail": (
            "⚠️ Could not add the bot automatically.\n"
            "Please add <code>{bot}</code> as admin with <b>Post Messages</b> right manually,\n"
            "then open <code>.github</code> again."
        ),
        "dest_removed": "🗑 <b>{title}</b> removed.",
        "repo_already": "⚠️ <code>{repo}</code> is already tracked in <b>{title}</b>.",
        "repo_not_tracked": "⚠️ <code>{repo}</code> is not tracked in <b>{title}</b>.",
        "repo_not_found": "❌ Repository <code>{repo}</code> not found or inaccessible.",
        "repo_added": "✅ Added <code>{repo}</code> to <b>{title}</b>.",
        "repo_removed": "✅ Removed <code>{repo}</code> from <b>{title}</b>.",
        "no_dests": (
            "❌ <b>No destinations configured.</b>\n\n"
            "Run <code>.github</code> to set up a channel or group."
        ),
        "setup_canceled": "❌ Setup canceled.",
        "panel_title": (
            "{icon} <b>{title}</b>\n\n"
            "📦 <b>Repositories:</b> {repos}\n"
            "📣 <b>Events:</b> {events}\n"
            "⏱ <b>Interval:</b> {interval}s\n"
            "🔑 <b>Token:</b> {token}"
        ),
        "panel_repos_empty": "none",
        "interval_invalid": "❌ Enter a number between 60 and 3600.",
        "rate_limit": (
            "⚠️ <b>GitHub API rate limit.</b>\n"
            "Resets at <code>{reset}</code>.\n"
            "Set a personal token in the destination panel."
        ),
        "dests_list": "📋 <b>Configured destinations:</b>\n\n{list}",
        "notify_push_header": (
            "<b>📏 On </b>"
            "<a href='https://github.com/{repo}'><b>{repo}:{branch}</b></a>"
            "<b> new commits!</b>\n"
            "{count} commits pushed.\n"
            "<a href='{compare}'>Compare changes</a>"
        ),
        "notify_push_commit": (
            "\n<blockquote expandable><b>Commit </b>"
            "<a href='{url}'><b>#{sha}</b></a>"
            "<b> by <i>{name} (</i></b>"
            "<a href='https://github.com/{login}'><b><i>@{login}</i></b></a>"
            "<b><i>)</i></b>\n"
            "<i>{msg}</i>\n\n"
            "{files_section}"
            "{diff_section}"
            "</blockquote>"
        ),
        "notify_push_footer": "",
        "notify_push_created": "<b>🔧 Created files:</b>\n<code>{files}</code>\n\n",
        "notify_push_removed": "<b>🗑 Removed files:</b>\n<code>{files}</code>\n\n",
        "notify_push_modified": "<b>🖊 Modified files:</b>\n<code>{files}</code>\n\n",
        "notify_push_diff": "<b>⌨️ Diff:</b>\n➕ {added}\n➖ {removed}\n",
        "notify_push_empty": (
            "<b>📏 On </b>"
            "<a href='https://github.com/{repo}'><b>{repo}:{branch}</b></a>"
            "<b> new empty push</b>"
        ),
        "notify_issue": (
            "<b>{e} On </b><a href='{url}'><b>{repo}</b></a>"
            "<b> {action} issue!</b>\n\n"
            "<i>{title}</i>\n"
            "<a href='{url}'>#{num}</a> by "
            "<a href='https://github.com/{author}'><i>@{author}</i></a>"
        ),
        "notify_pr": (
            "<b>{e} On </b><a href='https://github.com/{repo}'><b>{repo}</b></a>"
            "<b> {action} pull request!</b>\n\n"
            "<i>{title}</i>\n"
            "<blockquote expandable>{body}</blockquote>\n\n"
            "User: <a href='https://github.com/{author}'><i>@{author}</i></a>\n\n"
            "<a href='{url}'>#{num}</a>"
        ),
        "notify_release": (
            "<b>{e} On </b><a href='https://github.com/{repo}'><b>{repo}</b></a>"
            "<b> {action} release!</b>\n\n"
            "🏷 <code>{tag}</code> · <b>{name}</b>\n"
            "👤 <a href='https://github.com/{author}'><i>@{author}</i></a>\n"
            "<a href='{url}'>Open release</a>"
        ),
        "notify_star_added": (
            "<b>⭐️ On </b><a href='https://github.com/{repo}'><b>{repo}</b></a>"
            "<b> added star!</b>\n\n"
            "Total stars: <i>{stars}</i>\n"
            "User: <a href='https://github.com/{user}'><i>@{user}</i></a>"
        ),
        "notify_star_removed": (
            "<b>💔 On </b><a href='https://github.com/{repo}'><b>{repo}</b></a>"
            "<b> removed star!</b>\n\n"
            "Total stars: <i>{stars}</i>\n"
            "User: <a href='https://github.com/{user}'><i>@{user}</i></a>"
        ),
        "_cfg_interval": "Default polling interval in seconds (60–3600). Overridden per destination.",
        "star_label": "⭐ Stars",
        "_cfg_token": (
            "Default GitHub token for destinations without a personal token.\n"

            "Without token: 60 req/h. With token: 5000 req/h.\n"
            "Create at: github.com/settings/tokens"
        ),
        "push_label": "🔨 Push",
        "issues_label": "🐛 Issues",
        "pull_request_label": "🔀 Pull Requests",
        "release_label": "🚀 Releases",
        "token_set": "✅ set",
        "token_not_set": "❌ not set",
        "btn_channel": "➕ Channel",
        "btn_group": "➕ Group",
        "btn_close": "✖️ Close",
        "btn_back": "◀️ Back",
        "btn_skip": "⏩ Skip",
        "btn_add_repo": "➕ Add repository",
        "btn_set_interval": "⏱ Set interval",
        "btn_set_token": "🔑 Set token",
        "btn_clear_token": "🔑 Clear token",
        "btn_remove": "🗑 Remove",
        "btn_enter_dest": "✏️ Enter {label} username / ID",
        "btn_add_repo_confirm": "✏️ Add repository",
        "input_dest": "@username or ID of the {label}",
        "input_repo": "owner/repo  (e.g. torvalds/linux)",
        "input_interval": "Interval in seconds  (60 – 3600)",
        "input_token": "GitHub Personal Access Token",
        "repo_invalid_format": "❌ Invalid format. Use <code>owner/repo</code>.",
        "checking_repo": "🔍 Checking repository...",
        "issue_opened": "opened",
        "issue_closed": "closed",
        "pr_merged": "merged",
        "pr_closed": "closed",
        "pr_opened": "opened",
        "release_prerelease": "pre-release",
        "release_published": "published",
        "dest_label_channel": "Channel",
        "dest_label_group": "Group",
    }

    strings_ru = {
        "name": "GitHubMonitor",
        "_cls_doc": "Мониторинг GitHub репозиториев — коммиты, issues, PR, релизы и звёзды",

        "setup_welcome": (
            "🐙 <b>GitHub Monitor</b>\n\n"
            "Выберите назначение для настройки.\n"
            "У каждого канала/группы свой список репозиториев и настройки.\n"
            "Уведомления отправляются от имени бота."
        ),
        "enter_dest": (
            "{icon} <b>Настройка {label_lc}а</b>\n\n"
            "Введите <b>@username или ID</b> {label_lc}а.\n"
            "Бот будет добавлен администратором автоматически."
        ),
        "dest_not_found": (
            "❌ <b>Чат не найден.</b>\n\n"
            "Проверьте @username или ID.\n"
            "Убедитесь, что вы администратор этого чата."
        ),
        "dest_configured": (
            "✅ <b>{label}</b> настроен: <b>{title}</b>\n\n"
            "Теперь добавьте первый репозиторий для отслеживания\n"
            "в формате <code>owner/repo</code>:"
        ),
        "bot_invite_fail": (
            "⚠️ Не удалось добавить бота автоматически.\n"
            "Добавьте <code>{bot}</code> вручную как администратора с правом <b>Публикация сообщений</b>,\n"
            "затем откройте <code>.github</code> снова."
        ),
        "dest_removed": "🗑 <b>{title}</b> удалён.",
        "repo_already": "⚠️ <code>{repo}</code> уже отслеживается в <b>{title}</b>.",
        "repo_not_tracked": "⚠️ <code>{repo}</code> не отслеживается в <b>{title}</b>.",
        "repo_not_found": "❌ Репозиторий <code>{repo}</code> не найден или недоступен.",
        "repo_added": "✅ Репозиторий <code>{repo}</code> добавлен в <b>{title}</b>.",
        "repo_removed": "✅ Репозиторий <code>{repo}</code> удалён из <b>{title}</b>.",
        "no_dests": (
            "❌ <b>Нет настроенных назначений.</b>\n\n"
            "Запустите <code>.github</code> чтобы добавить канал или группу."
        ),
        "setup_canceled": "❌ Настройка отменена.",
        "panel_title": (
            "{icon} <b>{title}</b>\n\n"
            "📦 <b>Репозитории:</b> {repos}\n"
            "📣 <b>События:</b> {events}\n"
            "⏱ <b>Интервал:</b> {interval} сек\n"
            "🔑 <b>Токен:</b> {token}"
        ),
        "panel_repos_empty": "нет",
        "interval_invalid": "❌ Введите число от 60 до 3600.",
        "rate_limit": (
            "⚠️ <b>GitHub API rate limit.</b>\n"
            "Сброс в <code>{reset}</code>.\n"
            "Установите токен в панели назначения."
        ),
        "dests_list": "📋 <b>Настроенные назначения:</b>\n\n{list}",
        "notify_push_header": (
            "<b>📏 На </b>"
            "<a href='https://github.com/{repo}'><b>{repo}:{branch}</b></a>"
            "<b> новые коммиты!</b>\n"
            "{count} коммитов отправлено.\n"
            "<a href='{compare}'>Сравнить изменения</a>"
        ),
        "notify_push_commit": (
            "\n<blockquote expandable><b>Коммит </b>"
            "<a href='{url}'><b>#{sha}</b></a>"
            "<b> от <i>{name} (</i></b>"
            "<a href='https://github.com/{login}'><b><i>@{login}</i></b></a>"
            "<b><i>)</i></b>\n"
            "<i>{msg}</i>\n\n"
            "{files_section}"
            "{diff_section}"
            "</blockquote>"
        ),
        "notify_push_footer": "",
        "notify_push_created": "<b>🔧 Созданные файлы:</b>\n<code>{files}</code>\n\n",
        "notify_push_removed": "<b>🗑 Удалённые файлы:</b>\n<code>{files}</code>\n\n",
        "notify_push_modified": "<b>🖊 Изменённые файлы:</b>\n<code>{files}</code>\n\n",
        "notify_push_diff": "<b>⌨️ Diff:</b>\n➕ {added}\n➖ {removed}\n",
        "notify_push_empty": (
            "<b>📏 На </b>"
            "<a href='https://github.com/{repo}'><b>{repo}:{branch}</b></a>"
            "<b> пустой push</b>"
        ),
        "notify_issue": (
            "<b>{e} На </b><a href='{url}'><b>{repo}</b></a>"
            "<b> {action} issue!</b>\n\n"
            "<i>{title}</i>\n"
            "<a href='{url}'>#{num}</a> от "
            "<a href='https://github.com/{author}'><i>@{author}</i></a>"
        ),
        "notify_pr": (
            "<b>{e} На </b><a href='https://github.com/{repo}'><b>{repo}</b></a>"
            "<b> {action} pull request!</b>\n\n"
            "<i>{title}</i>\n"
            "<blockquote expandable>{body}</blockquote>\n\n"
            "Пользователь: <a href='https://github.com/{author}'><i>@{author}</i></a>\n\n"
            "<a href='{url}'>#{num}</a>"
        ),
        "notify_release": (
            "<b>{e} На </b><a href='https://github.com/{repo}'><b>{repo}</b></a>"
            "<b> {action} релиз!</b>\n\n"
            "🏷 <code>{tag}</code> · <b>{name}</b>\n"
            "👤 <a href='https://github.com/{author}'><i>@{author}</i></a>\n"
            "<a href='{url}'>Открыть релиз</a>"
        ),
        "notify_star_added": (
            "<b>⭐️ На </b><a href='https://github.com/{repo}'><b>{repo}</b></a>"
            "<b> добавлена звезда!</b>\n\n"
            "Всего звёзд: <i>{stars}</i>\n"
            "Пользователь: <a href='https://github.com/{user}'><i>@{user}</i></a>"
        ),
        "notify_star_removed": (
            "<b>💔 На </b><a href='https://github.com/{repo}'><b>{repo}</b></a>"
            "<b> убрана звезда!</b>\n\n"
            "Всего звёзд: <i>{stars}</i>\n"
            "Пользователь: <a href='https://github.com/{user}'><i>@{user}</i></a>"
        ),
        "_cfg_interval": "Интервал опроса по умолчанию (60–3600 сек). Переопределяется в настройках назначения.",
        "star_label": "⭐ Звёзды",
        "_cfg_token": (
            "Глобальный GitHub-токен для назначений без персонального токена.\n"

            "Без токена: 60 запросов/час. С токеном: 5000.\n"
            "Создать: github.com/settings/tokens"
        ),
        "push_label": "🔨 Push",
        "issues_label": "🐛 Issues",
        "pull_request_label": "🔀 Pull Requests",
        "release_label": "🚀 Релизы",
        "token_set": "✅ установлен",
        "token_not_set": "❌ не установлен",
        "btn_channel": "➕ Канал",
        "btn_group": "➕ Группа",
        "btn_close": "✖️ Закрыть",
        "btn_back": "◀️ Назад",
        "btn_skip": "⏩ Пропустить",
        "btn_add_repo": "➕ Добавить репозиторий",
        "btn_set_interval": "⏱ Установить интервал",
        "btn_set_token": "🔑 Установить токен",
        "btn_clear_token": "🔑 Очистить токен",
        "btn_remove": "🗑 Удалить",
        "btn_enter_dest": "✏️ Ввести {label} username / ID",
        "btn_add_repo_confirm": "✏️ Добавить репозиторий",
        "input_dest": "@username или ID {label}а",
        "input_repo": "owner/repo  (например: torvalds/linux)",
        "input_interval": "Интервал в секундах  (60 – 3600)",
        "input_token": "GitHub Personal Access Token",
        "repo_invalid_format": "❌ Неверный формат. Используйте <code>owner/repo</code>.",
        "checking_repo": "🔍 Проверяю репозиторий...",
        "issue_opened": "открыт",
        "issue_closed": "закрыт",
        "pr_merged": "смёрджен",
        "pr_closed": "закрыт",
        "pr_opened": "открыт",
        "release_prerelease": "пре-релиз",
        "release_published": "опубликован",
        "dest_label_channel": "Канал",
        "dest_label_group": "Группа",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "interval",
                300,
                lambda: self.strings["_cfg_interval"],
                validator=loader.validators.Integer(minimum=60, maximum=3600),
            ),
            loader.ConfigValue(
                "github_token",
                None,
                lambda: self.strings["_cfg_token"],
                validator=loader.validators.Hidden(
                    loader.validators.Union(
                        loader.validators.String(),
                        loader.validators.NoneType(),
                    )
                ),
            ),
        )
        self._sessions: dict[str, aiohttp.ClientSession] = {}

    async def client_ready(self):
        raw = self.db.get("GitHubMod", "dests")
        if raw is None:
            self.db.set("GitHubMod", "dests", {})
            return
        if not isinstance(raw, dict):
            self.db.set("GitHubMod", "dests", {})
            return
        migrated = {}
        changed = False
        for k, v in raw.items():
            if isinstance(v, dict):
                migrated[k] = v
            else:
                changed = True
                logger.info("GitHubMod: dropping malformed dest entry %s=%r", k, v)
        if changed:
            self.db.set("GitHubMod", "dests", migrated)

    async def on_unload(self):
        self.poller.stop()
        for s in self._sessions.values():
            with contextlib.suppress(Exception):
                await s.close()


    def _get_dests(self) -> dict:
        return self.db.get("GitHubMod", "dests", {})

    def _save_dests(self, dests: dict):
        self.db.set("GitHubMod", "dests", dests)


    def _get_session(self, chat_id_str: str) -> aiohttp.ClientSession:
        dest = self._get_dests().get(chat_id_str, {})
        token = dest.get("token") or self.config["github_token"]
        headers = dict(HEADERS_BASE)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        s = self._sessions.get(chat_id_str)
        if s and not s.closed:
            s.headers.update(headers)
            return s
        s = aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=20))
        self._sessions[chat_id_str] = s
        return s

    def _reset_session(self, chat_id_str: str):
        s = self._sessions.pop(chat_id_str, None)
        if s and not s.closed:
            import asyncio
            asyncio.ensure_future(s.close())


    @staticmethod
    def _to_bot_api_id(entity) -> int:
        """Convert Telethon entity ID to Bot API format (-100XXXXXXXXX for channels/supergroups)."""
        eid = entity.id
        if isinstance(entity, (Channel, Chat)):
            return int(f"-100{eid}")
        return eid

    async def _resolve_peer(self, peer_str: str):
        peer_str = peer_str.strip()
        try:
            ident = int(peer_str) if peer_str.lstrip("-").isdigit() else peer_str
            return await self._client.get_entity(ident)
        except Exception:
            return None

    async def _invite_bot(self, peer) -> tuple[bool, str]:
        bot = self.inline.bot_username
        try:
            await self._client(InviteToChannelRequest(peer, [bot]))
        except Exception as e:
            err = str(e).lower()
            if "already" in err or "participant" in err:
                pass
            else:
                return False, str(e)

        with contextlib.suppress(Exception):
            await self._client(
                EditAdminRequest(
                    channel=peer,
                    user_id=bot,
                    admin_rights=ChatAdminRights(
                        post_messages=True,
                        edit_messages=True,
                        delete_messages=True,
                    ),
                    rank="GitHub",
                )
            )
        return True, ""


    async def _api_get(self, path: str, chat_id_str: str, extra_headers: dict | None = None) -> tuple[list | dict | None, bool]:
        url = f"{GITHUB_API}{path}"
        session = self._get_session(chat_id_str)
        try:
            async with session.get(url, headers=extra_headers) as resp:
                if resp.status in (403, 429):
                    reset = int(resp.headers.get("X-RateLimit-Reset", 0))
                    dt = datetime.fromtimestamp(reset).strftime("%H:%M:%S") if reset else "?"
                    logger.warning("GitHubMod: rate limited (%s), resets %s", chat_id_str, dt)
                    return None, True
                if resp.status == 404:
                    return None, False
                if resp.status != 200:
                    logger.warning("GitHubMod: %s → %s", path, resp.status)
                    return None, False
                return await resp.json(), False
        except Exception:
            logger.exception("GitHubMod: request failed %s", path)
            return None, False

    async def _check_repo(self, repo: str, chat_id_str: str) -> tuple[bool, bool]:
        data, rl = await self._api_get(f"/repos/{repo}", chat_id_str)
        return data is not None, rl

    async def _fetch_commits(self, repo: str, since: str, cid: str) -> list:
        # List commits since last check (returns sha, html_url, commit.message, author — but NO stats/files)
        data, _ = await self._api_get(f"/repos/{repo}/commits?since={since}&per_page=5", cid)
        if not isinstance(data, list) or not data:
            return []
        # Enrich each commit with stats+files by fetching individually
        enriched = []
        for c in data:
            sha = c.get("sha", "")
            if not sha:
                enriched.append(c)
                continue
            detail, _ = await self._api_get(f"/repos/{repo}/commits/{sha}", cid)
            enriched.append(detail if isinstance(detail, dict) else c)
        return enriched

    async def _fetch_branch_for_commit(self, repo: str, sha: str, cid: str) -> str:
        """Find the branch name that contains this commit SHA."""
        data, _ = await self._api_get(f"/repos/{repo}/branches", cid)
        if not isinstance(data, list):
            return "main"
        # Check each branch's latest commit — fast path for small repos
        for b in data:
            if (b.get("commit") or {}).get("sha", "") == sha:
                return b.get("name", "main")
        return (data[0].get("name", "main")) if data else "main"

    async def _fetch_issues(self, repo: str, since: str, cid: str) -> list:
        data, _ = await self._api_get(
            f"/repos/{repo}/issues?state=all&since={since}&per_page=10&sort=updated", cid
        )
        return [i for i in (data or []) if isinstance(data, list) and "pull_request" not in i]

    async def _fetch_prs(self, repo: str, since: str, cid: str) -> list:
        data, _ = await self._api_get(
            f"/repos/{repo}/pulls?state=all&per_page=10&sort=updated&direction=desc", cid
        )
        if not isinstance(data, list):
            return []
        since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        return [
            pr for pr in data
            if datetime.fromisoformat(
                (pr.get("updated_at") or "1970-01-01T00:00:00Z").replace("Z", "+00:00")
            ) > since_dt
        ]

    async def _fetch_releases(self, repo: str, since: str, cid: str) -> list:
        data, _ = await self._api_get(f"/repos/{repo}/releases?per_page=5", cid)
        if not isinstance(data, list):
            return []
        since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        return [
            r for r in data
            if datetime.fromisoformat(
                (r.get("published_at") or "1970-01-01T00:00:00Z").replace("Z", "+00:00")
            ) > since_dt
        ]

    async def _fetch_stargazers(self, repo: str, since: str, cid: str) -> list:
        data, _ = await self._api_get(
            f"/repos/{repo}/stargazers?per_page=20", cid,
            extra_headers={"Accept": "application/vnd.github.star+json"},
        )
        if not isinstance(data, list):
            return []
        since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        result = []
        for item in data:
            starred_at = item.get("starred_at") or "1970-01-01T00:00:00Z"
            if datetime.fromisoformat(starred_at.replace("Z", "+00:00")) > since_dt:
                result.append({
                    "action": "created",
                    "sender": item.get("user", {}),
                    "repository": {"stargazers_count": "?"},
                })
        return result


    def _fmt_push(self, repo: str, commits: list, branch: str = "main", compare_url: str = "") -> list[str]:
        if not commits:
            return [self.strings("notify_push_empty").format(repo=repo, branch=branch)]

        commit_blocks = []
        for c in commits:
            commit = c.get("commit", {})
            login = (c.get("author") or {}).get("login", "")
            name = commit.get("author", {}).get("name", login or "unknown")
            sha = c.get("sha", "")[:7]
            msg = commit.get("message", "").split("\n")[0][:120]

            files_section = ""
            diff_section = ""
            stats = c.get("stats", {})
            files = c.get("files", [])
            if files:
                created = [f["filename"] for f in files if f.get("status") == "added"]
                removed_f = [f["filename"] for f in files if f.get("status") == "removed"]
                modified = [f["filename"] for f in files if f.get("status") == "modified"]
                if created:
                    files_section += self.strings("notify_push_created").format(files="\n".join(created))
                if removed_f:
                    files_section += self.strings("notify_push_removed").format(files="\n".join(removed_f))
                if modified:
                    files_section += self.strings("notify_push_modified").format(files="\n".join(modified))
            if stats.get("additions") or stats.get("deletions"):
                diff_section = self.strings("notify_push_diff").format(
                    added=stats.get("additions", 0),
                    removed=stats.get("deletions", 0),
                )
            commit_blocks.append(self.strings("notify_push_commit").format(
                url=c.get("html_url", "#"),
                sha=sha, name=name, login=login or name,
                msg=msg, files_section=files_section, diff_section=diff_section,
            ))

        pusher = (commits[-1].get("author") or {}).get("login", "") if commits else ""
        # Build compare URL: oldest_sha...newest_sha (GitHub shows diff between them)
        if not compare_url and len(commits) >= 2:
            old_sha = commits[0].get("parents", [{}])[0].get("sha", commits[0].get("sha", ""))[:12]
            new_sha = commits[-1].get("sha", "")[:12]
            compare_url = f"https://github.com/{repo}/compare/{old_sha}...{new_sha}"
        elif not compare_url:
            compare_url = commits[-1].get("html_url", f"https://github.com/{repo}")

        msg = self.strings("notify_push_header").format(
            repo=repo, branch=branch,
            count=len(commits), compare=compare_url,
        )
        msg += "".join(commit_blocks)
        msg += self.strings("notify_push_footer").format(login=pusher)
        return [msg]

    def _fmt_issues(self, repo: str, issues: list) -> list[str]:
        return [
            self.strings("notify_issue").format(
                e=E["issue_open" if i.get("state") == "open" else "issue_close"],
                action=self.strings("issue_opened") if i.get("state") == "open" else self.strings("issue_closed"),
                repo=repo,
                url=i.get("html_url", "#"),
                num=i.get("number", "?"),
                title=i.get("title", "")[:100],
                author=(i.get("user") or {}).get("login", "unknown"),
            )
            for i in reversed(issues)
        ]

    def _fmt_prs(self, repo: str, prs: list) -> list[str]:
        msgs = []
        for pr in reversed(prs):
            merged = pr.get("merged_at") is not None
            state = pr.get("state", "open")
            if merged:
                e_key, action = "pr_merge", self.strings("pr_merged")
            elif state == "closed":
                e_key, action = "pr_close", self.strings("pr_closed")
            else:
                e_key, action = "pr_open", self.strings("pr_opened")
            raw_body = pr.get("body") or ""
            body = (raw_body[:200] + "...") if len(raw_body) > 200 else raw_body
            msgs.append(self.strings("notify_pr").format(
                e=E[e_key], action=action, repo=repo,
                url=pr.get("html_url", "#"),
                num=pr.get("number", "?"),
                title=pr.get("title", "")[:100],
                body=body,
                author=(pr.get("user") or {}).get("login", "unknown"),
            ))
        return msgs

    def _fmt_releases(self, repo: str, releases: list) -> list[str]:
        return [
            self.strings("notify_release").format(
                e=E["prerelease" if r.get("prerelease") else "release"],
                action=self.strings("release_prerelease") if r.get("prerelease") else self.strings("release_published"),
                repo=repo,
                tag=r.get("tag_name", ""),
                name=r.get("name") or r.get("tag_name", ""),
                author=(r.get("author") or {}).get("login", "unknown"),
                url=r.get("html_url", "#"),
            )
            for r in reversed(releases)
        ]


    def _fmt_star(self, repo: str, stars_data: list) -> list[str]:
        msgs = []
        for s in stars_data:
            action = s.get("action", "created")
            user = (s.get("sender") or {}).get("login", "unknown")
            stars = (s.get("repository") or {}).get("stargazers_count", "?")
            key = "notify_star_added" if action == "created" else "notify_star_removed"
            msgs.append(self.strings(key).format(repo=repo, stars=stars, user=user))
        return msgs

    @loader.loop(autostart=True, wait_before=True)
    async def poller(self):
        dests = self._get_dests()
        self.poller.interval = self.config["interval"]
        if not dests:
            return

        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        for cid_str, dest in list(dests.items()):
            interval = dest.get("interval", self.config["interval"])
            self.poller.interval = min(self.poller.interval, interval)
            try:
                await self._poll_dest(cid_str, dest, now_iso)
            except Exception:
                logger.exception("GitHubMod: error polling %s", cid_str)
            for repo in dest.get("repos", {}):
                dests[cid_str]["repos"][repo]["last_checked"] = now_iso

        self._save_dests(dests)

    async def _poll_dest(self, cid_str: str, dest: dict, now_iso: str):
        events = dest.get("events", list(EVENT_LABELS.keys()))
        chat_id = int(cid_str)
        messages: list[str] = []

        for repo, repo_data in dest.get("repos", {}).items():
            since = repo_data.get("last_checked")
            if not since:
                continue
            if "push" in events:
                c = await self._fetch_commits(repo, since, cid_str)
                if c:
                    newest_sha = c[-1].get("sha", "")
                    branch = await self._fetch_branch_for_commit(repo, newest_sha, cid_str)
                    messages += self._fmt_push(repo, c, branch=branch)
            if "issues" in events:
                i = await self._fetch_issues(repo, since, cid_str)
                if i:
                    messages += self._fmt_issues(repo, i)
            if "pull_request" in events:
                p = await self._fetch_prs(repo, since, cid_str)
                if p:
                    messages += self._fmt_prs(repo, p)
            if "release" in events:
                r = await self._fetch_releases(repo, since, cid_str)
                if r:
                    messages += self._fmt_releases(repo, r)
            if "star" in events:
                s = await self._fetch_stargazers(repo, since, cid_str)
                if s:
                    messages += self._fmt_star(repo, s)

        for text in messages:
            try:
                await self.inline.bot.send_message(
                    chat_id,
                    text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
            except Exception:
                logger.exception("GitHubMod: failed to send to %s", chat_id)


    def _panel_text(self, dest: dict) -> str:
        repos = dest.get("repos", {})
        events = dest.get("events", list(EVENT_LABELS.keys()))
        token = dest.get("token")
        return self.strings("panel_title").format(
            icon="📢" if dest.get("type") == "channel" else "👥",
            title=dest.get("title", "?"),
            repos=", ".join(f"<code>{r}</code>" for r in repos)
            or self.strings("panel_repos_empty"),
            events=" · ".join(self.strings(e + "_label") for e in events),
            interval=dest.get("interval", self.config["interval"]),
            token=self.strings("token_set") if token else self.strings("token_not_set"),
        )

    def _panel_markup(self, cid_str: str, dest: dict) -> list:
        events = dest.get("events", list(EVENT_LABELS.keys()))
        repos = dest.get("repos", {})
        markup = []

        for e_key in EVENT_LABELS:
            markup.append([{
                "text": ("✅ " if e_key in events else "☑️ ") + self.strings(e_key + "_label"),
                "callback": self._cb_toggle_event,
                "args": (cid_str, e_key),
            }])

        markup.append([{
            "text": self.strings("btn_add_repo"),
            "input": self.strings("input_repo"),
            "handler": self._cb_add_repo,
            "kwargs": {"cid_str": cid_str},
        }])

        for repo in repos:
            markup.append([{
                "text": self.strings("btn_remove") + f" {repo}",
                "callback": self._cb_remove_repo,
                "args": (cid_str, repo),
            }])

        markup.append([{
            "text": self.strings("btn_set_interval"),
            "input": self.strings("input_interval"),
            "handler": self._cb_set_interval,
            "kwargs": {"cid_str": cid_str},
        }])
        markup.append([{
            "text": self.strings("btn_set_token"),
            "input": self.strings("input_token"),
            "handler": self._cb_set_token,
            "kwargs": {"cid_str": cid_str},
        }])
        markup.append([
            {"text": self.strings("btn_clear_token"), "callback": self._cb_clear_token, "args": (cid_str,)},
            {"text": self.strings("btn_remove"), "callback": self._cb_remove_dest, "args": (cid_str,)},
        ])
        markup.append([{"text": self.strings("btn_back"), "callback": self._cb_main_menu}])
        return markup

    async def _render_main_menu(self, call_or_msg):
        dests = self._get_dests()
        text = self.strings("setup_welcome")
        markup = []
        for cid_str, dest in dests.items():
            if not isinstance(dest, dict):
                continue
            icon = "📢" if dest.get("type") == "channel" else "👥"
            markup.append([{
                "text": icon + " " + dest.get("title", cid_str),
                "callback": self._cb_open_panel,
                "args": (cid_str,),
            }])
        markup.append([
            {"text": self.strings("btn_channel"), "callback": self._cb_add_dest, "args": ("channel",)},
            {"text": self.strings("btn_group"), "callback": self._cb_add_dest, "args": ("group",)},
        ])
        if dests:
            markup.append([{"text": self.strings("btn_close"), "action": "close"}])

        if isinstance(call_or_msg, Message):
            await self.inline.form(message=call_or_msg, text=text, reply_markup=markup)
        else:
            await call_or_msg.edit(text, reply_markup=markup)


    async def _cb_main_menu(self, call):
        await self._render_main_menu(call)

    async def _cb_open_panel(self, call, cid_str: str):
        dest = self._get_dests().get(cid_str, {})
        await call.edit(self._panel_text(dest), reply_markup=self._panel_markup(cid_str, dest))

    async def _cb_toggle_event(self, call, cid_str: str, event: str):
        dests = self._get_dests()
        events = dests[cid_str].get("events", list(EVENT_LABELS.keys()))
        if event in events:
            events.remove(event)
        else:
            events.append(event)
        dests[cid_str]["events"] = events
        self._save_dests(dests)
        dest = dests[cid_str]
        await call.edit(self._panel_text(dest), reply_markup=self._panel_markup(cid_str, dest))

    async def _cb_remove_repo(self, call, cid_str: str, repo: str):
        dests = self._get_dests()
        dests[cid_str].get("repos", {}).pop(repo, None)
        self._save_dests(dests)
        dest = dests[cid_str]
        await call.edit(self._panel_text(dest), reply_markup=self._panel_markup(cid_str, dest))

    async def _cb_clear_token(self, call, cid_str: str):
        dests = self._get_dests()
        dests[cid_str].pop("token", None)
        self._save_dests(dests)
        self._reset_session(cid_str)
        dest = dests[cid_str]
        await call.edit(self._panel_text(dest), reply_markup=self._panel_markup(cid_str, dest))

    async def _cb_remove_dest(self, call, cid_str: str):
        dests = self._get_dests()
        title = dests.get(cid_str, {}).get("title", cid_str)
        dests.pop(cid_str, None)
        self._save_dests(dests)
        self._reset_session(cid_str)
        await call.edit(self.strings("dest_removed").format(title=title))

    async def _cb_add_dest(self, call, dest_type: str):
        icon = "📢" if dest_type == "channel" else "👥"
        label = self.strings("dest_label_channel") if dest_type == "channel" else self.strings("dest_label_group")
        await call.edit(
            self.strings("enter_dest").format(icon=icon, label=label, label_lc=label.lower()),
            reply_markup=[
                [{
                    "text": self.strings("btn_enter_dest").format(label=label.lower()),
                    "input": self.strings("input_dest").format(label=label.lower()),
                    "handler": self._cb_got_dest,
                    "kwargs": {"dest_type": dest_type},
                }],
                [{"text": self.strings("btn_back"), "callback": self._cb_main_menu}],
            ],
        )

    async def _cb_got_dest(self, call, peer_str: str, dest_type: str):
        entity = await self._resolve_peer(peer_str)
        if not entity:
            await call.edit(
                self.strings("dest_not_found"),
                reply_markup=[[{"text": self.strings("btn_back"), "callback": self._cb_main_menu}]],
            )
            return

        ok, err = await self._invite_bot(entity)
        if not ok:
            await call.edit(
                self.strings("bot_invite_fail").format(bot=self.inline.bot_username),
                reply_markup=[[{"text": self.strings("btn_back"), "callback": self._cb_main_menu}]],
            )
            return

        bot_api_id = self._to_bot_api_id(entity)
        cid_str = str(bot_api_id)
        title = getattr(entity, "title", cid_str)
        label = self.strings("dest_label_channel") if dest_type == "channel" else self.strings("dest_label_group")

        dests = self._get_dests()
        if cid_str not in dests:
            dests[cid_str] = {
                "id": bot_api_id,
                "title": title,
                "type": dest_type,
                "repos": {},
                "events": list(EVENT_LABELS.keys()),
            }
            self._save_dests(dests)

        await call.edit(
            self.strings("dest_configured").format(label=label, title=title),
            reply_markup=[
                [{
                    "text": self.strings("btn_add_repo_confirm"),
                    "input": self.strings("input_repo"),
                    "handler": self._cb_add_repo,
                    "kwargs": {"cid_str": cid_str},
                }],
                [{"text": self.strings("btn_skip"), "callback": self._cb_open_panel, "args": (cid_str,)}],
            ],
        )

    async def _cb_add_repo(self, call, repo: str, cid_str: str):
        repo = repo.strip().strip("/")
        dests = self._get_dests()
        dest = dests.get(cid_str, {})
        title = dest.get("title", cid_str)

        if "/" not in repo or len(repo.split("/")) != 2:
            await call.edit(
                self.strings("repo_invalid_format"),
                reply_markup=[[{"text": self.strings("btn_back"), "callback": self._cb_open_panel, "args": (cid_str,)}]],
            )
            return
        if repo in dest.get("repos", {}):
            await call.edit(
                self.strings("repo_already").format(repo=repo, title=title),
                reply_markup=[[{"text": self.strings("btn_back"), "callback": self._cb_open_panel, "args": (cid_str,)}]],
            )
            return

        await call.edit(self.strings("checking_repo"))
        exists, rl = await self._check_repo(repo, cid_str)
        if rl:
            await call.edit(self.strings("rate_limit").format(reset="—"))
            return
        if not exists:
            await call.edit(
                self.strings("repo_not_found").format(repo=repo),
                reply_markup=[[{"text": self.strings("btn_back"), "callback": self._cb_open_panel, "args": (cid_str,)}]],
            )
            return

        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        dests[cid_str].setdefault("repos", {})[repo] = {"last_checked": now_iso}
        self._save_dests(dests)
        dest = dests[cid_str]
        await call.edit(self._panel_text(dest), reply_markup=self._panel_markup(cid_str, dest))

    async def _cb_set_interval(self, call, val: str, cid_str: str):
        try:
            secs = int(val.strip())
            assert 60 <= secs <= 3600
        except (ValueError, AssertionError):
            await call.answer(self.strings("interval_invalid"), show_alert=True)
            return
        dests = self._get_dests()
        dests[cid_str]["interval"] = secs
        self._save_dests(dests)
        dest = dests[cid_str]
        await call.edit(self._panel_text(dest), reply_markup=self._panel_markup(cid_str, dest))

    async def _cb_set_token(self, call, token: str, cid_str: str):
        token = token.strip()
        dests = self._get_dests()
        dests[cid_str]["token"] = token or None
        self._save_dests(dests)
        self._reset_session(cid_str)
        dest = dests[cid_str]
        await call.edit(self._panel_text(dest), reply_markup=self._panel_markup(cid_str, dest))


    @loader.command(ru_doc="- Открыть панель управления GitHub Monitor")
    async def githubcmd(self, message: Message):
        """- Open GitHub Monitor control panel"""
        await self._render_main_menu(message)

