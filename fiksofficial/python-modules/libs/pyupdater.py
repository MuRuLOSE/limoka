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

import asyncio
import hashlib
import hmac
import logging
import re
import time

from .. import loader

logger = logging.getLogger(__name__)

BLOB_RE = re.compile(r"https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)")
RAW_RE  = re.compile(r"https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.+)")

API_BASE     = "https://37a5bcc11453.vps.myjino.ru"
BOT_USERNAME = "pyupdater_bot"
GITHUB_TOKEN = ""

TOKEN_DB_KEY = "user_token"
TOKEN_PREFIX = "pyut_"


def _parse(url: str):
    for pat in (BLOB_RE, RAW_RE):
        m = pat.match(url.strip())
        if m:
            return m.groups()
    return None


def _gh_headers() -> dict:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def _sign(secret_key: str, api_key: str) -> str:
    bucket = (int(time.time()) // 60) * 60
    msg = f"{api_key}:{bucket}".encode()
    return hmac.new(secret_key.encode(), msg, hashlib.sha256).hexdigest()


class PyUpdaterLib(loader.Library):
    developer = "@pyupdater"
    version = (1, 0, 0)

    async def init(self):
        await self._refresh_token()

    async def _refresh_token(self):
        """Каждый раз при загрузке библиотеки запрашивает свежий токен у бота."""
        try:
            sent = await self.client.send_message(BOT_USERNAME, "/token")

            response = None
            for _ in range(20):
                await asyncio.sleep(0.5)
                msgs = await self.client.get_messages(BOT_USERNAME, limit=1)
                if (
                    msgs
                    and msgs[0].id != sent.id
                    and msgs[0].text
                    and msgs[0].text.startswith(TOKEN_PREFIX)
                ):
                    response = msgs[0]
                    break

            if response is None:
                logger.warning("PyUpdater: не получили токен от бота")
                return

            self._lib_set(TOKEN_DB_KEY, response.text.strip())
            logger.info("PyUpdater: токен обновлён")

            async def _cleanup():
                await asyncio.sleep(3)
                try:
                    await sent.delete()
                    await response.delete()
                except Exception:
                    pass

            asyncio.create_task(_cleanup())

        except Exception:
            logger.exception("PyUpdater: ошибка при получении токена")

    async def check(
        self,
        module: loader.Module,
        github_url: str,
        api_key: str,
        secret_key: str,
    ) -> None:
        parts = _parse(github_url)
        if parts is None:
            logger.warning("PyUpdater: cannot parse URL %r", github_url)
            return

        owner, repo, branch, path = parts
        module_name = module.strings["name"]

        asyncio.create_task(self._ping(api_key, secret_key, module.tg_id, module_name))
        asyncio.create_task(self._maybe_confirm_test(api_key, module.tg_id))

        commits_url = (
            f"https://api.github.com/repos/{owner}/{repo}/commits"
            f"?path={path}&sha={branch}&per_page=1"
        )
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
        db_key = f"pyu_sha_{owner}_{repo}_{path.replace('/', '_')}"
        saved_sha: str = module._db.get(module_name, db_key, "")

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    commits_url,
                    headers=_gh_headers(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status in (403, 429):
                        logger.warning("PyUpdater: GitHub rate limit for %s", module_name)
                        return
                    resp.raise_for_status()
                    commits = await resp.json()

                if not commits:
                    return

                latest_sha: str = commits[0]["sha"]
                if latest_sha == saved_sha:
                    return

                async with session.get(
                    raw_url,
                    headers=_gh_headers(),
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    resp.raise_for_status()
                    new_code = await resp.text()

        except asyncio.TimeoutError:
            logger.warning("PyUpdater: timeout for %s", module_name)
            return
        except Exception:
            logger.exception("PyUpdater: error checking %s", module_name)
            return

        module._db.set(module_name, db_key, latest_sha)
        logger.info("PyUpdater: reloading %s (commit %s)", module_name, latest_sha[:7])

        loader_mod = next(
            (m for m in module.allmodules.modules if m.__class__.__name__ == "LoaderMod"),
            None,
        )
        if loader_mod is None:
            logger.error("PyUpdater: LoaderMod not found")
            return

        asyncio.create_task(loader_mod.load_module(new_code, None, save_fs=True))

    async def _maybe_confirm_test(self, api_key: str, user_tg_id: int) -> None:
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{API_BASE}/test/pending",
                    params={"api_key": api_key},
                    timeout=aiohttp.ClientTimeout(total=8),
                ) as resp:
                    if resp.status != 200:
                        return
                    data = await resp.json()
                    if not data.get("pending"):
                        return

                await session.post(
                    f"{API_BASE}/test/confirm",
                    json={"api_key": api_key, "user_tg_id": user_tg_id},
                    timeout=aiohttp.ClientTimeout(total=8),
                )
        except Exception:
            pass

    async def _ping(self, api_key: str, secret_key: str, user_tg_id: int, module_name: str) -> None:
        user_token: str = self._lib_get(TOKEN_DB_KEY, "")
        payload = {
            "api_key":     api_key,
            "signature":   _sign(secret_key, api_key),
            "user_tg_id":  user_tg_id,
            "module_name": module_name,
        }
        if user_token:
            payload["user_token"] = user_token

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"{API_BASE}/ping",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=8),
                )
        except Exception:
            pass
