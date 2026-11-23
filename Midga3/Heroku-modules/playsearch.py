#M i d g a 3 

#meta developer: @midga3_modules
# scope: heroku_min 2.0.0

from google_play_scraper import app as gp_app, search as gp_search
import logging
from .. import loader, utils
from herokutl.tl.types import Message
__verison__ = (1, 1, 0)
logger = logging.getLogger(__name__)
@loader.tds
class playsearch(loader.Module):
    """
    Search games!
    """
    strings = {
        "name": "PlaySearch",
        "searching": "<tg-emoji emoji-id=5188217332748527444>🔍</tg-emoji>Searching...",
        "game": "<tg-emoji emoji-id=5370869711888194012>👾</tg-emoji> App: {}\n<tg-emoji emoji-id=5789531407231487577>🎮</tg-emoji> Found: {}.\n<tg-emoji emoji-id=5409008750893734809>🏆</tg-emoji> Top apps:\n{}",
        "not_found": "<tg-emoji emoji-id=5210952531676504517>❌</tg-emoji>Not found, sry",
        "app_line": "{}. <a href=\"https://play.google.com/store/apps/details?id={}\">{}</a> — ⭐ {}\n   <i>{}</i> • {}",
        "sub_added": "Subscribed to <b>{}</b> ({})",
        "sub_removed": "Unsubscribed from <b>{}</b>",
        "sub_exists": "Already subscribed to <b>{}</b>",
        "sub_missing": "You are not subscribed to <b>{}</b>",
        "sub_list_empty": " No subscriptions",
        "sub_list": "Your subscriptions:\n{}",
        "sub_item": "• <b>{}</b> — <code>{}</code>",
        "update_notify": "🔄 <b>Update available!</b>\n\n<b>{}</b>\n Version: <code>{}</code>\nUpdated: {}\n\n<a href=\"https://play.google.com/store/apps/details?id={}\">Open in Play Store</a>",
        "sub_usage": "Usage: <code>.subscribe &lt;app_id&gt;</code>\nExample: <code>.subscribe com.nianticlabs.pokemongo</code>",
        "unsub_usage": "Usage: <code>.unsubscribe &lt;app_id&gt;</code>",
    }
    def __init__(self):
        self.config = loader.ModuleConfig()
    def _get_subs(self):
        return self._db.get("playsearch", "subs", default={})
    def _save_subs(self, subs):
        self._db.set("playsearch", "subs", subs)
    @loader.loop(interval=300, autostart=True)
    async def poller(self):
        subs = self._get_subs()
        if not subs:
            return
        for app_id, info in list(subs.items()):
            try:
                data = gp_app(app_id, lang="en", country="us")
            except Exception as e:
                logger.error(f"Error fetching {app_id}: {e}")
                continue
            new_version = data.get('version', '')
            new_updated = data.get('updated', 0)
            old_version = info.get('version', '')
            old_updated = info.get('updated', 0)
            if new_version != old_version or new_updated != old_updated:
                info['version'] = new_version
                info['updated'] = new_updated
                subs[app_id] = info
                self._save_subs(subs)
                if old_version:
                    for user_id in info.get('users', []):
                        try:
                            await self._client.send_message(
                                user_id,
                                self.strings['update_notify'].format(
                                    data.get('title', app_id),
                                    new_version,
                                    new_updated,
                                    app_id
                                ),
                                disable_web_page_preview=True
                            )
                        except Exception as e:
                            logger.error(f"Error notifying {user_id}: {e}")

    def _game_nav(self, pages, index):
        if len(pages) <= 1:
            return None
        buttons = []
        if index > 0:
            buttons.append({"text": "◀️", "callback": self._game_page, "args": (pages, index - 1)})
        buttons.append({"text": f"{index + 1}/{len(pages)}", "callback": self._game_page, "args": (pages, index)})
        if index < len(pages) - 1:
            buttons.append({"text": "▶️", "callback": self._game_page, "args": (pages, index + 1)})
        return [buttons]

    async def _game_page(self, call, pages, index):
        await call.edit(pages[index], reply_markup=self._game_nav(pages, index))

    @loader.command()
    async def game(self, message: Message):
        """
        Find games.
        """
        args = utils.get_args_raw(message)
        if not args:
            await message.edit(self.strings['not_found'])
            return
        await message.edit(self.strings['searching'])
        try:
            results = gp_search(args, lang="en", country="us", n_hits=15)
        except Exception as e:
            logger.error(f"Error: {e}")
            await message.edit(self.strings['not_found'])
            return
        if not results:
            await message.edit(self.strings['not_found'])
            return

        pages = []
        step = 15 if self.config.get("show_all_15", False) else 5
        for page_start in range(0, len(results), step):
            chunk = results[page_start:page_start + step]
            lines = []
            for index, app in enumerate(chunk, start=page_start + 1):
                if not app:
                    continue
                app_id = app.get('appId', '')
                title = app.get('title', 'Unknown')
                score = app.get('score', 0)
                score = round(score, 2) if score else "N/A"
                genre = app.get('genre', 'N/A')
                installs = app.get('installs', 'N/A')
                lines.append(self.strings['app_line'].format(index, app_id, title, score, genre, installs))
            runs_text = "<blockquote expandable>" + "\n".join(lines) + "</blockquote>"
            pages.append(self.strings['game'].format(args, len(results), runs_text))

        await self.inline.form(
            message=message,
            text=pages[0],
            reply_markup=self._game_nav(pages, 0)
        )

    @loader.command()
    async def subscribe(self, message: Message):
        "Subscribe to updates of the game."
        args = utils.get_args_raw(message)
        if not args:
            await message.edit(self.strings['sub_usage'])
            return
        app_id = args.strip()
        try:
            data = gp_app(app_id, lang="en", country="us")
        except Exception as e:
            logger.error(f"Error: {e}")
            await message.edit(self.strings['not_found'])
            return
        subs = self._get_subs()
        user_id = message.sender_id
        if app_id in subs:
            if user_id in subs[app_id].get('users', []):
                await message.edit(self.strings['sub_exists'].format(data.get('title', app_id)))
                return
            subs[app_id].setdefault('users', []).append(user_id)
        else:
            subs[app_id] = {
                'title': data.get('title', app_id),
                'version': data.get('version', ''),
                'updated': data.get('updated', 0),
                'users': [user_id],
            }
        self._save_subs(subs)
        await message.edit(self.strings['sub_added'].format(data.get('title', app_id), app_id))

    @loader.command()
    async def unsubscribe(self, message: Message):
        "Subcribe, but the other way."
        args = utils.get_args_raw(message)
        if not args:
            await message.edit(self.strings['unsub_usage'])
            return
        app_id = args.strip()
        subs = self._get_subs()
        user_id = message.sender_id
        if app_id not in subs or user_id not in subs[app_id].get('users', []):
            await message.edit(self.strings['sub_missing'].format(app_id))
            return
        subs[app_id]['users'].remove(user_id)
        title = subs[app_id].get('title', app_id)
        if not subs[app_id]['users']:
            del subs[app_id]
        self._save_subs(subs)
        await message.edit(self.strings['sub_removed'].format(title))

    @loader.command()
    async def mysubs(self, message: Message):
        "Your list..."
        subs = self._get_subs()
        user_id = message.sender_id
        user_subs = {aid: info for aid, info in subs.items() if user_id in info.get('users', [])}
        if not user_subs:
            await message.edit(self.strings['sub_list_empty'])
            return
        items = []
        for aid, info in user_subs.items():
            items.append(self.strings['sub_item'].format(info.get('title', aid), aid))
        await message.edit(self.strings['sub_list'].format("\n".join(items)))
