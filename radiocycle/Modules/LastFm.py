# ---------------------------------------------------------------------------------
#░█▀▄░▄▀▀▄░█▀▄░█▀▀▄░█▀▀▄░█▀▀▀░▄▀▀▄░░░█▀▄▀█
#░█░░░█░░█░█░█░█▄▄▀░█▄▄█░█░▀▄░█░░█░░░█░▀░█
#░▀▀▀░░▀▀░░▀▀░░▀░▀▀░▀░░▀░▀▀▀▀░░▀▀░░░░▀░░▒▀
# Name: LastFM
# Description: Module for music from different services
# Author: @codrago_m
# ---------------------------------------------------------------------------------
# 🔒    Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html
# ---------------------------------------------------------------------------------
# Author: @codrago
# Commands: nowplay
# scope: heroku_only
# meta developer: @ke_mods
# meta banner: https://raw.githubusercontent.com/coddrago/modules/refs/heads/main/banner.png
# meta pic: https://envs.sh/Hob.webp
# ---------------------------------------------------------------------------------

# =======================================
#   _  __         __  __           _
#  | |/ /___     |  \/  | ___   __| |___
#  | ' // _ \    | |\/| |/ _ \ / _` / __|
#  | . \  __/    | |  | | (_) | (_| \__ \
#  |_|\_\___|    |_|  |_|\___/ \__,_|___/
#           @ke_mods
# =======================================
#
#  LICENSE: CC BY-ND 4.0 (Attribution-NoDerivatives 4.0 International)
#  --------------------------------------
#  https://creativecommons.org/licenses/by-nd/4.0/legalcode
# =======================================

# Forked from @codrago_m. Banners from YaMusic by @kamekuro_hmods

from .. import loader, utils 
import requests
import io
import textwrap
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

# Forked from @codrago_m. Banners from YaMusic by @kamekuro_hmods

class Banners:
    def __init__(self, title, artists, track_cover, font_url):
        self.title = title
        self.artists = artists
        self.track_cover = track_cover
        self.font_bytes = requests.get(font_url).content

    def _prepare_base(self):
        W, H = 1920, 768
        tf = ImageFont.truetype(io.BytesIO(self.font_bytes), 80)
        af = ImageFont.truetype(io.BytesIO(self.font_bytes), 55)
        img = Image.open(io.BytesIO(self.track_cover)).convert("RGBA")
        banner = img.resize((W, W)).crop((0, (W-H)//2, W, ((W-H)//2)+H)).filter(ImageFilter.GaussianBlur(30))
        banner = ImageEnhance.Brightness(banner).enhance(0.3)
        cov = img.resize((H - 150, H - 150))
        mask = Image.new("L", cov.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, *cov.size), radius=35, fill=255)
        banner.paste(cov, (75, 75), mask)
        return banner, ImageDraw.Draw(banner), tf, af

    def measure(self, text, font, draw):
        b = draw.textbbox((0, 0), text, font=font)
        return b[2] - b[0], b[3] - b[1]

    def new(self):
        banner, draw, tf, af = self._prepare_base()
        lf = ImageFont.truetype(io.BytesIO(self.font_bytes), 40)
        space = (743, 75, 1870, 693)
        t_lines = textwrap.wrap(self.title, 23)[:2]
        if len(t_lines) > 1 and len(textwrap.wrap(self.title, 23)) > 2: t_lines[-1] += "…"
        a_lines = textwrap.wrap(self.artists, 23)[:1]
        if len(textwrap.wrap(self.artists, 23)) > 1: a_lines[-1] += "…"
        content = [
            *({"t": l, "f": tf, "c": "#FFFFFF"} for l in t_lines),
            *({"t": l, "f": af, "c": "#FFFFFF"} for l in a_lines),
            {"t": "last.fm", "f": lf, "c": "#A0A0A0"}
        ]
        h_list = [self.measure(i["t"], i["f"], draw)[1] for i in content]
        total_h = sum(h_list) + 35 * (len(content) - 1)
        y = space[1] + (space[3] - space[1] - total_h) // 2
        for i, item in enumerate(content):
            w, _ = self.measure(item["t"], item["f"], draw)
            draw.text((space[0] + (space[2] - space[0] - w) / 2, y), item["t"], font=item["f"], fill=item["c"])
            y += h_list[i] + 35

        return self._save(banner)

    def old(self):
        banner, draw, tf, af = self._prepare_base()
        lf = ImageFont.truetype(io.BytesIO(self.font_bytes), 80)
        t_lines = textwrap.wrap(self.title, 23)[:2]
        if len(textwrap.wrap(self.title, 23)) > 2: t_lines[1] += "..."
        a_lines = textwrap.wrap(self.artists, 40)
        a_lines = [x[:x.rfind(", ")-1] if "•" in x[-2:] else x for x in a_lines]
        y = 110
        for i, l in enumerate(t_lines):
            draw.text((150 + (768 - 150), y), l, font=tf, fill="#FFFFFF")
            y += 70 if i != len(t_lines)-1 else 0
        
        y = 110 * 2 + (70 if len(t_lines) > 1 else 0)
        for i, l in enumerate(a_lines):
            draw.text((150 + (768 - 150), y), l, font=af, fill="#A0A0A0")
            y += 50

        draw.text((768, 578), "last.fm", font=lf, fill="#FFFFFF")
        return self._save(banner)

    def _save(self, img):
        out = io.BytesIO()
        img.save(out, format="PNG")
        out.seek(0)
        out.name = "banner.png"
        return out

# Forked from @codrago_m. Banners from YaMusic by @kamekuro_hmods

@loader.tds
class lastfmmod(loader.Module):
    """Module for music from different services. Forked from @codrago_m. Banners from YaMusic by @kamekuro_hmods"""

# Forked from @codrago_m. Banners from YaMusic by @kamekuro_hmods

    strings = {
        "name": "LastFm",
        "no_track": "<emoji document_id=5465665476971471368>❌</emoji> <b>No track is currently playing</b>",
        "_doc_text": "The text that will be written next to the file",
        "_doc_username": "Your username from last.fm",
        "nick_error": "<emoji document_id=5465665476971471368>❌</emoji> <b>Put your nickname from last.fm</b>",
        "uploading": "<emoji document_id=5841359499146825803>🕔</emoji> <i>Uploading banner...</i>",
    }
    strings_ru = {
        "name": "LastFm",
        "no_track": "<emoji document_id=5465665476971471368>❌</emoji> <b>Сейчас ничего не играет</b>",
        "_doc_text": "Текст, который будет написан рядом с файлом",
        "_doc_username": "Ваш username с last.fm",
        "nick_error": "<emoji document_id=5465665476971471368>❌</emoji> <b>Укажите ваш никнейм с last.fm</b>",
        "uploading": "<emoji document_id=5841359499146825803>🕔</emoji> <i>Загрузка баннера...</i>",
    }
    strings_jp = {
        "name": "LastFm",
        "no_track": "<emoji document_id=5465665476971471368>❌</emoji> <b>現在再生中のトラックはありません</b>",
        "_doc_text": "ファイルの横に表示されるテキスト",
        "_doc_username": "Last.fmのユーザー名",
        "nick_error": "<emoji document_id=5465665476971471368>❌</emoji> <b>Last.fmのニックネームを入力してください</b>",
        "uploading": "<emoji document_id=5841359499146825803>🕔</emoji> <i>バナーをアップロード中...</i>",
    }

# Forked from @codrago_m. Banners from YaMusic by @kamekuro_hmods

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue("username", None, lambda: self.strings["_doc_username"]),
            loader.ConfigValue("custom_text", "<emoji document_id=5413612466208799435>🤩</emoji> <b>{song_name}</b> — <b>{song_artist}</b>", lambda: self.strings["_doc_text"]),
            loader.ConfigValue("font", "https://raw.githubusercontent.com/kamekuro/assets/master/fonts/Onest-Bold.ttf", "Custom font URL (ttf)"),
            loader.ConfigValue("banner_version", "new", lambda: "Banner version", validator=loader.validators.Choice(["old", "new"])),
        )

# Forked from @codrago_m. Banners from YaMusic by @kamekuro_hmods

    @loader.command(alias="np")
    async def nowplay(self, message):
        """| send playing track info"""
        user = self.config["username"]
        if not user:
            await self.invoke("config", "lastfm", message=message)
            return await utils.answer(message, self.strings["nick_error"])
            
        try:
            url = f'http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&nowplaying=true&user={user}&api_key=460cda35be2fbf4f28e8ea7a38580730&format=json'
            data = requests.get(url).json()
            track = next((t for t in data.get('recenttracks', {}).get('track', []) if t.get('@attr', {}).get('nowplaying')), None)
            if not track:
                return await utils.answer(message, self.strings["no_track"])
            name = track.get('name', 'Unknown')
            artist = track.get('artist', {}).get('#text', 'Unknown')
            caption = self.config["custom_text"].format(song_artist=artist, song_name=name)
            imgs = track.get('image', [])
            cov_url = next((i['#text'] for i in imgs if i['size'] == 'extralarge'), imgs[-1]['#text'] if imgs else None)

            if not cov_url:
                return await utils.answer(message, caption)
            msg = await utils.answer(message, self.strings["uploading"])
            cov_bytes = await utils.run_sync(requests.get, cov_url)
            banners = Banners(name, artist, cov_bytes.content, self.config["font"])
            file = await utils.run_sync(getattr(banners, self.config["banner_version"]))
            await utils.answer(msg, caption, file=file)

        except Exception as e:
            await utils.answer(message, f"<pre><code class='language-python'>{e}</code></pre>")

# Forked from @codrago_m. Banners from YaMusic by @kamekuro_hmods
