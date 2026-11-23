import argparse
import ast
import asyncio
import logging
import os
import subprocess
import tempfile
from html import escape
from pathlib import Path

import aiohttp

import parse

parser = argparse.ArgumentParser(description="Update Diffs Script")
parser.add_argument("--token", required=True, help="Telegram bot token")
parser.add_argument("--api_url", default="https://api.telegram.org", help="Telegram API URL")
parser.add_argument("--chat_id", required=True, help="Chat ID to send updates to")
parser.add_argument("--base_commit", default="HEAD~1", help="Base commit to compare against")
parser.add_argument("--request_timeout", type=float, default=60, help="HTTP timeout in seconds")
parser.add_argument("--max_retries", type=int, default=8, help="Retries for 429 and temporary errors")
parser.add_argument("--queue_size", type=int, default=100, help="Maximum pending queue jobs")
args = parser.parse_args()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("diff-notifier")


class TelegramQueue:
    """Single-worker queue; retries Telegram 429 using parameters.retry_after."""
    def __init__(self, session):
        self.session = session
        self.queue = asyncio.Queue(maxsize=args.queue_size)
        self.worker = None

    async def start(self):
        self.worker = asyncio.create_task(self._run())

    async def send_message(self, text):
        await self.queue.put(("sendMessage", {"chat_id": args.chat_id, "text": text, "parse_mode": "HTML"}, None))

    async def send_document(self, path, caption=None):
        data = {"chat_id": args.chat_id, "parse_mode": "HTML"}
        if caption:
            data["caption"] = caption
        await self.queue.put(("sendDocument", data, path))

    async def _request(self, method, data, path):
        url = f"{args.api_url.rstrip('/')}/bot{args.token}/{method}"
        timeout = aiohttp.ClientTimeout(total=args.request_timeout)
        if path:
            # Reopen on each attempt because the HTTP client consumes the stream.
            with open(path, "rb") as file_obj:
                form = aiohttp.FormData()
                for key, value in data.items():
                    form.add_field(key, str(value))
                form.add_field("document", file_obj, filename=os.path.basename(path), content_type="application/octet-stream")
                async with self.session.post(url, data=form, timeout=timeout) as response:
                    return response.status, await response.json(content_type=None)
        async with self.session.post(url, data=data, timeout=timeout) as response:
            return response.status, await response.json(content_type=None)

    async def _send_with_retries(self, method, data, path):
        for attempt in range(args.max_retries + 1):
            try:
                status, result = await self._request(method, data, path)
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as exc:
                if attempt == args.max_retries:
                    log.error("%s failed after retries: %s", method, exc)
                    return
                delay = min(2 ** attempt, 60)
                log.warning("Temporary network error: %s; retry in %ss", exc, delay)
                await asyncio.sleep(delay)
                continue

            if not isinstance(result, dict):
                result = {"description": str(result)}
            error_code = result.get("error_code", status)

            if status == 429 or error_code == 429:
                retry_after = result.get("parameters", {}).get("retry_after", 1)
                try:
                    retry_after = max(1, float(retry_after))
                except (TypeError, ValueError):
                    retry_after = 1
                if attempt == args.max_retries:
                    log.error("%s: 429; retry limit reached", method)
                    return
                log.warning("Telegram 429: waiting %s seconds (retry %s/%s)", retry_after, attempt + 1, args.max_retries)
                await asyncio.sleep(retry_after)
                continue

            if status >= 500:
                if attempt == args.max_retries:
                    log.error("Telegram server error HTTP %s: %s", status, result)
                    return
                delay = min(2 ** attempt, 60)
                log.warning("Telegram HTTP %s; retry in %ss", status, delay)
                await asyncio.sleep(delay)
                continue

            if status >= 400 or not result.get("ok"):
                log.error("Telegram rejected %s (HTTP %s): %s", method, status, result)
                return
            log.info("Telegram %s sent", method)
            return

    async def _run(self):
        while True:
            job = await self.queue.get()
            try:
                if job is None:
                    return
                await self._send_with_retries(*job)
            except Exception:
                log.exception("Unexpected error while sending Telegram job")
            finally:
                self.queue.task_done()

    async def finish(self):
        await self.queue.join()
        await self.queue.put(None)
        await self.worker


def get_diff_files(base_commit, diff_filter):
    try:
        output = subprocess.check_output(
            ["git", "diff", f"--diff-filter={diff_filter}", "--name-only", base_commit, "HEAD"],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", errors="replace")
        return [item for item in output.splitlines() if item]
    except subprocess.CalledProcessError:
        log.exception("Unable to get changed files")
        return []


def get_file_diff(path, base_commit):
    try:
        return subprocess.check_output(
            ["git", "diff", base_commit, "HEAD", "--", path], stderr=subprocess.DEVNULL
        ).decode("utf-8", errors="replace")
    except subprocess.CalledProcessError:
        log.exception("Unable to get diff for %s", path)
        return ""


def get_commit(revision, path, fallback):
    try:
        value = subprocess.check_output(
            ["git", "rev-list", "-n", "1", revision, "--", path], stderr=subprocess.DEVNULL
        ).decode().strip()
        return value or fallback
    except subprocess.CalledProcessError:
        return fallback


def get_developer(path):
    try:
        info = parse.get_module_info(path)
        developer = (info or {}).get("meta", {}).get("developer")
        return developer.strip() if developer else None
    except Exception:
        log.exception("Unable to read module metadata for %s", path)
        return None


def parse_version(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets):
                try:
                    return ast.literal_eval(node.value)
                except (ValueError, SyntaxError):
                    return None
    return None


def is_module_file(path):
    return Path(path).suffix == ".py" and len(Path(path).parts) >= 2


def make_caption(path, base_commit, is_new=False):
    name = Path(path).stem
    developer = get_developer(path)
    new_hash = get_commit("HEAD", path, "HEAD")
    old_hash = get_commit(base_commit, path, base_commit)
    raw_url = f"https://raw.githubusercontent.com/MuRuLOSE/limoka/refs/heads/main/{path}"
    diff_url = f"https://github.com/MuRuLOSE/limoka/compare/{old_hash}...{new_hash}.diff"

    if is_new:
        title = f"🪼 <b>New module <code>{name}</code> approved</b>"
    else:
        try:
            version = parse_version(Path(path).read_text(encoding="utf-8"))
            version = ".".join(map(str, version)) if version else ""
        except OSError:
            version = ""
            log.exception("Unable to read version from %s", path)
        title = f"🪼 <b>Module <code>{name}</code> <code>{version}</code> changes approved</b>"
    if developer:
        title += f"\nby <code>{developer}</code>"
    return title + f'\n\n<b><a href="{raw_url}">File URL</a></b> | <b><a href="{diff_url}">Diff URL</a></b>'


def create_temp_diff(name, diff):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".diff", prefix=f"{name}_", delete=False, encoding="utf-8") as tmp:
        tmp.write(diff)
        return tmp.name


async def main():
    base = args.base_commit
    added = [p for p in get_diff_files(base, "A") if is_module_file(p)]
    modified = [p for p in get_diff_files(base, "M") if is_module_file(p)]
    deleted = [p for p in get_diff_files(base, "D") if is_module_file(p)]
    if not (added or modified or deleted):
        log.info("No module changes detected")
        return

    temp_files = []
    timeout = aiohttp.ClientTimeout(total=args.request_timeout)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        sender = TelegramQueue(session)
        await sender.start()
        try:
            for path in deleted:
                await sender.send_message(f"🪼 <b>Module <code>{escape(Path(path).stem, quote=False)}</code> has been deleted</b>")

            for path, is_new in [(p, True) for p in added] + [(p, False) for p in modified]:
                diff = get_file_diff(path, base)
                if not diff:
                    log.info("Skipping %s: empty diff", path)
                    continue
                temp_path = create_temp_diff(Path(path).stem, diff)
                temp_files.append(temp_path)
                await sender.send_document(temp_path, make_caption(path, base, is_new))

            # Wait until all queued jobs (including retries) have completed.
            await sender.finish()
        finally:
            for path in temp_files:
                try:
                    os.remove(path)
                except OSError:
                    log.warning("Unable to remove temporary file %s", path)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Interrupted")
