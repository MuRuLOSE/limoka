#             █ █ ▀ █▄▀ ▄▀█ █▀█ ▀
#             █▀█ █ █ █ █▀█ █▀▄ █
#              © Copyright 2022
#
#          https://t.me/hikariatama
#
# 🔒 Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html
#
# You CANNOT edit, distribute or redistribute this file without direct permission from the author.
#
# ORIGINAL MODULE: https://raw.githubusercontent.com/hikariatama/ftg/master/spotify.py

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
# requires: telethon spotipy pillow requests yt-dlp

import asyncio
import contextlib
import functools
import io
import logging
import re
import textwrap
import time
import traceback
import os
from types import FunctionType

import requests
import spotipy
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
from telethon.errors import FloodWaitError
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.types import Message

from .. import loader, utils

logger = logging.getLogger(__name__)
logging.getLogger("spotipy").setLevel(logging.CRITICAL)

class Banners:
    def __init__(
        self,
        title: str,
        artists: list,
        duration: int,
        progress: int,
        track_cover: bytes,
        font
    ):
        self.title = title
        self.artists = ", ".join(artists) if isinstance(artists, list) else artists
        self.duration = duration
        self.progress = progress
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
        bg = bg.filter(ImageFilter.GaussianBlur(radius=40))
        bg = ImageEnhance.Brightness(bg).enhance(0.4) 
        return bg

    def _draw_progress_bar(self, draw, x, y, w, h, progress_pct, color="white", bg_color="#5e5e5e"):
        draw.rounded_rectangle((x, y, x + w, y + h), radius=h/2, fill=bg_color)
        
        fill_w = int(w * progress_pct)
        if fill_w > 0:
            draw.rounded_rectangle((x, y, x + fill_w, y + h), radius=h/2, fill=color)

        dot_radius = h * 1.2
        dot_x = x + fill_w
        dot_y = y + (h / 2)
        
        draw.ellipse(
            (dot_x - dot_radius, dot_y - dot_radius, dot_x + dot_radius, dot_y + dot_radius),
            fill=color
        )

    def horizontal(self):
        W, H = 1500, 600
        padding = 60
        cover_size = 480
        
        font_bytes = requests.get(self.font_url).content
        title_font = self._get_font(55, font_bytes)
        artist_font = self._get_font(45, font_bytes)
        time_font = self._get_font(25, font_bytes)

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

        cur_time = f"{(self.progress//1000//60):02}:{(self.progress//1000%60):02}"
        dur_time = f"{(self.duration//1000//60):02}:{(self.duration//1000%60):02}"
        
        cur_w = time_font.getlength(cur_time)
        dur_w = time_font.getlength(dur_time)
        
        bar_y = 480
        bar_h = 8
        gap = 25
        
        draw.text((text_x, bar_y - 12), cur_time, font=time_font, fill="white")
        
        bar_start_x = text_x + cur_w + gap
        bar_end_x = text_x + text_width_limit - dur_w - gap
        bar_w = bar_end_x - bar_start_x
        
        prog_pct = self.progress / self.duration if self.duration > 0 else 0
        self._draw_progress_bar(draw, bar_start_x, bar_y, bar_w, bar_h, prog_pct)
        
        draw.text((bar_end_x + gap, bar_y - 12), dur_time, font=time_font, fill="white")

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
        time_font = self._get_font(35, font_bytes)

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
        bar_h = 8
        bar_w = W - (padding * 2)
        prog_pct = self.progress / self.duration if self.duration > 0 else 0
        
        self._draw_progress_bar(draw, padding, bar_y, bar_w, bar_h, prog_pct, color="white", bg_color="#5e5e5e")

        cur_time = f"{(self.progress//1000//60):02}:{(self.progress//1000%60):02}"
        dur_time = f"{(self.duration//1000//60):02}:{(self.duration//1000%60):02}"
        
        draw.text((padding, bar_y + 40), cur_time, font=time_font, fill="#B3B3B3")
        
        dur_w = time_font.getlength(dur_time)
        draw.text((W - padding - dur_w, bar_y + 40), dur_time, font=time_font, fill="#B3B3B3")

        by = io.BytesIO()
        img.save(by, format="PNG")
        by.seek(0)
        by.name = "banner.png"
        return by

@loader.tds
class SpotifyMod(loader.Module):
    """Card with the currently playing track on Spotify."""

    strings = {
        "name": "SpotifyMod",
        "need_auth": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>Please execute"
            " </b><code>.sauth</code><b> before performing this action.</b>"
        ),
        "on-repeat": (
            "<emoji document_id=5258420634785947640>🔄</emoji> <b>Set on-repeat.</b>"
        ),
        "off-repeat": (
            "<emoji document_id=5260687119092817530>🔄</emoji> <b>Stopped track"
            " repeat.</b>"
        ),
        "skipped": (
            "<emoji document_id=6037622221625626773>➡️</emoji> <b>Skipped track.</b>"
        ),
        "playing": "<emoji document_id=5773626993010546707>▶️</emoji> <b>Playing...</b>",
        "back": (
            "<emoji document_id=6039539366177541657>⬅️</emoji> <b>Switched to previous"
            " track</b>"
        ),
        "paused": "<emoji document_id=5774077015388852135>❌</emoji> <b>Pause</b>",
        "restarted": (
            "<emoji document_id=5843596438373667352>✅️</emoji> <b>Playing track"
            " from the"
            " beginning</b>"
        ),
        "liked": (
            "<emoji document_id=5258179403652801593>❤️</emoji> <b>Liked current"
            " playback</b>"
        ),
        "unlike": (
            "<emoji document_id=5774077015388852135>❌</emoji>"
            " <b>Unliked current playback</b>"
        ),
        "err": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>An error occurred."
            "</b>\n<code>{}</code>"
        ),
        "already_authed": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>Already authorized</b>"
        ),
        "authed": (
            "<emoji document_id=5776375003280838798>✅</emoji> <b>Authentication"
            " successful</b>"
        ),
        "deauth": (
            "<emoji document_id=5877341274863832725>🚪</emoji> <b>Successfully logged out"
            " of account</b>"
        ),
        "auth": (
            '<emoji document_id=5778168620278354602>🔗</emoji> <a href="{}">Follow this'
            " link</a>, allow access, then enter <code>.scode https://...</code> with"
            " the link you received."
        ),
        "no_music": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>No music is playing!</b>"
        ),
        "dl_err": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>Failed to download"
            " track.</b>"
        ),
        "volume_changed": (
            "<emoji document_id=5890997763331591703>🔊</emoji>"
            " <b>Volume changed to {}%.</b>"
        ),
        "volume_invalid": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>Volume level must be"
            " a number between 0 and 100.</b>"
        ),
        "volume_err": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>An error occurred while"
            " changing volume.</b>"
        ),
        "no_volume_arg": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>Please specify a"
            " volume level between 0 and 100.</b>"
        ),
        "searching_tracks": (
            "<emoji document_id=5841359499146825803>🕔</emoji> <b>Searching for tracks"
            " matching {}...</b>"
        ),
        "no_search_query": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>Please specify a"
            " search query.</b>"
        ),
        "no_tracks_found": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>No tracks found for"
            " {}.</b>"
        ),
        "search_results": (
            "<emoji document_id=5776375003280838798>✅</emoji> <b>Search results for"
            " {}:</b>\n\n{}"
        ),
        "downloading_search_track": (
            "<emoji document_id=5841359499146825803>🕔</emoji> <b>Downloading {}...</b>"
        ),
        "download_success": (
            "<emoji document_id=5776375003280838798>✅</emoji> <b>Successfully downloaded {} - {}</b>"
        ),
        "invalid_track_number": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>Invalid track number."
            " Please search first or provide a valid number from the list.</b>"
        ),
        "device_list": (
            "<emoji document_id=5956561916573782596>📄</emoji> <b>Available devices:</b>\n{}"
        ),
        "no_devices_found": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>No devices found.</b>"
        ),
        "device_changed": (
            "<emoji document_id=5776375003280838798>✅</emoji> <b>Playback transferred to"
            " {}.</b>"
        ),
        "invalid_device_id": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>Invalid device ID."
            " Use</b> <code>.sdevice</code> <b>to see available devices.</b>"
        ),
        "search_results_cleared": "<emoji document_id=5776375003280838798>✅</emoji> <b>Search results cleared</b>",
        "autobio": (
            "<emoji document_id=6319076999105087378>🎧</emoji> <b>Spotify autobio {}</b>"
        ),
        "no_ytdlp": "<emoji document_id=5778527486270770928>❌</emoji> <b>yt-dlp not found... Check config or install yt-dlp (<code>{}terminal pip install yt-dlp</code>)</b>",
        "snowt_failed": "\n\n<emoji document_id=5778527486270770928>❌</emoji> <b>Download failed</b>",
        "uploading_banner": "\n\n<emoji document_id=5841359499146825803>🕔</emoji> <i>Uploading banner...</i>",
        "downloading_track": "\n\n<emoji document_id=5841359499146825803>🕔</emoji> <i>Downloading track...</i>",
        "no_playlists": "<emoji document_id=5778527486270770928>❌</emoji> <b>No playlists found.</b>",
        "playlists_list": "<emoji document_id=5956561916573782596>📄</emoji> <b>Your playlists:</b>\n\n{}",
        "added_to_playlist": "<emoji document_id=5776375003280838798>✅</emoji> <b>Added {} to {}</b>",
        "removed_from_playlist": "<emoji document_id=5776375003280838798>✅</emoji> <b>Removed {} from {}</b>",
        "invalid_playlist_index": "<emoji document_id=5778527486270770928>❌</emoji> <b>Invalid playlist number.</b>",
        "no_cached_playlists": "<emoji document_id=5778527486270770928>❌</emoji> <b>Use .splaylists first.</b>",
        "playlist_created": "<emoji document_id=5776375003280838798>✅</emoji> <b>Playlist {} created.</b>",
        "playlist_deleted": "<emoji document_id=5776375003280838798>✅</emoji> <b>Playlist {} deleted.</b>",
        "no_playlist_name": "<emoji document_id=5778527486270770928>❌</emoji> <b>Please specify a playlist name.</b>",
    }

    strings_ru = {
        "_cls_doc": "Карточка с играющим треком в Spotify.",
        "need_auth": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>Выполни"
            " </b><code>.sauth</code><b> перед выполнением этого действия.</b>"
        ),
        "err": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>Произошла ошибка."
            "</b>\n<code>{}</code>"
        ),
        "on-repeat": (
            "<emoji document_id=5258420634785947640>🔄</emoji> <b>Включен повтор трека.</b>"
        ),
        "off-repeat": (
            "<emoji document_id=5260687119092817530>🔄</emoji> <b>Повтор трека отключён.</b>"
        ),
        "skipped": (
            "<emoji document_id=6037622221625626773>➡️</emoji> <b>Трек пропущен.</b>"
        ),
        "playing": "<emoji document_id=5773626993010546707>▶️</emoji> <b>Играет...</b>",
        "back": (
            "<emoji document_id=6039539366177541657>⬅️</emoji> <b>Переключено на предыдущий трек</b>"
        ),
        "paused": "<emoji document_id=5774077015388852135>❌</emoji> <b>Пауза</b>",
        "restarted": (
            "<emoji document_id=5843596438373667352>✅️</emoji> <b>Воспроизведение трека с начала...</b>"
        ),
        "liked": (
            "<emoji document_id=5258179403652801593>❤️</emoji> <b>Текущий трек добавлен в избранное</b>"
        ),
        "unlike": (
            "<emoji document_id=5774077015388852135>❌</emoji> <b>Убрал лайк с текущего трека</b>"
        ),
        "already_authed": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>Уже авторизован</b>"
        ),
        "authed": (
            "<emoji document_id=5776375003280838798>✅</emoji> <b>Успешная аутентификация</b>"
        ),
        "deauth": (
            "<emoji document_id=5877341274863832725>🚪</emoji> <b>Успешный выход из аккаунта</b>"
        ),
        "auth": (
            '<emoji document_id=5778168620278354602>🔗</emoji> <a href="{}">Пройдите по этой ссылке</a>, разрешите вход, затем введите <code>.scode https://...</code> с ссылкой которую вы получили.'
        ),
        "no_music": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>Музыка не играет!</b>"
        ),
        "dl_err": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>Не удалось скачать трек.</b>"
        ),
        "volume_changed": (
            "<emoji document_id=5890997763331591703>🔊</emoji>"
            " <b>Громкость изменена на {}%.</b>"
        ),
        "volume_invalid": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>Уровень громкости должен"
            " быть числом от 0 до 100.</b>"
        ),
        "volume_err": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>Произошла ошибка при"
            " изменении громкости.</b>"
        ),
        "no_volume_arg": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>Пожалуйста, укажите"
            " уровень громкости от 0 до 100.</b>"
        ),
        "searching_tracks": (
            "<emoji document_id=5841359499146825803>🕔</emoji> <b>Идет поиск треков"
            " по запросу {}...</b>"
        ),
        "no_search_query": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>Пожалуйста, укажите"
            " поисковый запрос.</b>"
        ),
        "no_tracks_found": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>По запросу '{}'"
            " ничего не найдено.</b>"
        ),
        "search_results": (
            "<emoji document_id=5776375003280838798>✅</emoji> <b>Результаты поиска"
            " по запросу {}:</b>\n\n{}"
        ),
        "downloading_search_track": (
            "<emoji document_id=5841359499146825803>🕔</emoji> <b>Скачиваю {}...</b>"
        ),
        "download_success": (
            "<emoji document_id=5776375003280838798>✅</emoji> <b>Трек {} - {} успешно скачан.</b>"
        ),
        "invalid_track_number": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>Некорректный номер трека."
            " Сначала выполните поиск или укажите правильный номер из списка.</b>"
        ),
        "device_list": (
            "<emoji document_id=5956561916573782596>📄</emoji> <b>Доступные устройства:</b>\n{}"
        ),
        "no_devices_found": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>Устройства не найдены.</b>"
        ),
        "device_changed": (
            "<emoji document_id=5776375003280838798>✅</emoji> <b>Воспроизведение переключено на"
            " {}.</b>"
        ),
        "invalid_device_id": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>Некорректный ID устройства."
            " Используйте</b> <code>.sdevice</code> <b>, чтобы увидеть доступные устройства.</b>"
        ),
        "search_results_cleared": "<emoji document_id=5776375003280838798>✅</emoji> <b>Результаты поиска очищены</b>",
        "autobio": (
            "<emoji document_id=6319076999105087378>🎧</emoji> <b>Обновление био"
            " включено {}</b>"
        ),
        "no_ytdlp": "<emoji document_id=5778527486270770928>❌</emoji> <b>yt-dlp не найден... Проверьте конфиг или установите yt-dlp (<code>{}terminal pip install yt-dlp</code>)</b>",
        "snowt_failed": "\n\n<emoji document_id=5778527486270770928>❌</emoji> <b>Ошибка скачивания.</b>",
        "uploading_banner": "\n\n<emoji document_id=5841359499146825803>🕔</emoji> <i>Загрузка баннера...</i>",
        "downloading_track": "\n\n<emoji document_id=5841359499146825803>🕔</emoji> <i>Скачивание трека...</i>",
        "no_playlists": "<emoji document_id=5778527486270770928>❌</emoji> <b>Плейлисты не найдены.</b>",
        "playlists_list": "<emoji document_id=5956561916573782596>📄</emoji> <b>Ваши плейлисты:</b>\n\n{}",
        "added_to_playlist": "<emoji document_id=5776375003280838798>✅</emoji> <b>Трек {} добавлен в {}</b>",
        "removed_from_playlist": "<emoji document_id=5776375003280838798>✅</emoji> <b>Трек {} удален из {}</b>",
        "invalid_playlist_index": "<emoji document_id=5778527486270770928>❌</emoji> <b>Неверный номер плейлиста.</b>",
        "no_cached_playlists": "<emoji document_id=5778527486270770928>❌</emoji> <b>Сначала используйте .splaylists.</b>",
        "playlist_created": "<emoji document_id=5776375003280838798>✅</emoji> <b>Плейлист {} создан.</b>",
        "playlist_deleted": "<emoji document_id=5776375003280838798>✅</emoji> <b>Плейлист {} удален.</b>",
        "no_playlist_name": "<emoji document_id=5778527486270770928>❌</emoji> <b>Пожалуйста, укажите название плейлиста.</b>",
    }
    strings_jp = {
        "_cls_doc": "Spotify からのメッセージ",
        "need_auth": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>この操作を行う前に "
            "</b><code>.sauth</code><b> を実行してください。</b>"
        ),
        "on-repeat": (
            "<emoji document_id=5258420634785947640>🔄</emoji> <b>リピート再生を設定しました。</b>"
        ),
        "off-repeat": (
            "<emoji document_id=5260687119092817530>🔄</emoji> <b>リピート再生を解除しました。</b>"
        ),
        "skipped": (
            "<emoji document_id=6037622221625626773>➡️</emoji> <b>スキップしました。</b>"
        ),
        "playing": "<emoji document_id=5773626993010546707>▶️</emoji> <b>再生中...</b>",
        "back": (
            "<emoji document_id=6039539366177541657>⬅️</emoji> <b>前のトラックに戻りました。</b>"
        ),
        "paused": "<emoji document_id=5774077015388852135>❌</emoji> <b>一時停止</b>",
        "restarted": (
            "<emoji document_id=5843596438373667352>✅️</emoji> <b>最初から再生します。</b>"
        ),
        "liked": (
            "<emoji document_id=5258179403652801593>❤️</emoji> <b>お気に入りに追加しました。</b>"
        ),
        "unlike": (
            "<emoji document_id=5774077015388852135>❌</emoji>"
            " <b>お気に入りから削除しました。</b>"
        ),
        "err": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>エラーが発生しました。"
            "</b>\n<code>{}</code>"
        ),
        "already_authed": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>既に認証されています。</b>"
        ),
        "authed": (
            "<emoji document_id=5776375003280838798>✅</emoji> <b>認証に成功しました。</b>"
        ),
        "deauth": (
            "<emoji document_id=5877341274863832725>🚪</emoji> <b>ログアウトしました。</b>"
        ),
        "auth": (
            '<emoji document_id=5778168620278354602>🔗</emoji> <a href="{}">リンクをクリック</a>してアクセスを許可し、取得したURLを使って <code>.scode https://...</code> を入力してください。'
        ),
        "no_music": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>音楽は再生されていません！</b>"
        ),
        "dl_err": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>トラックのダウンロードに失敗しました。</b>"
        ),
        "volume_changed": (
            "<emoji document_id=5890997763331591703>🔊</emoji>"
            " <b>音量を {}% に変更しました。</b>"
        ),
        "volume_invalid": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>音量は0から100の数字で指定してください。</b>"
        ),
        "volume_err": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>音量の変更中にエラーが発生しました。</b>"
        ),
        "no_volume_arg": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>0から100の間で音量を指定してください。</b>"
        ),
        "searching_tracks": (
            "<emoji document_id=5841359499146825803>🕔</emoji> <b>{} を検索中...</b>"
        ),
        "no_search_query": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>検索キーワードを指定してください。</b>"
        ),
        "no_tracks_found": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>{} は見つかりませんでした。</b>"
        ),
        "search_results": (
            "<emoji document_id=5776375003280838798>✅</emoji> <b>{} の検索結果:</b>\n\n{}"
        ),
        "downloading_search_track": (
            "<emoji document_id=5841359499146825803>🕔</emoji> <b>{} をダウンロード中...</b>"
        ),
        "download_success": (
            "<emoji document_id=5776375003280838798>✅</emoji> <b>{} - {} のダウンロードに成功しました。</b>"
        ),
        "invalid_track_number": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>トラック番号が無効です。"
            " 先に検索するか、リストから有効な番号を指定してください。</b>"
        ),
        "device_list": (
            "<emoji document_id=5956561916573782596>📄</emoji> <b>利用可能なデバイス:</b>\n{}"
        ),
        "no_devices_found": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>デバイスが見つかりません。</b>"
        ),
        "device_changed": (
            "<emoji document_id=5776375003280838798>✅</emoji> <b>再生デバイスを"
            " {} に切り替えました。</b>"
        ),
        "invalid_device_id": (
            "<emoji document_id=5778527486270770928>❌</emoji> <b>デバイスIDが無効です。"
            " </b><code>.sdevice</code> <b>で利用可能なデバイスを確認してください。</b>"
        ),
        "search_results_cleared": "<emoji document_id=5776375003280838798>✅</emoji> <b>検索結果をクリアしました。</b>",
        "autobio": (
            "<emoji document_id=6319076999105087378>🎧</emoji> <b>Spotify AutoBio: {}</b>"
        ),
        "no_ytdlp": "<emoji document_id=5778527486270770928>❌</emoji> <b>yt-dlpが見つかりません... 設定を確認するか、インストールしてください (<code>{}terminal pip install yt-dlp</code>)</b>",
        "snowt_failed": "\n\n<emoji document_id=5778527486270770928>❌</emoji> <b>ダウンロードに失敗しました。</b>",
        "uploading_banner": "\n\n<emoji document_id=5841359499146825803>🕔</emoji> <i>バナーをアップロード中...</i>",
        "downloading_track": "\n\n<emoji document_id=5841359499146825803>🕔</emoji> <i>トラックをダウンロード中...</i>",
        "no_playlists": "<emoji document_id=5778527486270770928>❌</emoji> <b>プレイリストが見つかりません。</b>",
        "playlists_list": "<emoji document_id=5956561916573782596>📄</emoji> <b>あなたのプレイリスト:</b>\n\n{}",
        "added_to_playlist": "<emoji document_id=5776375003280838798>✅</emoji> <b>{} を {} に追加しました。</b>",
        "removed_from_playlist": "<emoji document_id=5776375003280838798>✅</emoji> <b>{} を {} から削除しました。</b>",
        "invalid_playlist_index": "<emoji document_id=5778527486270770928>❌</emoji> <b>プレイリスト番号が無効です。</b>",
        "no_cached_playlists": "<emoji document_id=5778527486270770928>❌</emoji> <b>先に .splaylists を使用してください。</b>",
        "playlist_created": "<emoji document_id=5776375003280838798>✅</emoji> <b>プレイリスト {} を作成しました。</b>",
        "playlist_deleted": "<emoji document_id=5776375003280838798>✅</emoji> <b>プレイリスト {} を削除しました。</b>",
        "no_playlist_name": "<emoji document_id=5778527486270770928>❌</emoji> <b>プレイリスト名を指定してください。</b>",
    }

    def __init__(self):
        self._client_id = "e0708753ab60499c89ce263de9b4f57a"
        self._client_secret = "80c927166c664ee98a43a2c0e2981b4a"
        self.scope = (
            "user-read-playback-state playlist-read-private playlist-read-collaborative"
            " user-modify-playback-state user-library-modify"
            " playlist-modify-public playlist-modify-private"
        )
        self.sp_auth = spotipy.oauth2.SpotifyOAuth(
            client_id=self._client_id,
            client_secret=self._client_secret,
            redirect_uri="https://thefsch.github.io/spotify/",
            scope=self.scope,
        )
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "show_banner",
                True,
                "Show banner with track info",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "custom_text",
                (
                    "<emoji document_id=6007938409857815902>🎧</emoji> <b>Now playing:</b> {track} — {artists}\n"
                    "<emoji document_id=5877465816030515018>🔗</emoji> <b><a href='{songlink}'>song.link</a></b>"
                ),
                """Custom text, supports {track}, {artists}, {album}, {playlist}, {playlist_owner}, {spotify_url}, {songlink}, {progress}, {duration}, {device} placeholders""",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "font",
                "https://raw.githubusercontent.com/kamekuro/assets/master/fonts/Onest-Bold.ttf",
                "Custom font. Specify URL to .ttf file",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "auto_bio_template",
                "🎧 {}",
                lambda: "Template for Spotify AutoBio",
            ),
            loader.ConfigValue(
                "ytdlp_path",
                "",
                "Path to ytdlp binary",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "banner_version",
                "horizontal",
                lambda: "Banner version",
                validator=loader.validators.Choice(["horizontal", "vertical"]),
            ),
        )

    async def client_ready(self, client, db):
        self.font_ready = asyncio.Event()

        self._premium = getattr(await client.get_me(), "premium", False)
        try:
            self.sp = spotipy.Spotify(auth=self.get("acs_tkn")["access_token"])
        except Exception:
            self.set("acs_tkn", None)
            self.sp = None

        if self.get("autobio", False):
            self.autobio.start()

    def tokenized(func) -> FunctionType:
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            if not args[0].get("acs_tkn", False) or not args[0].sp:
                await utils.answer(args[1], args[0].strings("need_auth"))
                return

            return await func(*args, **kwargs)

        wrapped.__doc__ = func.__doc__
        wrapped.__module__ = func.__module__

        return wrapped

    def error_handler(func) -> FunctionType:
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception:
                logger.exception(traceback.format_exc())
                with contextlib.suppress(Exception):
                    await utils.answer(
                        args[1],
                        args[0].strings("err").format(traceback.format_exc()),
                    )

        wrapped.__doc__ = func.__doc__
        wrapped.__module__ = func.__module__

        return wrapped


    @loader.loop(interval=90)
    async def autobio(self):
        try:
            current_playback = self.sp.current_playback()
            track = current_playback["item"]["name"]
            track = re.sub(r"([(].*?[)])", "", track).strip()
        except Exception:
            return

        bio = self.config["auto_bio_template"].format(f"{track}")

        try:
            await self._client(
                UpdateProfileRequest(about=bio[: 140 if self._premium else 70])
            )
        except FloodWaitError as e:
            logger.info(f"Sleeping {max(e.seconds, 60)} bc of floodwait")
            await asyncio.sleep(max(e.seconds, 60))
            return
    
    async def _download_track(self, message, query: str, caption: str = ""):
        dl_dir = os.path.join(os.getcwd(), "spotifymod")
        if not os.path.exists(dl_dir):
            os.makedirs(dl_dir, exist_ok=True)
        
        for f in os.listdir(dl_dir):
            try:
                os.remove(os.path.join(dl_dir, f))
            except:
                pass

        try:
            squery = query.replace('"', '').replace("'", "")

            cmd = (
                f'{self.config["ytdlp_path"]} -x --audio-format mp3 --add-metadata '
                f'-o "{dl_dir}/%(title)s [%(id)s].%(ext)s" '
                f'"ytsearch1:{squery}"'
            )

            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()

            files = [f for f in os.listdir(dl_dir) if f.endswith(".mp3")]
            
            if files:
                target_file = os.path.join(dl_dir, files[0])
                await utils.answer(message, caption, file=target_file)
            else:
                await utils.answer(message, self.strings("snowt_failed"))

        except Exception as e:
            logger.error(e)
            await utils.answer(message, self.strings("dl_err"))
        
        finally:
            if os.path.exists(dl_dir):
                for f in os.listdir(dl_dir):
                    try:
                        os.remove(os.path.join(dl_dir, f))
                    except:
                        pass


    @error_handler
    @tokenized
    @loader.command(
        ru_doc="- ➕ Добавить текущий трек в плейлист (используйте номер из .splaylists)"
    )
    async def splaylistadd(self, message: Message):
        """- ➕ Add current track to playlist (use number from .splaylists)"""
        args = utils.get_args_raw(message)
        if not args or not args.isdigit():
            await utils.answer(message, self.strings("invalid_playlist_index"))
            return
        
        index = int(args) - 1
        playlists = self.get("last_playlists", [])
        
        if not playlists:
            await utils.answer(message, self.strings("no_cached_playlists"))
            return

        if index < 0 or index >= len(playlists):
            await utils.answer(message, self.strings("invalid_playlist_index"))
            return
            
        current = self.sp.current_playback()
        if not current or not current.get("item"):
            await utils.answer(message, self.strings("no_music"))
            return
            
        track_uri = current["item"]["uri"]
        track_name = current["item"]["name"]
        artists = ", ".join([a["name"] for a in current["item"]["artists"]])
        full_track_name = f"{artists} - {track_name}"
        
        playlist_id = playlists[index]["id"]
        playlist_name = playlists[index]["name"]
        
        try:
            self.sp.playlist_add_items(playlist_id, [track_uri])
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 403 and "Insufficient client scope" in str(e):
                await utils.answer(message, self.strings("need_auth"))
                return
            raise e
        
        await utils.answer(message, self.strings("added_to_playlist").format(utils.escape_html(full_track_name), utils.escape_html(playlist_name)))

    @error_handler
    @tokenized
    @loader.command(
        ru_doc="- ➖ Удалить текущий трек из плейлиста (используйте номер из .splaylists)"
    )
    async def splaylistrem(self, message: Message):
        """- ➖ Remove current track from playlist (use number from .splaylists)"""
        args = utils.get_args_raw(message)
        if not args or not args.isdigit():
            await utils.answer(message, self.strings("invalid_playlist_index"))
            return
        
        index = int(args) - 1
        playlists = self.get("last_playlists", [])
        
        if not playlists:
            await utils.answer(message, self.strings("no_cached_playlists"))
            return

        if index < 0 or index >= len(playlists):
            await utils.answer(message, self.strings("invalid_playlist_index"))
            return
            
        current = self.sp.current_playback()
        if not current or not current.get("item"):
            await utils.answer(message, self.strings("no_music"))
            return
            
        track_uri = current["item"]["uri"]
        track_name = current["item"]["name"]
        artists = ", ".join([a["name"] for a in current["item"]["artists"]])
        full_track_name = f"{artists} - {track_name}"
        
        playlist_id = playlists[index]["id"]
        playlist_name = playlists[index]["name"]
        
        try:
            self.sp.playlist_remove_all_occurrences_of_items(playlist_id, [track_uri])
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 403 and "Insufficient client scope" in str(e):
                await utils.answer(message, self.strings("need_auth"))
                return
            raise e
        
        await utils.answer(message, self.strings("removed_from_playlist").format(utils.escape_html(full_track_name), utils.escape_html(playlist_name)))

    @error_handler
    @tokenized
    @loader.command(
        ru_doc="- 🆕 Создать новый плейлист"
    )
    async def splaylistcreate(self, message: Message):
        """- 🆕 Create a new playlist"""
        name = utils.get_args_raw(message)
        if not name:
            await utils.answer(message, self.strings("no_playlist_name"))
            return
        
        user_id = self.sp.me()["id"]
        self.sp.user_playlist_create(user_id, name)
        await utils.answer(message, self.strings("playlist_created").format(utils.escape_html(name)))

    @error_handler
    @tokenized
    @loader.command(
        ru_doc="- 🗑 Удалить плейлист (используйте номер из .splaylists)"
    )
    async def splaylistdelete(self, message: Message):
        """- 🗑 Delete playlist (use number from .splaylists)"""
        args = utils.get_args_raw(message)
        if not args or not args.isdigit():
            await utils.answer(message, self.strings("invalid_playlist_index"))
            return
        
        index = int(args) - 1
        playlists = self.get("last_playlists", [])
        
        if not playlists:
            await utils.answer(message, self.strings("no_cached_playlists"))
            return

        if index < 0 or index >= len(playlists):
            await utils.answer(message, self.strings("invalid_playlist_index"))
            return
            
        playlist_id = playlists[index]["id"]
        playlist_name = playlists[index]["name"]
        
        self.sp.current_user_unfollow_playlist(playlist_id)
        await utils.answer(message, self.strings("playlist_deleted").format(utils.escape_html(playlist_name)))

    @error_handler
    @tokenized
    @loader.command(
        ru_doc="- 📃 Получить все плейлисты"
    )
    async def splaylists(self, message: Message):
        """- 📃 Get all playlists"""
        user_id = self.sp.me()["id"]
        playlists = self.sp.current_user_playlists()
        
        editable_playlists = []
        for playlist in playlists["items"]:
            if playlist["owner"]["id"] == user_id or playlist["collaborative"]:
                editable_playlists.append(playlist)
        
        self.set("last_playlists", editable_playlists)

        playlist_list_text = ""
        for i, playlist in enumerate(editable_playlists):
            name = utils.escape_html(playlist["name"])
            url = playlist["external_urls"]["spotify"]
            count = playlist["tracks"]["total"]
            playlist_list_text += f"<b>{i + 1}.</b> <a href='{url}'>{name}</a> ({count} tracks)\n"

        if not playlist_list_text:
            await utils.answer(message, self.strings("no_playlists"))
        else:
            await utils.answer(message, self.strings("playlists_list").format(playlist_list_text))

    @error_handler
    @tokenized
    @loader.command(
        ru_doc="- ℹ️ Переключить стриминг воспроизведения в био"
    )
    async def sbiocmd(self, message: Message):
        """- ℹ️ Toggle bio playback streaming"""
        current = self.get("autobio", False)
        new = not current
        self.set("autobio", new)
        await utils.answer(
            message,
            self.strings("autobio").format("enabled" if new else "disabled"),
        )

        if new:
            self.autobio.start()
        else:
            self.autobio.stop()

    @error_handler
    @tokenized
    @loader.command(
        ru_doc="- 🔊 Изменить громкость. .svolume <0-100>"
    )
    async def svolume(self, message: Message):
        """- 🔊 Change playback volume. .svolume <0-100>"""
        try:
            args = utils.get_args_raw(message)
            if not args:
                await utils.answer(message, self.strings("no_volume_arg"))
                return

            volume_percent = int(args)
            if 0 <= volume_percent <= 100:
                self.sp.volume(volume_percent)
                await utils.answer(message, self.strings("volume_changed").format(volume_percent))
            else:
                await utils.answer(message, self.strings("volume_invalid"))
        except ValueError:
            await utils.answer(message, self.strings("volume_invalid"))
        except Exception:
            await utils.answer(message, self.strings("volume_err"))

    @error_handler
    @tokenized
    @loader.command(
        ru_doc=(
            "- 🎵 Выбрать устройство для воспроизведения. Например: .sdevice <ID устройства>\n"
            "- 📝 Показать список устройств: .sdevice"
        )
    )
    async def sdevicecmd(self, message: Message):
        """- 🎵 Set preferred playback device. Usage: .sdevice <device_id> or .sdevice to list devices"""
        args = utils.get_args_raw(message)
        devices = self.sp.devices()["devices"]

        if not args:
            if not devices:
                await utils.answer(message, self.strings("no_devices_found"))
                return

            device_list_text = ""
            for i, device in enumerate(devices):
                is_active = "(active)" if device["is_active"] else ""
                device_list_text += (
                    f"<b>{i+1}.</b> {device['name']}"
                    f" ({device['type']}) {is_active}\n"
                )

            await utils.answer(message, self.strings("device_list").format(device_list_text.strip()))
            return

        device_id = None
        try:
            device_number = int(args)
            if 0 < device_number <= len(devices):
                device_id = devices[device_number - 1]["id"]
                device_name = devices[device_number - 1]["name"]
            else:
                await utils.answer(message, self.strings("invalid_device_id"))
                return
        except ValueError:
            found_device = next((d for d in devices if d["id"] == args.strip()), None)
            if found_device:
                device_id = found_device["id"]
                device_name = found_device["name"]
            else:
                await utils.answer(message, self.strings("invalid_device_id"))
                return

        self.sp.transfer_playback(device_id=device_id)
        await utils.answer(message, self.strings("device_changed").format(device_name))
            
    @error_handler
    @tokenized
    @loader.command(
        ru_doc="- 💫 Включить повтор трека"
    )
    async def srepeatcmd(self, message: Message):
        """- 💫 Repeat"""
        self.sp.repeat("track")
        await utils.answer(message, self.strings("on-repeat"))

    @error_handler
    @tokenized
    @loader.command(
        ru_doc="- ✋ Остановить повтор"
    )
    async def sderepeatcmd(self, message: Message):
        """- ✋ Stop repeat"""
        self.sp.repeat("context")
        await utils.answer(message, self.strings("off-repeat"))

    @error_handler
    @tokenized
    @loader.command(
        ru_doc="- 👉 Следующий трек"
    )
    async def snextcmd(self, message: Message):
        """- 👉 Next track"""
        self.sp.next_track()
        await utils.answer(message, self.strings("skipped"))

    @error_handler
    @tokenized
    @loader.command(
        ru_doc="- 🤚 Продолжить воспроизведение"
    )
    async def sresumecmd(self, message: Message):
        """- 🤚 Resume"""
        self.sp.start_playback()
        await utils.answer(message, self.strings("playing"))

    @error_handler
    @tokenized
    @loader.command(
        ru_doc="- 🤚 Пауза"
    )
    async def spausecmd(self, message: Message):
        """- 🤚 Pause"""
        self.sp.pause_playback()
        await utils.answer(message, self.strings("paused"))

    @error_handler
    @tokenized
    @loader.command(
        ru_doc="- ⏮ Предыдущий трек"
    )
    async def sbackcmd(self, message: Message):
        """- ⏮ Previous track"""
        self.sp.previous_track()
        await utils.answer(message, self.strings("back"))

    @error_handler
    @tokenized
    @loader.command(
        ru_doc="- ⏪ Перезапустить трек"
    )
    async def sbegincmd(self, message: Message):
        """- ⏪ Restart track"""
        self.sp.seek_track(0)
        await utils.answer(message, self.strings("restarted"))

    @error_handler
    @tokenized
    @loader.command(
        ru_doc="- ❤️ Лайкнуть играющий трек"
    )
    async def slikecmd(self, message: Message):
        """- ❤️ Like current track"""
        cupl = self.sp.current_playback()
        self.sp.current_user_saved_tracks_add([cupl["item"]["id"]])
        await utils.answer(message, self.strings("liked"))
    
    @error_handler
    @tokenized
    @loader.command(
        ru_doc="- 💔 Убрать лайк с играющего трека"
    )
    async def sunlikecmd(self, message: Message):
        """- 💔 Unlike current track"""
        cupl = self.sp.current_playback()
        self.sp.current_user_saved_tracks_delete([cupl["item"]["id"]])
        await utils.answer(message, self.strings("unlike"))

    @error_handler
    @loader.command(
        ru_doc="- Получить ссылку для авторизации"
    )
    async def sauthcmd(self, message: Message):
        """- Get authorization link"""
        if self.get("acs_tkn", False) and not self.sp:
            await utils.answer(message, self.strings("already_authed"))
        else:
            self.sp_auth.get_authorize_url()
            await utils.answer(
                message,
                self.strings("auth").format(self.sp_auth.get_authorize_url()),
            )

    @error_handler
    @loader.command(
        ru_doc="- Вставить код авторизации"
    )
    async def scodecmd(self, message: Message):
        """- Paste authorization code"""
        url = message.message.split(" ")[1]
        code = self.sp_auth.parse_auth_response_url(url)
        self.set("acs_tkn", self.sp_auth.get_access_token(code, True, False))
        self.sp = spotipy.Spotify(auth=self.get("acs_tkn")["access_token"])
        await utils.answer(message, self.strings("authed"))

    @error_handler
    @loader.command(
        ru_doc="- Выйти из аккаунта"
    )
    async def unauthcmd(self, message: Message):
        """- Log out of account"""
        self.set("acs_tkn", None)
        del self.sp
        await utils.answer(message, self.strings("deauth"))

    @error_handler
    @tokenized
    @loader.command(
        ru_doc="- Обновить токен авторизации"
    )
    async def stokrefreshcmd(self, message: Message):
        """- Refresh authorization token"""
        self.set(
            "acs_tkn",
            self.sp_auth.refresh_access_token(self.get("acs_tkn")["refresh_token"]),
        )
        self.set("NextRefresh", time.time() + 45 * 60)
        self.sp = spotipy.Spotify(auth=self.get("acs_tkn")["access_token"])
        await utils.answer(message, self.strings("authed"))

    @error_handler
    @tokenized
    @loader.command(
        ru_doc="- 🎧 Показать карточку играющего трека"
    )
    async def snowcmd(self, message: Message):
        """- 🎧 View current track card."""
        current_playback = self.sp.current_playback()
        if not current_playback or not current_playback.get("is_playing", False):
            await utils.answer(message, self.strings("no_music"))
            return

        track = current_playback["item"]["name"]
        track_id = current_playback["item"]["id"]
        artists = ", ".join([a["name"] for a in current_playback["item"]["artists"]])
        album_name = current_playback["item"]["album"].get("name", "Unknown Album")
        duration_ms = current_playback["item"].get("duration_ms", 0)
        progress_ms = current_playback.get("progress_ms", 0)

        duration = f"{duration_ms//1000//60}:{duration_ms//1000%60:02}"
        progress = f"{progress_ms//1000//60}:{progress_ms//1000%60:02}"

        spotify_url = f"https://open.spotify.com/track/{track_id}"
        songlink = f"https://song.link/s/{track_id}"

        try:
            device_raw = (
                current_playback["device"]["name"]
                + " "
                + current_playback["device"]["type"].lower()
            )
            device = device_raw.replace("computer", "").replace("smartphone", "").strip()
        except Exception:
            device = None

        try:
            playlist_id = current_playback["context"]["uri"].split(":")[-1]
            playlist = self.sp.playlist(playlist_id)
            playlist_name = playlist.get("name", None)
            try:
                playlist_owner = (
                    f'<a href="https://open.spotify.com/user/{playlist["owner"]["id"]}">'
                    f'{playlist["owner"]["display_name"]}</a>'
                )
            except KeyError:
                playlist_owner = playlist.get("owner", {}).get("display_name", "")
        except Exception:
            playlist_name = ""
            playlist_owner = ""

        text = self.config["custom_text"].format(
            track=utils.escape_html(track),
            artists=utils.escape_html(artists),
            album=utils.escape_html(album_name),
            duration=duration,
            progress=progress,
            device=device,
            spotify_url=spotify_url,
            songlink=songlink,
            playlist=utils.escape_html(playlist_name) if playlist_name else "",
            playlist_owner=playlist_owner or "",
        )

        if self.config["show_banner"]:
            cover_url = current_playback["item"]["album"]["images"][0]["url"]

            tmp_msg = await utils.answer(message, text + self.strings("uploading_banner"))

            banners = Banners(
                title=track,
                artists=artists,
                duration=duration_ms,
                progress=progress_ms,
                track_cover=requests.get(cover_url).content,
                font=self.config["font"],
            )
            file = getattr(banners, self.config["banner_version"], banners.horizontal)()
            
            await utils.answer(tmp_msg, text, file=file)
        else:
            await utils.answer(message, text)

    @error_handler
    @tokenized
    @loader.command(
        ru_doc="- 🎧 Скачать играющий трек"
    )
    async def snowtcmd(self, message: Message):
        """- 🎧 Download current track."""
        current_playback = self.sp.current_playback()
        if not current_playback or not current_playback.get("is_playing", False):
            await utils.answer(message, self.strings("no_music"))
            return

        track = current_playback["item"]["name"]
        artists = ", ".join([a["name"] for a in current_playback["item"]["artists"]])
        album_name = current_playback["item"]["album"].get("name", "Unknown Album")
        duration_ms = current_playback["item"].get("duration_ms", 0)
        progress_ms = current_playback.get("progress_ms", 0)

        duration = f"{duration_ms//1000//60}:{duration_ms//1000%60:02}"
        progress = f"{progress_ms//1000//60}:{progress_ms//1000%60:02}"

        spotify_url = f"https://open.spotify.com/track/{current_playback['item']['id']}"
        songlink = f"https://song.link/s/{current_playback['item']['id']}"

        try:
            device_raw = (
                current_playback["device"]["name"]
                + " "
                + current_playback["device"]["type"].lower()
            )
            device = device_raw.replace("computer", "").replace("smartphone", "").strip()
        except Exception:
            device = None

        try:
            playlist_id = current_playback["context"]["uri"].split(":")[-1]
            playlist = self.sp.playlist(playlist_id)
            playlist_name = playlist.get("name", None)
            try:
                playlist_owner = (
                    f'<a href="https://open.spotify.com/user/{playlist["owner"]["id"]}">'
                    f'{playlist["owner"]["display_name"]}</a>'
                )
            except KeyError:
                playlist_owner = playlist.get("owner", {}).get("display_name", "")
        except Exception:
            playlist_name = ""
            playlist_owner = ""

        text = self.config["custom_text"].format(
            track=utils.escape_html(track),
            artists=utils.escape_html(artists),
            album=utils.escape_html(album_name),
            duration=duration,
            progress=progress,
            device=device,
            spotify_url=spotify_url,
            songlink=songlink,
            playlist=utils.escape_html(playlist_name) if playlist_name else "",
            playlist_owner=playlist_owner or "",
        )

        msg = await utils.answer(message, text + self.strings("downloading_track"))
        
        await self._download_track(msg, f"{artists} {track}", caption=text)

    @error_handler
    @tokenized
    @loader.command(
        ru_doc=(
            "- 🔍 Поиск треков. Например: .ssearch Imagine Dragons Believer\n"
            "- 🎧 Скачать трек: .ssearch 1 (где 1 — номер трека из списка)"
        )
    )
    async def ssearchcmd(self, message: Message):
        """🔍 Search for tracks. Usage: .ssearch <query> or .ssearch <number> to download"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings("no_search_query"))
            return

        try:
            track_number = int(args)
            search_results = self.get("last_search_results", [])
            
            if not search_results:
                await utils.answer(message, self.strings("no_tracks_found"))
                return

            if track_number <= 0 or track_number > len(search_results):
                raise ValueError

            msg = await utils.answer(message, self.strings("downloading_track"))
            
            track_info = search_results[track_number - 1]
            track_name = track_info["name"]
            artists = ", ".join([a["name"] for a in track_info["artists"]])
            
            caption_text = self.strings("download_success").format(
                utils.escape_html(track_name), 
                utils.escape_html(artists)
            )
            
            await self._download_track(msg, f"{artists} {track_name}", caption=caption_text)
            return

        except ValueError:
            await utils.answer(message, self.strings("searching_tracks").format(args))

            results = self.sp.search(q=args, limit=5, type="track")

            if not results or not results["tracks"]["items"]:
                await utils.answer(message, self.strings("no_tracks_found").format(args))
                return

            self.set("last_search_results", results["tracks"]["items"])
            
            tracks_list = []
            for i, track in enumerate(results["tracks"]["items"]):
                track_name = track["name"]
                artists = ", ".join([artist["name"] for artist in track["artists"]])
                track_url = track["external_urls"]["spotify"]
                tracks_list.append(
                    "<b>{number}.</b> {track_name} — {artists}\n<a href='{track_url}'>🔗 Spotify</a>".format(
                        number=i + 1,
                        track_name=utils.escape_html(track_name),
                        artists=utils.escape_html(artists),
                        track_url=track_url,
                    )
                )

            text = "\n".join(tracks_list)
            await utils.answer(message, self.strings("search_results").format(args, text))

    
    @loader.command(
        ru_doc="- 🔄 Сброс результатов поиска по трекам"
    )
    async def ssearchresetcmd(self, message: Message):
        """- 🔄 Reset track search results"""
        self.set("last_search_results", [])
        await utils.answer(message, self.strings["search_results_cleared"])

    async def watcher(self, message: Message):
        """Watcher is used to update token"""
        if not self.sp:
            return

        if self.get("NextRefresh", False):
            ttc = self.get("NextRefresh", 0)
            crnt = time.time()
            if ttc < crnt:
                self.set(
                    "acs_tkn",
                    self.sp_auth.refresh_access_token(
                        self.get("acs_tkn")["refresh_token"]
                    ),
                )
                self.set("NextRefresh", time.time() + 45 * 60)
                self.sp = spotipy.Spotify(auth=self.get("acs_tkn")["access_token"])
        else:
            self.set(
                "acs_tkn",
                self.sp_auth.refresh_access_token(self.get("acs_tkn")["refresh_token"]),
            )
            self.set("NextRefresh", time.time() + 45 * 60)
            self.sp = spotipy.Spotify(auth=self.get("acs_tkn")["access_token"])
