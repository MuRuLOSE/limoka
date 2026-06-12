# meta developer: @SunnexGB
# requires: aiohttp
# meta pic: https://r2.fakecrime.bio/uploads/ab42b5e2-91f1-4ed1-8002-51b3184e3839.jpg
# meta banner: https://r2.fakecrime.bio/uploads/ab42b5e2-91f1-4ed1-8002-51b3184e3839.jpg
# meta fhsdesc: YaMusic, music, музыка, яндекс музыка,Lyrics, слова, текст, трек, песня
# все же я не знаю трек или сонг, так что пусть будет трек, а не сонг потому что интуитивнее поняттнее,наверное?
# крутой баннер да?
#current version
__version__ = (1, 1, 2)

from herokutl.types import Message
from .. import loader, utils
from ..types import InlineCall
import aiohttp
import asyncio
import re


@loader.tds
class YandexLyrics(loader.Module):
    """life lyrics current song"""

    strings = {
        "name": "YandexLyrics",
        "no_YaMusicMod": "<tg-emoji emoji-id=5431402435497181911>💢</tg-emoji> <b>YaMusicMod not found,but u can install it. You can also support developer: </b> @codrago_m",
        "no_auth": "<tg-emoji emoji-id=5429225166250984904>⁉️</tg-emoji><b> You not authorized in SpotifyMod, visit you Saved Messages and setup token to continue.</b>",
        "no_ym": "<tg-emoji emoji-id=5429164207780152924>😅</tg-emoji> <b>Nothing is playing on YaMusic.</b>",
        "no_lyrics": "<tg-emoji emoji-id=5431402435497181911>💢</tg-emoji> <b>Lyrics not found for:</b> <code>{}</code>",
        "not_synced": "<i><tg-emoji emoji-id=5431445849026611010>⚠️</tg-emoji> Lyrics are not synchronized.</i>\n\n",
        "finished": "<tg-emoji emoji-id=5429638011392377649>‼️</tg-emoji> Playback ended or track changed.",
        "header": "<tg-emoji emoji-id=5429413328768224565>🎤</tg-emoji> <b>{} - {}</b>\n\n",
        "timeout": "<b><tg-emoji emoji-id=5429455831764584284>⏳</tg-emoji></b><b> Oopsi, looks like we've got a timeout here</b>.",

    }

    strings_ru = {
        "cls_doc": "Лайв слова текущей песни.",
        "no_YaMusicMod": "<tg-emoji emoji-id=5431402435497181911>💢</tg-emoji> <b>YaMusicMod не найден,но его можно установить. Вы также можете поддержать разработчика: </b> @codrago_m",
        "no_auth": "<tg-emoji emoji-id=5429225166250984904>⁉️</tg-emoji><b> Вы не авторизированы в YaMusicMod, перейдите в Избранное и установите токен для продолжения работы.</b>",
        "no_ym": "<tg-emoji emoji-id=5429164207780152924>😅</tg-emoji> <b>В YaMusic ничего не играет.</b>",
        "no_lyrics": "<tg-emoji emoji-id=5431402435497181911>💢</tg-emoji> <b>Текст не найден для:</b> <code>{}</code>",
        "not_synced": "<i><tg-emoji emoji-id=5431445849026611010>⚠️</tg-emoji> Текст не синхронизирован.</i>\n\n",
        "finished": "<tg-emoji emoji-id=5429638011392377649>‼️</tg-emoji> Воспроизведение завершено или трек сменился.",
        "header": "<tg-emoji emoji-id=5429413328768224565>🎤</tg-emoji> <b>{} - {}</b>\n\n",
        "timeout": "<b><tg-emoji emoji-id=5429455831764584284>⏳</tg-emoji></b><b> Упси, похоже кто то словил таймаут.</b>.",
    }


    def __init__(self):
        self._active_tasks: dict = {}
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "emoji_current",
                "<tg-emoji emoji-id='5215679757366089921'>🤯</tg-emoji>",
                "Emoji for current line",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "dot",
                "♪",
                "instrumental_emoji or text",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "lyrics_delay",
                0.5,
                "delay in switching to a new timing sector with words",
            ),
            loader.ConfigValue(
                "request_timeout",
                12,
                "timeout value",
            ),
        )

    async def install_yamusic(self, call: InlineCall):
        mod_url = "https://raw.githubusercontent.com/coddrago/modules/main/YaMusic.py"
        try:
            m = self.lookup("Modules") or self.lookup("loader")
            await m.download_and_install(mod_url)
            await call.answer("YaMusicMod installed!", show_alert=True)
            mod = self.lookup("YaMusicMod")
            acs_tkn = mod.get("__config__")["token"] if mod else "****"
            if not acs_tkn:
                await self.invoke("yguide", " ", "me")
                await call.edit(
                    self.strings("no_auth"),    
                    reply_markup=[[{"text": "Хорошо", "callback": self.close}]],
                )
            else:
                await call.delete()
        except Exception as e:
            await call.answer(f"Error! Check logs.\n{e}", show_alert=True)

    def close(self, call: InlineCall):
        return call.delete()

    async def _get_lyrics(self, artist: str, track: str):
        clean_track = re.sub(r"\(.*?\)|\[.*?\]", "", track).strip()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://lrclib.net/api/search",
                    params={"track_name": clean_track, "artist_name": artist},
                    timeout=aiohttp.ClientTimeout(total=(self.config["request_timeout"])),
                ) as resp:
                    if resp.status == 200:
                        res = await resp.json()
                        return res[0] if res else None
        except asyncio.TimeoutError:
            return {"timeout": True}
        except Exception:
            pass
        return None

    def _parse_synced(self, synced_text: str) -> list:
        lines = []
        for line in synced_text.split("\n"):
            m = re.search(r"\[(\d+):(\d+\.\d+)\](.*)", line)
            if m:
                mins, secs, text = m.groups()
                lines.append({
                    "time": (int(mins) * 60 + float(secs)) * 1000,
                    "text": text.strip(),
                })
        return lines

    def _build_content(self, artist, track, lines, plain, progress_ms, not_synced_str):
        header = self.strings("header").format(
            utils.escape_html(artist),
            utils.escape_html(track),
        )
        if lines:
            curr_idx = 0
            for i, line in enumerate(lines):
                if progress_ms >= line["time"]:
                    curr_idx = i
            win_start = max(0, curr_idx - 1)
            win_end = min(len(lines), curr_idx + 6)
            rows = []
            for i in range(win_start, win_end):
                t = lines[i]["text"] or self.config["dot"]
                if i == curr_idx:
                    rows.append(
                        f"<b>{self.config['emoji_current']} {utils.escape_html(t)}</b>"
                    )
                else:
                    rows.append(f"<code>{utils.escape_html(t)}</code>")
            return header + "\n".join(rows)
        else:
            return header + not_synced_str + f"<blockquote expandable>{utils.escape_html((plain or '')[:4000])}</blockquote>"

    def _markup(self, song_url):
        return [
            [{"text": "🔗 song.link", "url": song_url}],
            [{"text": "❌ Close", "callback": self._close_cb}],
        ]

    async def _close_cb(self, call):
        for track_id, task in list(self._active_tasks.items()):
            task.cancel()
            self._active_tasks.pop(track_id, None)
        try:
            await call.answer()
            await call.delete()
        except Exception:
            pass

    async def run_loop(self, form, mod, track_id, artist_name, track_name, song_url, lines, plain, not_synced_str):
        last_display = ""
        try:
            while True:
                pb = await mod._YaMusicMod__get_now_playing()
                if not pb or not pb.get("track") or pb["track"]["track_id"] != track_id:
                    try:
                        await form.edit(
                            self.strings("finished"),
                            reply_markup=[[{"text": "❌ Close", "callback": self._close_cb}]],
                        )
                    except Exception:
                        pass
                    break

                prog = pb.get("progress_ms", 0)
                content = self._build_content(
                    artist_name, track_name, lines, plain, prog, not_synced_str
                )

                if content != last_display:
                    try:
                        await form.edit(content, reply_markup=self._markup(song_url))
                        last_display = content
                    except Exception:
                        break

                if not lines:
                    break

                await asyncio.sleep(self.config["lyrics_delay"])

        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        finally:
            self._active_tasks.pop(track_id, None)

    @loader.command(ru_doc="- показать синхронизированный текст песни")
    async def ynowlcmd(self, message: Message):
        """- show synchronized lyrics for current YaMusic track"""
        mod = self.lookup("YaMusic")
        if not mod:
            form = await self.inline.form("⏳", message=message)
            await form.edit(
                self.strings("no_YaMusicMod"),
                reply_markup=[[{"text": "Install YaMusic", "callback": self.install_yamusic}]],
            )
            return

        ya_token = mod.get("__config__")["token"]
        if not ya_token:
            await self.invoke("yguide", " ", "me")
            form = await self.inline.form("⏳", message=message)
            await form.edit(
                self.strings("no_auth"),
                reply_markup=[[{"text": "Хорошо", "callback": self.close}]],
                )
            return
        
        playback = await mod._YaMusicMod__get_now_playing()
        if not playback or not playback.get("track"):
            return await utils.answer(message, self.strings("no_ym"))

        track = playback["track"]
        track_id = track["track_id"]
        artist_name = ", ".join(track["artist"])
        track_name = track["title"]
        song_url = f"https://song.link/s/{track_id}"

        old = self._active_tasks.pop(track_id, None)
        if old:
            old.cancel()

        data = await self._get_lyrics(artist_name, track_name)
        if data and data.get("timeout"):
            return utils.answer(
                message,
                self.strings["timeout"]
            )
        if not data or data.get("instrumental"):
            track_and_artist = f"{utils.escape_html(track_name)} - {utils.escape_html(artist_name)}"
            return await utils.answer(
                message,
                self.strings("no_lyrics").format(track_and_artist),
            )

        synced_raw = data.get("syncedLyrics")
        plain = data.get("plainLyrics", "")

        lines = self._parse_synced(synced_raw) if synced_raw else []
        not_synced_str = self.strings("not_synced")

        prog = playback.get("progress_ms", 0)
        initial_content = self._build_content(
            artist_name, track_name, lines, plain, prog, not_synced_str
        )

        form = await self.inline.form(
            text=initial_content,
            message=message,
            reply_markup=self._markup(song_url),
        )

        task = asyncio.create_task(
            self.run_loop(
                form=form,
                mod=mod,
                track_id=track_id,
                artist_name=artist_name,
                track_name=track_name,
                song_url=song_url,
                lines=lines,
                plain=plain,
                not_synced_str=not_synced_str,
            )
        )
        self._active_tasks[track_id] = task

                # Fan-fantasizing
                # Fa-fa-fa-fantasizing
                # You and I-I-I
                # When I close my eyes (my eyes)
                # Nothings real
                # Fantasizing (fantasizing)
                # Bout you and I
                # Cos you only hit my line
                # When you wanna waste time
                # I know you're so busy
                # But trust me baby I'm not blind (blind)
                # Uh oh, you and I
                # We could never be
                # Uh oh you and I
                # Cos we will never be
                # Uh oh, you and I
                # No, we will never be
                # That pretty picture that I painted in my mind (mind)
                # So tell me what (tell me, tell me)
                # The view is like
                # With your head in the clouds
                # And tell me what (tell me, tell me)
                # It feels like to be right all the time
                # You say that you love me
                # But you don't even love yourself (no)
                # Wanna get in my head
                # But I ain't gonna let you close (no)
                # Tryna control me
                # But I ain't gon' play your game
                # No more
                # No I won't
                # When I close (when I close)
                # My eyes (my eyes)
                # Nothing's real (no)
                # Fantasizing (fantasize)
                # bout you-you-you-you-you
                # You-you-you-you
                # You-you-you-you
                # You-you-you
                # And I
                # You-you-you-you-you-you-you
                # You-you-you-you-you-you-you
                # You-you-you-you-you
                # And I
                # This is the last time I tell you
                # Don't come round my way if you're just gon' waste my time
                # And no, I won't be there for the long run
                # No, not I
                # But you never get (never get)
                # The message, do you?
                # You never seem (never seem)
                # To grip an understanding
                # That you emulate a ghost
                # I pointed out all of your flaws
                # But you still came up with excuses for em all
                # So typical (so typical)
                # You know it all
                # So of course, I'm the one that's wrong (right?)
                # When I close my eyes
                # Nothings real
                # Fan- fantasize
                # Fa-fa-fa-fa
                # Fantasizing
                # Fa-fantasizing bout you and I