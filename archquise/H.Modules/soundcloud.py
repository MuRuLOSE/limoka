# Proprietary License Agreement

# Copyright (c) 2024-29 CodWiz

# Permission is hereby granted to any person obtaining a copy of this software and associated documentation files (the "Software"), to use the Software for personal and non-commercial purposes, subject to the following conditions:

# 1. The Software may not be modified, altered, or otherwise changed in any way without the explicit written permission of the author.

# 2. Redistribution of the Software, in original or modified form, is strictly prohibited without the explicit written permission of the author.

# 3. The Software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement. In no event shall the author or copyright holder be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the Software or the use or other dealings in the Software.

# 4. Any use of the Software must include the above copyright notice and this permission notice in all copies or substantial portions of the Software.

# 5. By using the Software, you agree to be bound by the terms and conditions of this license.

# For any inquiries or requests for permissions, please contact codwiz@yandex.ru.

# ---------------------------------------------------------------------------------
# Name: SoundCloud
# Description: Card with the currently playing track on SoundCloud
# Author: @hikka_mods
# ---------------------------------------------------------------------------------
# meta developer: @hikka_mods
# scope: SoundCloud
# scope: SoundCloud 0.0.2
# requires: requests pillow yt-dlp
# ---------------------------------------------------------------------------------

import contextlib
import dataclasses
import functools
import hashlib
import io
import logging
from typing import Dict, List, Optional

import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from telethon.tl.types import Message
from yt_dlp import YoutubeDL

from .. import loader, utils

logger = logging.getLogger(__name__)

_API = "https://api-v2.soundcloud.com"
_COVER_HQ = "-t500x500"

_ORANGE = (255, 85, 0)
_DIM = (155, 155, 170)
_FADED = (100, 100, 115)
_CARD_BG = (255, 255, 255, 14)
_CARD_ACTIVE = (255, 255, 255, 26)
_BAR_MUTED = (255, 255, 255, 16)


@dataclasses.dataclass(frozen=True)
class TrackInfo:
    """Parsed SoundCloud track metadata."""

    track_id: int
    title: str
    artist: str
    duration_ms: int
    permalink: str
    cover_url: str
    genre: str
    plays: int
    likes: int
    reposts: int
    comments: int

    @classmethod
    def parse(cls, raw: dict) -> "TrackInfo":
        u = raw.get("user") or {}
        return cls(
            track_id=raw.get("id", 0),
            title=raw.get("title") or "Unknown",
            artist=u.get("username") or "Unknown",
            duration_ms=raw.get("duration") or raw.get("full_duration") or 0,
            permalink=raw.get("permalink_url") or "",
            cover_url=raw.get("artwork_url") or u.get("avatar_url") or "",
            genre=raw.get("genre") or "",
            plays=raw.get("playback_count") or 0,
            likes=raw.get("likes_count") or raw.get("favoritings_count") or 0,
            reposts=raw.get("reposts_count") or 0,
            comments=raw.get("comment_count") or 0,
        )

    @property
    def duration_fmt(self) -> str:
        s = self.duration_ms // 1000
        return f"{s // 60}:{s % 60:02d}"

    @property
    def hq_cover(self) -> str:
        return self.cover_url.replace("-large", _COVER_HQ)


def _compact(n: int) -> str:
    """Format large numbers: 12500 → 12.5K."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


class _Fonts:
    """Cached font loader from raw bytes."""

    __slots__ = ("_raw", "_loaded")

    def __init__(self, data: bytes):
        self._raw = data
        self._loaded: Dict[int, ImageFont.FreeTypeFont] = {}

    def __call__(self, size: int) -> ImageFont.FreeTypeFont:
        if size not in self._loaded:
            self._loaded[size] = ImageFont.truetype(io.BytesIO(self._raw), size)
        return self._loaded[size]

    def fit(self, text: str, max_w: int, hi: int, lo: int) -> ImageFont.FreeTypeFont:
        for s in range(hi, lo - 1, -2):
            f = self(s)
            if f.getlength(text) <= max_w:
                return f
        return self(lo)


def _ellipsis(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> str:
    """Truncate text with '…' using binary search."""
    if font.getlength(text) <= max_w:
        return text
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if font.getlength(text[:mid] + "…") <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo] + "…"


def _center_text(draw, text, font, y, canvas_w, fill="white"):
    bb = draw.textbbox((0, 0), text, font=font)
    draw.text(((canvas_w - bb[2] + bb[0]) // 2, y), text, font=font, fill=fill)


def _frosted_bg(src: bytes, w: int, h: int, dim: float = 0.25) -> Image.Image:
    """Blurred & dimmed background from cover art."""
    img = Image.open(io.BytesIO(src)).convert("RGBA")
    small = img.resize((max(w // 5, 1), max(h // 5, 1)), Image.Resampling.BILINEAR)
    small = small.filter(ImageFilter.GaussianBlur(12))
    result = small.resize((w, h), Image.Resampling.BILINEAR)
    return ImageEnhance.Brightness(result).enhance(dim)


def _gradient(
    w: int, h: int, vertical: bool = True, c_from=(0, 0, 0, 160), c_to=(0, 0, 0, 40)
) -> Image.Image:
    """Fast linear gradient via 1px strip resize."""
    length = h if vertical else w
    strip = Image.new("RGBA", (1, length) if vertical else (length, 1))
    px = strip.load()
    for i in range(length):
        t = i / max(length - 1, 1)
        rgba = tuple(int(c_from[c] + (c_to[c] - c_from[c]) * t) for c in range(4))
        if vertical:
            px[0, i] = rgba
        else:
            px[i, 0] = rgba
    return strip.resize((w, h), Image.Resampling.BILINEAR)


def _round_corners(img: Image.Image, r: int) -> Image.Image:
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, *img.size), r, fill=255)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(img, mask=mask)
    return out


def _rounded_cover(data: bytes, size: int, r: int) -> Image.Image:
    img = Image.open(io.BytesIO(data)).convert("RGBA")
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    return _round_corners(img, r)


def _place_cover(
    base: Image.Image,
    cover_data: bytes,
    size: int,
    radius: int,
    pos: tuple,
    shadow_blur: int = 20,
    shadow_alpha: int = 50,
):
    """Place cover with colored drop shadow (offset downward)."""
    cover = _rounded_cover(cover_data, size, radius)
    avg = cover.resize((1, 1), Image.Resampling.BILINEAR).getpixel((0, 0))

    pad = shadow_blur * 2
    offset_y = 8
    canvas = Image.new(
        "RGBA", (size + pad * 2, size + pad * 2 + offset_y), (0, 0, 0, 0)
    )
    shadow_shape = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(shadow_shape).rounded_rectangle(
        (0, 0, size, size), radius, fill=(*avg[:3], shadow_alpha)
    )
    canvas.paste(shadow_shape, (pad, pad + offset_y), shadow_shape)
    canvas = canvas.filter(ImageFilter.GaussianBlur(shadow_blur))
    canvas.paste(cover, (pad, pad), cover)

    base.paste(canvas, (pos[0] - pad, pos[1] - pad), canvas)


def _waveform(draw, x, y, w, h, bars=45, color=_ORANGE, muted=_BAR_MUTED, prog=0.0):
    """Waveform visualization bars with sha256-seeded heights."""
    bw = max(w // (bars * 2), 2)
    gap = (w - bw * bars) // max(bars - 1, 1)
    seed = hashlib.sha256(f"sc{bars}".encode()).digest()
    for i in range(bars):
        bx = x + i * (bw + gap)
        amp = seed[i % len(seed)] / 255
        bh = int(h * (0.25 + amp * 0.75))
        by = y + (h - bh) // 2
        c = color if i / bars <= prog else muted
        draw.rounded_rectangle((bx, by, bx + bw, by + bh), bw // 2, fill=c)


def _badge(
    draw, text, font, x, y, fg="white", bg=(255, 255, 255, 18), px=12, py=5
) -> int:
    """Rounded pill badge. Returns width."""
    bb = font.getbbox(text)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pw, ph = tw + px * 2, th + py * 2
    draw.rounded_rectangle((x, y, x + pw, y + ph), ph // 2, fill=bg)
    draw.text((x + px, y + py), text, font=font, fill=fg)
    return pw


def _export(img: Image.Image, name: str = "soundcloud.png") -> io.BytesIO:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    buf.seek(0)
    buf.name = name
    return buf


class CardFactory:
    """Generates visual cards for SoundCloud tracks."""

    def __init__(self, fonts: _Fonts):
        self._f = fonts

    def square(self, track: TrackInfo, cover: bytes) -> io.BytesIO:
        """Square now-playing card (800×800)."""
        S = 800
        p = 45

        bg = _frosted_bg(cover, S, S, 0.22)
        bg = Image.alpha_composite(
            bg, _gradient(S, S, True, (0, 0, 0, 50), (0, 0, 0, 190))
        )
        draw = ImageDraw.Draw(bg)

        bf = self._f(12)
        draw.text((p, p), "SOUNDCLOUD", font=bf, fill=_ORANGE)
        lw = bf.getlength("SOUNDCLOUD")
        draw.line([(p, p + 17), (p + lw, p + 17)], fill=(*_ORANGE, 100), width=2)

        cs = 310
        cx, cy = (S - cs) // 2, p + 32
        _place_cover(bg, cover, cs, 14, (cx, cy), shadow_blur=25, shadow_alpha=50)
        draw = ImageDraw.Draw(bg)

        wy = cy + cs + 30
        _waveform(draw, p + 35, wy, S - p * 2 - 70, 26, bars=50)

        tf = self._f(13)
        draw.text((p + 35, wy + 30), "0:00", font=tf, fill=_FADED)
        ds = track.duration_fmt
        draw.text((S - p - 35 - tf.getlength(ds), wy + 30), ds, font=tf, fill=_FADED)

        tw = S - p * 2
        ty = wy + 56
        title_f = self._f.fit(track.title, tw, 36, 20)
        _center_text(draw, _ellipsis(track.title, title_f, tw), title_f, ty, S)

        af = self._f.fit(track.artist, tw, 24, 16)
        _center_text(draw, _ellipsis(track.artist, af, tw), af, ty + 44, S, _DIM)

        sy = ty + 92
        sf = self._f(14)
        parts = []
        if track.genre:
            parts.append(track.genre)
        if track.plays:
            parts.append(f"▶ {_compact(track.plays)}")
        if track.likes:
            parts.append(f"♥ {_compact(track.likes)}")
        if not parts:
            parts.append(track.duration_fmt)
        _center_text(draw, "  ·  ".join(parts), sf, sy, S, _FADED)

        return _export(_round_corners(bg, 22))

    def horizontal(self, track: TrackInfo, cover: bytes) -> io.BytesIO:
        """Wide now-playing card (1200×400)."""
        W, H = 1200, 400
        p = 40
        cs = 280

        bg = _frosted_bg(cover, W, H, 0.22)
        bg = Image.alpha_composite(
            bg, _gradient(W, H, False, (0, 0, 0, 180), (0, 0, 0, 60))
        )

        cvy = (H - cs) // 2
        _place_cover(bg, cover, cs, 14, (p, cvy), shadow_blur=20, shadow_alpha=40)
        draw = ImageDraw.Draw(bg)

        bf = self._f(11)
        draw.text((p, p - 6), "SOUNDCLOUD", font=bf, fill=_ORANGE)

        if track.genre:
            gf = self._f(12)
            gt = track.genre.upper()
            draw.text((W - p - gf.getlength(gt), p - 6), gt, font=gf, fill=_FADED)

        tx = p + cs + 50
        tw = W - tx - p

        tty = cvy + 10
        title_f = self._f.fit(track.title, tw, 36, 22)
        draw.text(
            (tx, tty),
            _ellipsis(track.title, title_f, tw),
            font=title_f,
            fill="white",
        )

        af = self._f(22)
        draw.text(
            (tx, tty + 50),
            _ellipsis(track.artist, af, tw),
            font=af,
            fill=_DIM,
        )

        by = tty + 98
        bx = tx
        pill_f = self._f(14)
        bw = _badge(
            draw,
            track.duration_fmt,
            pill_f,
            bx,
            by,
            fg=_ORANGE,
            bg=(*_ORANGE, 35),
        )
        bx += bw + 8
        if track.plays:
            bw = _badge(draw, f"▶ {_compact(track.plays)}", pill_f, bx, by, fg=_DIM)
            bx += bw + 8
        if track.likes:
            _badge(draw, f"♥ {_compact(track.likes)}", pill_f, bx, by, fg=_DIM)

        wy = cvy + cs - 50
        _waveform(draw, tx, wy, tw, 22, bars=55)

        wf = self._f(12)
        draw.text((tx, wy + 26), "0:00", font=wf, fill=_FADED)
        ds = track.duration_fmt
        draw.text((tx + tw - wf.getlength(ds), wy + 26), ds, font=wf, fill=_FADED)

        return _export(_round_corners(bg, 20))

    def history(self, tracks: List[TrackInfo], fetch_cover) -> io.BytesIO:
        """History card with dynamic height based on track count."""
        W = 1200
        p = 36
        row_h = 120
        gap = 8
        hdr = 55
        n = len(tracks)
        H = p * 2 + hdr + n * row_h + (n - 1) * gap

        bg_data = fetch_cover(tracks[0].hq_cover)
        bg = _frosted_bg(bg_data, W, H, 0.18)
        bg = Image.alpha_composite(bg, Image.new("RGBA", (W, H), (0, 0, 0, 150)))
        draw = ImageDraw.Draw(bg)

        hf = self._f(14)
        draw.text((p, p), "SOUNDCLOUD", font=hf, fill=_ORANGE)
        thf = self._f(22)
        draw.text((p, p + 20), "Listening History", font=thf, fill="white")

        lw = hf.getlength("SOUNDCLOUD")
        draw.rounded_rectangle((p, p + 48, p + lw, p + 50), 1, fill=_ORANGE)

        ct = f"{n} tracks"
        draw.text((W - p - hf.getlength(ct), p + 22), ct, font=hf, fill=_FADED)

        title_f = self._f(22)
        artist_f = self._f(16)
        time_f = self._f(14)
        num_f = self._f(12)
        cp = 12
        cvsz = row_h - cp * 2
        card_w = W - p * 2

        yo = p + hdr + 8
        for idx, trk in enumerate(tracks):
            ry = int(yo)

            card = Image.new("RGBA", (card_w, row_h), (0, 0, 0, 0))
            cd = ImageDraw.Draw(card)
            cd.rounded_rectangle(
                (0, 0, card_w, row_h),
                12,
                fill=_CARD_ACTIVE if idx == 0 else _CARD_BG,
            )
            if idx == 0:
                cd.rounded_rectangle((0, 0, 4, row_h), 2, fill=_ORANGE)
            region = bg.crop((p, ry, p + card_w, ry + row_h))
            bg.paste(Image.alpha_composite(region, card), (p, ry))

            try:
                cv_data = fetch_cover(trk.hq_cover)
                cv = _rounded_cover(cv_data, cvsz, 8)
                bg.paste(cv, (p + cp + 6, ry + cp), cv)
            except Exception:
                pass

            draw = ImageDraw.Draw(bg)

            nt = f"{idx + 1:02d}"
            nw = num_f.getlength(nt)
            nx = p + cp + 6 + (cvsz - nw) // 2
            ny = ry + cp + cvsz - 18
            draw.rounded_rectangle(
                (nx - 3, ny - 1, nx + nw + 3, ny + 14), 3, fill=(0, 0, 0, 170)
            )
            draw.text((nx, ny - 1), nt, font=num_f, fill=_ORANGE)

            txt_x = p + cp + cvsz + 24
            txt_w = card_w - cvsz - cp * 3 - 24 - 70
            ty_center = ry + (row_h - 58) // 2

            draw.text(
                (txt_x, ty_center),
                _ellipsis(trk.title, title_f, txt_w),
                font=title_f,
                fill="white",
            )
            draw.text(
                (txt_x, ty_center + 30),
                _ellipsis(trk.artist, artist_f, txt_w),
                font=artist_f,
                fill=_DIM,
            )

            dt = trk.duration_fmt
            dw = time_f.getlength(dt)
            draw.text(
                (p + card_w - cp - dw - 8, ty_center + 4),
                dt,
                font=time_f,
                fill=_FADED,
            )

            if trk.plays:
                pt = f"▶ {_compact(trk.plays)}"
                pw = time_f.getlength(pt)
                draw.text(
                    (p + card_w - cp - pw - 8, ty_center + 24),
                    pt,
                    font=time_f,
                    fill=_FADED,
                )

            yo += row_h + gap

        return _export(_round_corners(bg, 20), "soundcloud_history.png")


def _require_token(func):
    """Decorator: ensure oauth_token is configured."""

    @functools.wraps(func)
    async def wrapper(self, message, *a, **kw):
        if not self.config["oauth_token"]:
            return await utils.answer(message, self.strings("no_token"))
        return await func(self, message, *a, **kw)

    return wrapper


def _catch_errors(func):
    """Decorator: log & report exceptions to user."""

    @functools.wraps(func)
    async def wrapper(self, message, *a, **kw):
        try:
            return await func(self, message, *a, **kw)
        except Exception:
            logger.exception("SoundCloud: %s failed", func.__name__)
            with contextlib.suppress(Exception):
                import traceback

                await utils.answer(
                    message, self.strings("error").format(traceback.format_exc())
                )

    return wrapper


@loader.tds
class SoundCloudMod(loader.Module):
    """Display the currently playing SoundCloud track as a stylized card."""

    strings = {
        "name": "SoundCloud",
        "no_token": (
            "<emoji document_id=5778527486270770928>\u274c</emoji>"
            " <b>Set </b><code>oauth_token</code><b> in module config</b>\n\n"
            "\U0001f511 Get it via extension:\n"
            "\u2022 <a href='https://chromewebstore.google.com/detail/"
            "jgocamehhjhbhomfnhknmiljlhjbaldg'>Chromium</a>\n"
            "\u2022 <a href='https://addons.mozilla.org/en-US/firefox/addon/"
            "playinnowbot/'>Firefox</a>\n"
            "\u2022 Or via DevTools: Application \u2192 Cookies \u2192 "
            "<code>oauth_token</code>"
        ),
        "nothing": (
            "<emoji document_id=5778527486270770928>❌</emoji>"
            " <b>Nothing is playing right now</b>"
        ),
        "error": (
            "<emoji document_id=5778527486270770928>❌</emoji>"
            " <b>Error</b>\n<code>{}</code>"
        ),
        "wait_card": (
            "\n\n<emoji document_id=5841359499146825803>🕔</emoji>"
            " <i>Generating card…</i>"
        ),
        "wait_dl": (
            "\n\n<emoji document_id=5841359499146825803>🕔</emoji> <i>Downloading…</i>"
        ),
        "dl_fail": (
            "\n\n<emoji document_id=5778527486270770928>❌</emoji>"
            " <i>Download failed</i>"
        ),
    }

    strings_ru = {
        "no_token": (
            "<emoji document_id=5778527486270770928>❌</emoji>"
            " <b>Установи </b><code>oauth_token</code>"
            "<b> в конфиге модуля</b>\n\n"
            "🔑 Получить токен:\n"
            "• <a href='https://chromewebstore.google.com/detail/"
            "jgocamehhjhbhomfnhknmiljlhjbaldg'>Chromium</a>\n"
            "• <a href='https://addons.mozilla.org/en-US/firefox/addon/"
            "playinnowbot/'>Firefox</a>\n"
            "• Или через DevTools: Application → Cookies → "
            "<code>oauth_token</code>"
        ),
        "nothing": (
            "<emoji document_id=5778527486270770928>❌</emoji>"
            " <b>Сейчас ничего не играет</b>"
        ),
        "error": (
            "<emoji document_id=5778527486270770928>❌</emoji>"
            " <b>Ошибка</b>\n<code>{}</code>"
        ),
        "wait_card": (
            "\n\n<emoji document_id=5841359499146825803>🕔</emoji>"
            " <i>Генерация карточки…</i>"
        ),
        "wait_dl": (
            "\n\n<emoji document_id=5841359499146825803>🕔</emoji> <i>Скачивание…</i>"
        ),
        "dl_fail": (
            "\n\n<emoji document_id=5778527486270770928>❌</emoji>"
            " <i>Ошибка скачивания</i>"
        ),
    }

    def __init__(self):
        self._font_data: Optional[bytes] = None
        self._font_src: Optional[str] = None
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "show_banner",
                True,
                "Generate image card",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "banner_type",
                "square",
                "Card layout",
                validator=loader.validators.Choice(["square", "horizontal"]),
            ),
            loader.ConfigValue(
                "template",
                (
                    "<emoji document_id=6007938409857815902>🎧</emoji>"
                    " <b>Now playing:</b> {artist} — {track}\n"
                    "<emoji document_id=5776213190387961618>🕓</emoji>"
                    " {duration}{genre}\n"
                    "<emoji document_id=5877465816030515018>🔗</emoji>"
                    " <b><a href='{url}'>SoundCloud</a></b>"
                ),
                "Message template. Placeholders: {track}, {artist},"
                " {url}, {duration}, {genre}, {stats}",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "font",
                "https://github.com/web-fonts/ttf/raw/refs/heads/master/alk-sanet-webfont.ttf",
                "URL to .ttf font file",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "oauth_token",
                "",
                "SoundCloud OAuth token",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "history_count",
                5,
                "Tracks in history (3–5)",
                validator=loader.validators.Integer(minimum=3, maximum=5),
            ),
        )

    def _headers(self) -> dict:
        return {
            "Authorization": f"OAuth {self.config['oauth_token']}",
            "Accept": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            ),
        }

    async def _get(self, path: str, **params) -> Optional[dict]:
        try:
            r = await utils.run_sync(
                requests.get,
                f"{_API}{path}",
                headers=self._headers(),
                params=params,
                timeout=5,
            )
            if r.status_code == 200:
                return r.json()
        except Exception:
            logger.debug("SC API %s failed", path)
        return None

    async def _load_font(self) -> bytes:
        url = self.config["font"]
        if self._font_data and self._font_src == url:
            return self._font_data
        data = await utils.run_sync(lambda: requests.get(url, timeout=10).content)
        self._font_data = data
        self._font_src = url
        return data

    async def _load_cover(self, url: str) -> Optional[bytes]:
        try:
            hq = url.replace("-large", _COVER_HQ)
            r = await utils.run_sync(requests.get, hq, timeout=10)
            if r.status_code == 200:
                return r.content
        except Exception:
            pass
        return None

    async def _current(self) -> Optional[TrackInfo]:
        for ep in ("/me/play-history/tracks", "/me/activities", "/stream"):
            data = await self._get(ep, limit=3)
            if not data:
                continue
            for item in data.get("collection", []):
                raw = item.get("track") or item
                if raw and "title" in raw and (raw.get("duration") or 0) > 0:
                    return TrackInfo.parse(raw)
        return None

    async def _recent(self, count: int) -> List[TrackInfo]:
        data = await self._get("/me/play-history/tracks", limit=count)
        if not data:
            return []
        return [
            TrackInfo.parse(it["track"])
            for it in data.get("collection", [])
            if it.get("track") and "title" in it["track"]
        ]

    async def _download(self, url: str) -> Optional[bytes]:
        try:
            token = self.config["oauth_token"]
            opts = {
                "format": "best[ext=mp3]/best",
                "quiet": True,
                "no_warnings": True,
                "http_headers": {
                    "Authorization": f"OAuth {token}",
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    ),
                },
            }

            def _run():
                with YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    audio = info.get("url")
                    if audio:
                        r = requests.get(audio, timeout=60)
                        if r.status_code == 200:
                            return r.content
                return None

            return await utils.run_sync(_run)
        except Exception as e:
            logger.error("Download failed: %s", e)
        return None

    def _format_message(self, t: TrackInfo) -> str:
        genre_part = f" | {utils.escape_html(t.genre)}" if t.genre else ""
        stats = []
        if t.plays:
            stats.append(f"▶ {_compact(t.plays)}")
        if t.likes:
            stats.append(f"♥ {_compact(t.likes)}")
        return self.config["template"].format(
            track=utils.escape_html(t.title),
            artist=utils.escape_html(t.artist),
            duration=t.duration_fmt,
            url=t.permalink,
            genre=genre_part,
            stats=" · ".join(stats),
        )

    def _format_detail(self, t: TrackInfo) -> str:
        parts = [t.duration_fmt]
        if t.genre:
            parts.append(utils.escape_html(t.genre))
        if t.plays:
            parts.append(f"▶ {_compact(t.plays)}")
        if t.likes:
            parts.append(f"♥ {_compact(t.likes)}")
        info = " | ".join(parts)
        return (
            f"<emoji document_id=6007938409857815902>🎧</emoji>"
            f" <b>{utils.escape_html(t.artist)} — {utils.escape_html(t.title)}</b>\n"
            f"<emoji document_id=5776213190387961618>🕓</emoji> {info}\n"
            f"<emoji document_id=5877465816030515018>🔗</emoji>"
            f" <b><a href='{t.permalink}'>SoundCloud</a></b>"
        )

    @_catch_errors
    @_require_token
    @loader.command(
        ru_doc="— Показать карточку текущего трека",
        en_doc="— Show current track card",
    )
    async def scnow(self, message: Message):
        track = await self._current()
        if not track:
            return await utils.answer(message, self.strings("nothing"))

        text = self._format_message(track)

        if not (self.config["show_banner"] and track.cover_url):
            return await utils.answer(message, text)

        msg = await utils.answer(message, text + self.strings("wait_card"))

        cover = await self._load_cover(track.cover_url)
        if not cover:
            return await utils.answer(msg, text)

        font_data = await self._load_font()
        factory = CardFactory(_Fonts(font_data))

        render = (
            factory.square
            if self.config["banner_type"] == "square"
            else factory.horizontal
        )
        card = await utils.run_sync(render, track, cover)
        await utils.answer(msg, text, file=card)

    @_catch_errors
    @_require_token
    @loader.command(
        ru_doc="— Скачать текущий трек",
        en_doc="— Download current track",
    )
    async def scnowt(self, message: Message):
        track = await self._current()
        if not track:
            return await utils.answer(message, self.strings("nothing"))

        text = self._format_detail(track)
        msg = await utils.answer(message, text + self.strings("wait_dl"))

        audio = await self._download(track.permalink)
        if not audio:
            return await utils.answer(msg, text + self.strings("dl_fail"))

        buf = io.BytesIO(audio)
        buf.name = f"{track.artist} - {track.title}.mp3"
        await utils.answer(msg, text, file=buf)

    @_catch_errors
    @_require_token
    @loader.command(
        ru_doc="— История прослушивания",
        en_doc="— Listening history",
    )
    async def schistory(self, message: Message):
        tracks = await self._recent(self.config["history_count"])
        if not tracks:
            return await utils.answer(message, self.strings("nothing"))

        text = (
            "<emoji document_id=5776213190387961618>📜</emoji>"
            " <b>История прослушивания:</b>\n\n"
        )
        for i, t in enumerate(tracks, 1):
            parts = [t.duration_fmt]
            if t.genre:
                parts.append(utils.escape_html(t.genre))
            if t.plays:
                parts.append(f"▶ {_compact(t.plays)}")
            meta = " | ".join(parts)
            text += (
                f"{i}. <b>{utils.escape_html(t.artist)} —"
                f" {utils.escape_html(t.title)}</b>\n"
                f"   <emoji document_id=5776213190387961618>🕓</emoji>"
                f" {meta} | <a href='{t.permalink}'>Link</a>\n\n"
            )

        if not self.config["show_banner"]:
            return await utils.answer(message, text)

        msg = await utils.answer(message, text + self.strings("wait_card"))
        try:
            font_data = await self._load_font()

            def _render():
                factory = CardFactory(_Fonts(font_data))

                def fetcher(u):
                    return requests.get(u, timeout=10).content

                return factory.history(tracks, fetcher)

            card = await utils.run_sync(_render)
            await utils.answer(msg, text, file=card)
        except Exception:
            await utils.answer(msg, text)
