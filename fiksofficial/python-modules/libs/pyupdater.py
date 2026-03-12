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

import aiohttp

from .. import loader

logger = logging.getLogger(__name__)

BLOB_RE = re.compile(r"https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)")
RAW_RE  = re.compile(r"https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.+)")

API_BASE     = "37a5bcc11453.vps.myjino.ru"
BOT_USERNAME = "pyupdater_bot"
GITHUB_TOKEN = ""


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

    developer = "@pymodule"
    version = (1, 0, 0)

    async def init(self):
        pass

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

        asyncio.create_task(self._ensure_token(module))

        asyncio.create_task(self._ping(api_key, secret_key, module.tg_id, module_name, module))

        commits_url = (
            f"https://api.github.com/repos/{owner}/{repo}/commits"
            f"?path={path}&sha={branch}&per_page=1"
        )
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
        db_key = f"pyu_sha_{owner}_{repo}_{path.replace('/', '_')}"
        saved_sha: str = module._db.get(module_name, db_key, "")

        try:
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
        logger.info("PyUpdater: reloading %s (%s)", module_name, latest_sha[:7])

        loader_mod = self.lookup("loader")
        if not loader_mod:
            logger.error("PyUpdater: LoaderMod not found via lookup")
            return

        asyncio.create_task(loader_mod.load_module(new_code, None, save_fs=True))

    async def _ensure_token(self, module: loader.Module) -> None:
        existing = self._lib_get("user_token", "")
        if existing:
            return

        try:
            sent = await self.client.send_message(BOT_USERNAME, "/token")
            async with self.client.conversation(BOT_USERNAME, timeout=10) as conv:
                response = await conv.get_response()

            token = response.text.strip()
            if not token.startswith("pyut_"):
                logger.warning("PyUpdater: unexpected /token response: %r", token)
                return

            self._lib_set("user_token", token)
            logger.info("PyUpdater: user token saved automatically")

            await asyncio.sleep(3)
            await sent.delete()
            await response.delete()

        except asyncio.TimeoutError:
            logger.warning("PyUpdater: bot did not respond to /token in time")
        except Exception:
            logger.exception("PyUpdater: failed to auto-fetch token")

    async def _ping(
        self,
        api_key: str,
        secret_key: str,
        user_tg_id: int,
        module_name: str,
        module: loader.Module,
    ) -> None:
        user_token: str = self._lib_get("user_token", "")
        payload = {
            "api_key":     api_key,
            "signature":   _sign(secret_key, api_key),
            "user_tg_id":  user_tg_id,
            "module_name": module_name,
        }
        if user_token:
            payload["user_token"] = user_token

        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"{API_BASE}/ping",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=8),
                )
        except Exception:
            pass
