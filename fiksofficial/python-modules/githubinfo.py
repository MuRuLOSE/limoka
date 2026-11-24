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
# meta fhsdesc: tool, tools, github, info, inline

from .. import loader, utils
from ..inline import InlineCall
import logging
import asyncio
import urllib.request
import json
from datetime import datetime, timedelta

@loader.tds
class GitHubInfoMod(loader.Module):
    """GitHub user information"""
    strings = {
        "name": "GitHubInfo",

        "no_username": "❗ Provide a GitHub username.",
        "user_not_found": "🚫 User not found: <b>{}</b>",
        "api_error": "⚠ GitHub API error: <b>{msg}</b>",
        "no_activity": "🕸 No recent activity from <b>{}</b>",
        "no_contrib": "📭 No contribution data.",
        "no_repos": "📭 No public repositories.",
        "no_orgs": "📭 Not a member of any organizations.",
        "no_title": "No title",
        "no_desc": "No description",
        "not_specified": "Not specified",
        "more_commits": "  ... and {} more\n",
        "hireable_yes": "Yes",
        "hireable_no": "No",

        "menu_text": "Choose a section:",

        "btn_activity": "🔥 Activity",
        "btn_contrib": "📊 Contributions",
        "btn_repos": "📦 Repositories",
        "btn_orgs": "🏛 Organizations",
        "btn_back": "← Back to profile",

        "profile_header": "<b>Profile</b> <a href=\"{url}\">{username}</a>\n\n",
        "profile_text": (
            "👤 Name: <b>{name}</b>\n"
            "🏷 Login: <code>{login}</code>\n"
            "📝 Bio: {bio}\n"
            "🏢 Company: {company}\n"
            "📍 Location: {location}\n"
            "📧 Email: {email}\n"
            "🔗 Website: {blog}\n"
            "🐦 Twitter: {twitter}\n"
            "💼 Hireable: {hireable}\n"
            "📊 Type: {type}\n"
            "📦 Public repos: <b>{repos}</b>\n"
            "⭐ Public gists: <b>{gists}</b>\n"
            "👥 Followers: <b>{followers}</b>\n"
            "👣 Following: <b>{following}</b>\n"
            "🕐 Created: <code>{created}</code>\n"
            "🕐 Updated: <code>{updated}</code>"
        ),

        "activity_header": "<b>Recent activity</b> <a href=\"https://github.com/{username}\">{username}</a>\n\n",

        "push_header": "🔨 Pushed to <code>{branch}</code> → <a href=\"https://github.com/{repo}\">{repo}</a>\n",
        "push_no_commits": "🔨 Pushed (no details) to <code>{branch}</code> → <a href=\"https://github.com/{repo}\">{repo}</a>\n",
        "commit_line": "• <a href=\"{url}\"><code>{sha}</code></a>: {message}\n",

        "create_branch": "✨ Created branch <code>{ref}</code> in <a href=\"https://github.com/{repo}\">{repo}</a>\n",
        "create_tag": "✨ Created tag <code>{ref}</code> in <a href=\"https://github.com/{repo}/releases/tag/{ref}\">{repo}</a>\n",
        "create_repo": "✨ Created repository <a href=\"https://github.com/{repo}\">{repo}</a>\n",

        "pr_opened": "🔄 Opened PR <a href=\"{url}\">#{} {title}</a>\n",
        "pr_closed": "🔄 Closed PR <a href=\"{url}\">#{} {title}</a>\n",
        "pr_merged": "🔄 Merged PR <a href=\"{url}\">#{} {title}</a>\n",

        "issue_opened": "❗ Opened issue <a href=\"{url}\">#{} {title}</a>\n",
        "issue_closed": "❗ Closed issue <a href=\"{url}\">#{} {title}</a>\n",

        "star": "⭐ Starred <a href=\"https://github.com/{repo}\">{repo}</a>\n",
        "fork": "⑂ Forked <a href=\"https://github.com/{fork}\">{fork}</a>\n",

        "other": "⚡ {event} in <a href=\"https://github.com/{repo}\">{repo}</a>\n",

        "repos_header": "<b>Top repositories by stars</b> <a href=\"https://github.com/{username}\">{username}</a>\n\n",
        "repo_line": "⭐ <b>{stars}</b> | <a href=\"{url}\">{name}</a> — {desc}\nLanguage: {lang} | Forks: {forks}\n\n",

        "orgs_header": "<b>Organizations</b> <a href=\"https://github.com/{username}\">{username}</a>\n\n",
        "org_line": "• <a href=\"{url}\">{login}</a> — {desc}\n",

        "contrib_header": "<b>Contribution graph (last year)</b> <a href=\"https://github.com/{username}\">{username}</a>\n",
        "contrib_footer": "\n⬛ = 0, 🟩 = 1+ contributions",
    }

    strings_ru = {
        "_cls_doc": "Информация о GitHub-пользователе",

        "no_username": "❗ Укажи GitHub username.",
        "user_not_found": "🚫 Пользователь не найден: <b>{}</b>",
        "api_error": "⚠ Ошибка GitHub API: <b>{msg}</b>",
        "no_activity": "🕸 Нет недавней активности у <b>{}</b>",
        "no_contrib": "📭 Нет данных о контрибуциях.",
        "no_repos": "📭 Нет публичных репозиториев.",
        "no_orgs": "📭 Не состоит в организациях.",
        "no_title": "Без названия",
        "no_desc": "Без описания",
        "not_specified": "Не указано",
        "more_commits": "  ... и ещё {}\n",
        "hireable_yes": "Да",
        "hireable_no": "Нет",

        "menu_text": "Выбери раздел:",

        "btn_activity": "🔥 Активность",
        "btn_contrib": "📊 Контрибы",
        "btn_repos": "📦 Репозитории",
        "btn_orgs": "🏛 Организации",
        "btn_back": "← Назад к профилю",

        "profile_header": "<b>Профиль</b> <a href=\"{url}\">{username}</a>\n\n",
        "profile_text": (
            "👤 Имя: <b>{name}</b>\n"
            "🏷 Логин: <code>{login}</code>\n"
            "📝 Био: {bio}\n"
            "🏢 Компания: {company}\n"
            "📍 Локация: {location}\n"
            "📧 Email: {email}\n"
            "🔗 Сайт: {blog}\n"
            "🐦 Twitter: {twitter}\n"
            "💼 Доступен для найма: {hireable}\n"
            "📊 Тип аккаунта: {type}\n"
            "📦 Публичные репозитории: <b>{repos}</b>\n"
            "⭐ Публичные гисты: <b>{gists}</b>\n"
            "👥 Подписчики: <b>{followers}</b>\n"
            "👣 Подписки: <b>{following}</b>\n"
            "🕐 Создан: <code>{created}</code>\n"
            "🕐 Обновлён: <code>{updated}</code>"
        ),

        "activity_header": "<b>Последняя активность</b> <a href=\"https://github.com/{username}\">{username}</a>\n\n",

        "push_header": "🔨 Запушил в <code>{branch}</code> → <a href=\"https://github.com/{repo}\">{repo}</a>\n",
        "push_no_commits": "🔨 Запушил (без деталей) в <code>{branch}</code> → <a href=\"https://github.com/{repo}\">{repo}</a>\n",
        "commit_line": "• <a href=\"{url}\"><code>{sha}</code></a>: {message}\n",

        "create_branch": "✨ Создал ветку <code>{ref}</code> в <a href=\"https://github.com/{repo}\">{repo}</a>\n",
        "create_tag": "✨ Создал тег <code>{ref}</code> в <a href=\"https://github.com/{repo}/releases/tag/{ref}\">{repo}</a>\n",
        "create_repo": "✨ Создал репозиторий <a href=\"https://github.com/{repo}\">{repo}</a>\n",

        "pr_opened": "🔄 Открыл PR <a href=\"{url}\">#{} {title}</a>\n",
        "pr_closed": "🔄 Закрыл PR <a href=\"{url}\">#{} {title}</a>\n",
        "pr_merged": "🔄 Замержил PR <a href=\"{url}\">#{} {title}</a>\n",

        "issue_opened": "❗ Открыл issue <a href=\"{url}\">#{} {title}</a>\n",
        "issue_closed": "❗ Закрыл issue <a href=\"{url}\">#{} {title}</a>\n",

        "star": "⭐ Добавил в избранное <a href=\"https://github.com/{repo}\">{repo}</a>\n",
        "fork": "⑂ Форкнул <a href=\"https://github.com/{fork}\">{fork}</a>\n",

        "other": "⚡ {event} в <a href=\"https://github.com/{repo}\">{repo}</a>\n",

        "repos_header": "<b>Топ репозитории по звёздам</b> <a href=\"https://github.com/{username}\">{username}</a>\n\n",
        "repo_line": "⭐ <b>{stars}</b> | <a href=\"{url}\">{name}</a> — {desc}\nЯзык: {lang} | Форков: {forks}\n\n",

        "orgs_header": "<b>Организации</b> <a href=\"https://github.com/{username}\">{username}</a>\n\n",
        "org_line": "• <a href=\"{url}\">{login}</a> — {desc}\n",

        "contrib_header": "<b>График контрибуций (последний год)</b> <a href=\"https://github.com/{username}\">{username}</a>\n",
        "contrib_footer": "\n⬛ = 0, 🟩 = 1+ контрибуций",
    }

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def github_fetch(self, url, github_api=True):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "Accept": "application/vnd.github+json" if github_api else "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except Exception as e:
            self.logger.error(f"[GitHub] {e}")
            return {"message": str(e)}

    @loader.command(ru_doc="{username без @} — Информация о GitHub пользователе")
    async def github(self, message):
        """{username without @} — GitHub user information"""
        username = utils.get_args_raw(message)
        if not username:
            await utils.answer(message, self.strings("no_username"))
            return

        user_data = await self.github_fetch(f"https://api.github.com/users/{username}")
        if "message" in user_data:
            await utils.answer(message, self.strings("user_not_found").format(username))
            return

        hireable = self.strings("hireable_yes") if user_data.get("hireable") else self.strings("hireable_no")

        profile_text = (
            self.strings("profile_header").format(url=user_data["html_url"], username=username)
            + self.strings("profile_text").format(
                name=user_data.get("name") or self.strings("not_specified"),
                login=username,
                bio=user_data.get("bio") or self.strings("no_desc"),
                company=user_data.get("company") or self.strings("not_specified"),
                location=user_data.get("location") or self.strings("not_specified"),
                email=user_data.get("email") or self.strings("not_specified"),
                blog=user_data.get("blog") or self.strings("not_specified"),
                twitter=user_data.get("twitter_username") or self.strings("not_specified"),
                hireable=hireable,
                type=user_data.get("type", "User"),
                repos=user_data.get("public_repos", 0),
                gists=user_data.get("public_gists", 0),
                followers=user_data.get("followers", 0),
                following=user_data.get("following", 0),
                created=user_data.get("created_at", "")[:10],
                updated=user_data.get("updated_at", "")[:10],
            )
            + "\n" + self.strings("menu_text")
        )

        await self.inline.form(
            message=message,
            text=profile_text,
            reply_markup=[
                [{"text": self.strings("btn_activity"), "callback": self._activity, "args": (username,)}],
                [{"text": self.strings("btn_contrib"), "callback": self._contrib, "args": (username,)}, {"text": self.strings("btn_repos"), "callback": self._repos, "args": (username,)}],
                [{"text": self.strings("btn_orgs"), "callback": self._orgs, "args": (username,)}],
            ],
            ttl=10 * 60,
        )

    async def _profile(self, call: InlineCall, username: str):
        # Этот метод теперь используется только для возврата к профилю
        data = await self.github_fetch(f"https://api.github.com/users/{username}")
        if "message" in data:
            await call.edit(self.strings("api_error").format(msg=data["message"]))
            return

        hireable = self.strings("hireable_yes") if data.get("hireable") else self.strings("hireable_no")

        profile_text = (
            self.strings("profile_header").format(url=data["html_url"], username=username)
            + self.strings("profile_text").format(
                name=data.get("name") or self.strings("not_specified"),
                login=username,
                bio=data.get("bio") or self.strings("no_desc"),
                company=data.get("company") or self.strings("not_specified"),
                location=data.get("location") or self.strings("not_specified"),
                email=data.get("email") or self.strings("not_specified"),
                blog=data.get("blog") or self.strings("not_specified"),
                twitter=data.get("twitter_username") or self.strings("not_specified"),
                hireable=hireable,
                type=data.get("type", "User"),
                repos=data.get("public_repos", 0),
                gists=data.get("public_gists", 0),
                followers=data.get("followers", 0),
                following=data.get("following", 0),
                created=data.get("created_at", "")[:10],
                updated=data.get("updated_at", "")[:10],
            )
            + "\n" + self.strings("menu_text")
        )

        await call.edit(
            text=profile_text,
            reply_markup=[
                [{"text": self.strings("btn_activity"), "callback": self._activity, "args": (username,)}],
                [{"text": self.strings("btn_contrib"), "callback": self._contrib, "args": (username,)}, {"text": self.strings("btn_repos"), "callback": self._repos, "args": (username,)}],
                [{"text": self.strings("btn_orgs"), "callback": self._orgs, "args": (username,)}],
            ]
        )

    async def _activity(self, call: InlineCall, username: str):
        events = await self.github_fetch(f"https://api.github.com/users/{username}/events?per_page=40")
        if "message" in events:
            await call.edit(self.strings("api_error").format(msg=events["message"]), reply_markup=[[{"text": self.strings("btn_back"), "callback": self._profile, "args": (username,)}]])
            return
        if not events:
            await call.edit(self.strings("no_activity").format(username=username), reply_markup=[[{"text": self.strings("btn_back"), "callback": self._profile, "args": (username,)}]])
            return

        lines = [self.strings("activity_header").format(username=username)]
        seen_repos = set()

        for event in events[:25]:
            etype = event["type"]
            repo = event["repo"]["name"]
            if repo in seen_repos and len(lines) > 20:
                continue

            payload = event.get("payload", {})

            if etype == "PushEvent":
                branch = payload.get("ref", "refs/heads/main").replace("refs/heads/", "")
                commits = payload.get("commits", [])

                if commits:
                    lines.append(self.strings("push_header").format(branch=branch, repo=repo))
                    for commit in commits[:5]:
                        sha = commit["sha"][:7]
                        message = commit["message"].split("\n")[0][:100]
                        if len(commit["message"].split("\n")[0]) > 100:
                            message += "..."
                        url = f"https://github.com/{repo}/commit/{commit['sha']}"
                        lines.append(self.strings("commit_line").format(url=url, sha=sha, message=message))
                    if len(commits) > 5:
                        lines.append(self.strings("more_commits").format(len(commits)-5))
                else:
                    lines.append(self.strings("push_no_commits").format(branch=branch, repo=repo))

                seen_repos.add(repo)

            elif etype == "CreateEvent":
                ref_type = payload.get("ref_type")
                ref = payload.get("ref") or ""
                if ref_type == "branch":
                    lines.append(self.strings("create_branch").format(ref=ref, repo=repo))
                elif ref_type == "tag":
                    lines.append(self.strings("create_tag").format(ref=ref, repo=repo))
                elif ref_type == "repository":
                    lines.append(self.strings("create_repo").format(repo=repo))

            elif etype == "PullRequestEvent":
                pr = payload.get("pull_request", {})
                number = pr.get("number", "?")
                title = pr.get("title") or self.strings("no_title")
                url = pr.get("html_url") or f"https://github.com/{repo}"
                action = payload.get("action")
                if action == "closed" and pr.get("merged"):
                    lines.append(self.strings("pr_merged").format(url=url, number=number, title=title))
                elif action == "opened":
                    lines.append(self.strings("pr_opened").format(url=url, number=number, title=title))
                elif action == "closed":
                    lines.append(self.strings("pr_closed").format(url=url, number=number, title=title))

            elif etype == "IssuesEvent":
                issue = payload.get("issue", {})
                number = issue.get("number", "?")
                title = issue.get("title") or self.strings("no_title")
                url = issue.get("html_url") or f"https://github.com/{repo}"
                action = payload.get("action")
                if action == "opened":
                    lines.append(self.strings("issue_opened").format(url=url, number=number, title=title))
                elif action == "closed":
                    lines.append(self.strings("issue_closed").format(url=url, number=number, title=title))

            elif etype == "WatchEvent":
                lines.append(self.strings("star").format(repo=repo))

            elif etype == "ForkEvent":
                fork = payload.get("forkee", {}).get("full_name", "unknown")
                lines.append(self.strings("fork").format(fork=fork))

            else:
                event_name = etype.replace("Event", "")
                lines.append(self.strings("other").format(event=event_name, repo=repo))

        await call.edit(
            text="".join(lines),
            reply_markup=[[{"text": self.strings("btn_back"), "callback": self._profile, "args": (username,)}]]
        )

    async def _repos(self, call: InlineCall, username: str):
        repos = await self.github_fetch(f"https://api.github.com/users/{username}/repos?sort=stars&per_page=10")
        if "message" in repos:
            await call.edit(self.strings("api_error").format(msg=repos["message"]), reply_markup=[[{"text": self.strings("btn_back"), "callback": self._profile, "args": (username,)}]])
            return
        if not repos:
            await call.edit(self.strings("no_repos"), reply_markup=[[{"text": self.strings("btn_back"), "callback": self._profile, "args": (username,)}]])
            return

        lines = [self.strings("repos_header").format(username=username)]
        for repo in repos[:10]:
            lines.append(self.strings("repo_line").format(
                stars=repo.get("stargazers_count", 0),
                url=repo["html_url"],
                name=repo["name"],
                desc=repo.get("description") or self.strings("no_desc"),
                lang=repo.get("language") or self.strings("not_specified"),
                forks=repo.get("forks_count", 0),
            ))

        await call.edit(
            text="".join(lines),
            reply_markup=[[{"text": self.strings("btn_back"), "callback": self._profile, "args": (username,)}]]
        )

    async def _orgs(self, call: InlineCall, username: str):
        orgs = await self.github_fetch(f"https://api.github.com/users/{username}/orgs")
        if "message" in orgs:
            await call.edit(self.strings("api_error").format(msg=orgs["message"]), reply_markup=[[{"text": self.strings("btn_back"), "callback": self._profile, "args": (username,)}]])
            return
        if not orgs:
            await call.edit(self.strings("no_orgs"), reply_markup=[[{"text": self.strings("btn_back"), "callback": self._profile, "args": (username,)}]])
            return

        lines = [self.strings("orgs_header").format(username=username)]
        for org in orgs:
            lines.append(self.strings("org_line").format(
                url=f"https://github.com/{org['login']}",
                login=org["login"],
                desc=org.get("description") or self.strings("no_desc"),
            ))

        await call.edit(
            text="".join(lines),
            reply_markup=[[{"text": self.strings("btn_back"), "callback": self._profile, "args": (username,)}]]
        )

    async def _contrib(self, call: InlineCall, username: str):
        data = await self.github_fetch(f"https://github-contributions-api.deno.dev/{username}.json", github_api=False)
        if not data or not data.get("contributions"):
            await call.edit(self.strings("no_contrib"), reply_markup=[[{"text": self.strings("btn_back"), "callback": self._profile, "args": (username,)}]])
            return

        raw_days = []
        for week in data.get("contributions", []):
            if isinstance(week, list):
                raw_days.extend([day for day in week if isinstance(day, dict)])

        today = datetime.utcnow().date()
        weeks_count = 53
        days_back = weeks_count * 7 + 7
        start = today - timedelta(days=days_back)

        matrix = [["⬛" for _ in range(weeks_count)] for _ in range(7)]

        for entry in raw_days:
            date_str = entry.get("date")
            if not date_str:
                continue
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if date < start or date > today:
                    continue
                count = entry.get("contributionCount") or entry.get("count", 0) or 0
                if count > 0:
                    day_idx = (date.weekday() + 1) % 7
                    week_idx = (date - start).days // 7
                    if week_idx < weeks_count:
                        matrix[day_idx][week_idx] = "🟩"
            except Exception:
                continue

        days_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        graph = "\n".join(f"{days_labels[i]} {''.join(matrix[i])}" for i in range(7))

        await call.edit(
            text=self.strings("contrib_header").format(username=username)
            + f"<pre>{graph}</pre>"
            + self.strings("contrib_footer"),
            reply_markup=[[{"text": self.strings("btn_back"), "callback": self._profile, "args": (username,)}]]
        )