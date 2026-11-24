#M i d g a 3 

#meta developer: @midga3_modules
# scope: heroku_min 2.0.0

import aiohttp
import logging
from .. import loader, utils
from herokutl.tl.types import Message
__verison__ = (1, 1, 0)
logger = logging.getLogger(__name__)
@loader.tds
class jsonchecker(loader.Module):
    strings = {
        "name": "JSON Checker",
        "searching": "<tg-emoji emoji-id=5188217332748527444>🔍</tg-emoji>Loading...",
        "json": "<tg-emoji emoji-id=5370869711888194012>👾</tg-emoji> URL: {}\n<tg-emoji emoji-id=5789531407231487577>🎮</tg-emoji> Keys: {}. \n <tg-emoji emoji-id=5409008750893734809>🏆</tg-emoji>Content: \n{}",
        "not_found": "<tg-emoji emoji-id=5210952531676504517>❌</tg-emoji>Check your config, make sure you set the right URL.",
        "new_notify": "JSON changed:\n{}",
        "url": "URL of JSON file",
    }
    async def client_ready(self):
        self.asset_channel = self._db.get("heroku.forums", "channel_id", 0)
        self._notif_topic = await utils.asset_forum_topic(
            self._client,
            self._db,
            self.asset_channel,
            "json checker",
            description="Here will be notifications about JSON changes.\nRequires URL in cfg",
            icon_emoji_id=5345892905103932200,
        )
    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "url",
                None,
                lambda: self.strings("url"),
            ),
        )

    async def _fetch(self):
        if not self.config["url"]:
            return None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.config["url"]) as resp:
                    return await resp.json(content_type=None)
        except Exception as e:
            logger.error(f"Error fetching JSON: {e}")
            return None

    def _diff(self, old, new, path=""):
        changes = []
        if type(old) != type(new):
            changes.append(f"{path or '/'}: {old!r} -> {new!r}")
            return changes
        if isinstance(old, dict):
            for k in set(old.keys()) | set(new.keys()):
                sub = f"{path}.{k}" if path else k
                if k not in old:
                    changes.append(f"{sub}: <missing> -> {new[k]!r}")
                elif k not in new:
                    changes.append(f"{sub}: {old[k]!r} -> <missing>")
                else:
                    changes.extend(self._diff(old[k], new[k], sub))
        elif isinstance(old, list):
            if len(old) != len(new):
                changes.append(f"{path or '/'}: len {len(old)} -> {len(new)}")
            for i, (a, b) in enumerate(zip(old, new)):
                changes.extend(self._diff(a, b, f"{path}[{i}]"))
        elif old != new:
            changes.append(f"{path or '/'}: {old!r} -> {new!r}")
        return changes

    @loader.loop(interval=60, autostart=True)
    async def poller(self):
        if not self.config["url"]:
            return
        data = await self._fetch()
        if data is None:
            return
        old_data = self._db.get("jsonchecker", "cached", default=None)
        if old_data is None:
            self._db.set("jsonchecker", "cached", data)
            return
        changes = self._diff(old_data, data)
        self._db.set("jsonchecker", "cached", data)
        if not changes:
            return
        text = "\n".join(changes[:50])
        keyboard = {
            "inline_keyboard": [
                [{"text": "🔗 Link", "url": self.config["url"]}]
            ]
        }
        await self.inline.bot.send_message(
            int(f"-100{self.asset_channel}"),
            self.strings["new_notify"].format(text),
            disable_webpage_preview=True,
            message_thread_id=self._notif_topic.id,
            reply_markup=keyboard
        )

    def _json_nav(self, pages, index):
        if len(pages) <= 1:
            return None
        buttons = []
        if index > 0:
            buttons.append({"text": "◀️", "callback": self._json_page, "args": (pages, index - 1)})
        buttons.append({"text": f"{index + 1}/{len(pages)}", "callback": self._json_page, "args": (pages, index)})
        if index < len(pages) - 1:
            buttons.append({"text": "▶️", "callback": self._json_page, "args": (pages, index + 1)})
        return [buttons]

    async def _json_page(self, call, pages, index):
        await call.edit(pages[index], reply_markup=self._json_nav(pages, index))


    @loader.command()
    async def jsonget(self, message: Message):
        await message.edit(self.strings["searching"])
        data = await self._fetch()
        if data is None:
            await message.edit(self.strings["not_found"])
            return
        lines = []
        if isinstance(data, dict):
            for k, v in list(data.items()):
                lines.append(f"{k}: {str(v)[:200]}")
        elif isinstance(data, list):
            for i, v in enumerate(data):
                lines.append(f"{i}: {str(v)[:200]}")
        else:
            lines.append(str(data)[:2000])
        keys_count = len(data) if hasattr(data, "__len__") else 0
        pages = []
        step = 5
        for page_start in range(0, max(len(lines), 1), step):
            chunk = lines[page_start:page_start + step]
            text = "<blockquote expandable>" + "\n".join(chunk) + "</blockquote>"
            pages.append(self.strings["json"].format(self.config["url"], keys_count, text))

        await self.inline.form(
            message=message,
            text=pages[0],
            reply_markup=self._json_nav(pages, 0)
            )
