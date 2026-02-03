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

# meta developer: @ke_mods

from .. import loader, utils 
import requests
import io
import textwrap
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

class Banners:
    def __init__(
        self,
        title: str,
        artists: list,
        track_cover: bytes,
        font
    ):
        self.title = title
        self.artists = ", ".join(artists) if isinstance(artists, list) else artists
        self.track_cover = track_cover
        self.font_url = font

    def _get_font(self, size, font_bytes):
        return ImageFont.truetype(io.BytesIO(font_bytes), size)

    def _prepare_cover(self, size, radius):
        cover = Image.open(io.BytesIO(self.track_cover)).convert("RGBA")
        cover = cover.resize((size, size), Image.Resampling.LANCZOS)
        
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, size, size), radius=radius, fill=255)
        
        output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        output.paste(cover, (0, 0), mask=mask)
        return output

    def _prepare_background(self, w, h):
        bg = Image.open(io.BytesIO(self.track_cover)).convert("RGBA")
        bg = bg.resize((w, h), Image.Resampling.BICUBIC)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=20))
        bg = ImageEnhance.Brightness(bg).enhance(0.4) 
        return bg

    def horizontal(self):
        W, H = 1500, 600
        padding = 60
        cover_size = 480
        
        font_bytes = requests.get(self.font_url).content
        title_font = self._get_font(55, font_bytes)
        artist_font = self._get_font(45, font_bytes)
        lfm_font = self._get_font(35, font_bytes)

        img = self._prepare_background(W, H)
        draw = ImageDraw.Draw(img)
        
        cover = self._prepare_cover(cover_size, 30)
        img.paste(cover, (padding, (H - cover_size) // 2), cover)

        text_x = padding + cover_size + 60
        text_y_start = 100
        text_width_limit = W - text_x - padding

        display_title = self.title
        while title_font.getlength(display_title) > text_width_limit and len(display_title) > 0:
            display_title = display_title[:-1]
        if len(display_title) < len(self.title): display_title += "…"

        display_artist = self.artists
        while artist_font.getlength(display_artist) > text_width_limit and len(display_artist) > 0:
            display_artist = display_artist[:-1]
        if len(display_artist) < len(self.artists): display_artist += "…"

        draw.text((text_x, text_y_start), display_title, font=title_font, fill="white")
        draw.text((text_x, text_y_start + 70), display_artist, font=artist_font, fill="#B3B3B3")

        bar_y = 480
        draw.text((text_x, bar_y), "last.fm", font=lfm_font, fill="white")

        by = io.BytesIO()
        img.save(by, format="PNG")
        by.seek(0)
        by.name = "banner.png"
        return by

    def vertical(self):
        W, H = 1000, 1500
        padding = 80
        cover_size = 800
        
        font_bytes = requests.get(self.font_url).content
        title_font = self._get_font(60, font_bytes)
        artist_font = self._get_font(45, font_bytes)
        lfm_font = self._get_font(35, font_bytes)

        img = self._prepare_background(W, H)
        draw = ImageDraw.Draw(img)

        cover = self._prepare_cover(cover_size, 40)
        cover_x = (W - cover_size) // 2
        cover_y = 120
        img.paste(cover, (cover_x, cover_y), cover)

        text_area_y = cover_y + cover_size + 120
        text_width_limit = W - (padding * 2)

        display_title = self.title
        while title_font.getlength(display_title) > text_width_limit and len(display_title) > 0:
            display_title = display_title[:-1]
        if len(display_title) < len(self.title): display_title += "…"

        display_artist = self.artists
        while artist_font.getlength(display_artist) > text_width_limit and len(display_artist) > 0:
            display_artist = display_artist[:-1]
        if len(display_artist) < len(self.artists): display_artist += "…"

        title_w = title_font.getlength(display_title)
        draw.text(((W - title_w) / 2, text_area_y), display_title, font=title_font, fill="white")

        artist_w = artist_font.getlength(display_artist)
        draw.text(((W - artist_w) / 2, text_area_y + 75), display_artist, font=artist_font, fill="#B3B3B3")

        bar_y = text_area_y + 260
        
        lfm_w = lfm_font.getlength("last.fm")
        draw.text(((W - lfm_w) / 2, bar_y), "last.fm", font=lfm_font, fill="white")

        by = io.BytesIO()
        img.save(by, format="PNG")
        by.seek(0)
        by.name = "banner.png"
        return by

@loader.tds
class lastfmmod(loader.Module):
    """Module for music from different services"""

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

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue("username", None, lambda: self.strings["_doc_username"]),
            loader.ConfigValue("custom_text", "<emoji document_id=5413612466208799435>🤩</emoji> <b>{song_name}</b> — <b>{song_artist}</b>", lambda: self.strings["_doc_text"]),
            loader.ConfigValue("font", "https://raw.githubusercontent.com/kamekuro/assets/master/fonts/Onest-Bold.ttf", "Custom font URL (ttf)"),
            loader.ConfigValue("banner_version", "horizontal", lambda: "Banner version", validator=loader.validators.Choice(["horizontal", "vertical"])),
        )

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
