__version__ = (2, 0, 1)
#                    region KAMEKURO.
#          █▄▀ ▄▀█ █▀▄▀█ █▀▀ █▄▀ █  █ █▀█ █▀█
#          █ █ █▀█ █ ▀ █ ██▄ █ █ ▀▄▄▀ █▀▄ █▄█ ▄
#                © Copyright 2025
#            ✈ https://t.me/kamekuro
# 🔒 Licensed under CC-BY-NC-ND 4.0 unless otherwise specified.
# 🌐 https://creativecommons.org/licenses/by-nc-nd/4.0
# + attribution
# + non-commercial
# + no-derivatives
# You CANNOT edit, distribute or redistribute this file without direct permission from the author.

#                    region YaMusic
#             ▀▄▀ ▄▀█ █▀▄▀█ █  █ █▀▀ █ █▀▀
#              █  █▀█ █ ▀ █ ▀▄▄▀ ▄▄█ █ █▄▄
# meta banner: https://raw.githubusercontent.com/kamekuro/hikka-mods/main/banners/yamusic.png
# meta pic: https://raw.githubusercontent.com/kamekuro/hikka-mods/main/icons/yamusic.png
# meta developer: @kamekuro_hmods
# packurl: https://raw.githubusercontent.com/kamekuro/hikka-mods/main/langpacks/yamusic.yml
# scope: heroku_only
# scope: heroku_min 1.7.2
# requires: aiohttp asyncio requests pillow==12.0.0 git+https://github.com/MarshalX/yandex-music-api

import aiohttp
import asyncio
import io
import json
import logging
import random
import requests
import string
import textwrap
import typing
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

import telethon
import yandex_music
import yandex_music.exceptions

from .. import loader, utils


logger = logging.getLogger(__name__)


class Banners:
    def __init__(
        self,
        title: str,
        artists: list,
        duration: int,
        progress: int,
        track_cover: bytes,
    ):
        self.title = title
        self.artists = artists
        self.duration = duration
        self.progress = progress
        self.track_cover = track_cover
        self.onest_b = "https://raw.githubusercontent.com/kamekuro/assets/master/fonts/Onest-Bold.ttf"
        self.onest_r = "https://raw.githubusercontent.com/kamekuro/assets/master/fonts/Onest-Regular.ttf"
        self.ysmusic_hb = "https://raw.githubusercontent.com/kamekuro/assets/master/fonts/YSMusic-HeadlineBold.ttf"

    def measure(
        self, text: str, font: ImageFont.FreeTypeFont, draw: ImageDraw.ImageDraw
    ):
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]


    def new(self):
        W, H = 1920, 768
        title_font = ImageFont.truetype(io.BytesIO(requests.get(self.onest_b).content), 80)
        artist_font = ImageFont.truetype(io.BytesIO(requests.get(self.onest_b).content), 55)
        time_font = ImageFont.truetype(io.BytesIO(requests.get(self.onest_b).content), 36)

        track_cov = Image.open(io.BytesIO(self.track_cover)).convert("RGBA")
        banner = (
            track_cov.resize((W, W))
            .crop((0, (W - H) // 2, W, ((W - H) // 2) + H))
            .filter(ImageFilter.GaussianBlur(radius=14))
        )
        banner = ImageEnhance.Brightness(banner).enhance(0.3)
        draw = ImageDraw.Draw(banner)

        track_cov = track_cov.resize((H - 250, H - 250))
        mask = Image.new("L", track_cov.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, track_cov.size[0], track_cov.size[1]), radius=35, fill=255
        )
        track_cov.putalpha(mask)
        track_cov = track_cov.crop(track_cov.getbbox())
        banner.paste(track_cov, (75, 75), mask)

        space = (643, 75, 1870, 593)
        title_lines = textwrap.wrap(self.title, width=23)
        if len(title_lines) > 2:
            title_lines = title_lines[:2]
            title_lines[-1] = title_lines[-1][:-1] + "…"
        artist_lines = textwrap.wrap(", ".join(self.artists), width=23)
        if len(artist_lines) > 1:
            artist_lines = artist_lines[:1]
            artist_lines[-1] = artist_lines[-1][:-1] + "…"
        lines = title_lines + artist_lines
        lines_sizes = [
            self.measure(
                line, artist_font if (i == len(lines)-1) else title_font, draw
            )
            for i, line in enumerate(lines)
        ]
        total_sizes = [sum(w for w, _ in lines_sizes), sum(h for _, h in lines_sizes)]
        spacing = title_font.size + 10
        y_start = space[1] + ((space[3]-space[1]-total_sizes[1]) / 2)
        for i, line in enumerate(lines):
            w, _ = lines_sizes[i]
            draw.text(
                (space[0] + (space[2]-space[0]-w) / 2, y_start),
                line,
                font=(artist_font if (i == (len(lines)-1)) else title_font),
                fill="#FFFFFF",
            )
            y_start += spacing

        draw.text(
            (75, 650),
            f"{(self.progress//1000//60):02}:{(self.progress//1000%60):02}",
            font=time_font,
            fill="#FFFFFF",
        )
        draw.text(
            (1745, 650),
            f"{(self.duration//1000//60):02}:{(self.duration//1000%60):02}",
            font=time_font,
            fill="#FFFFFF",
        )
        draw.rounded_rectangle([75, 700, 1845, 715], radius=15 // 2, fill="#A0A0A0")
        draw.rounded_rectangle(
            [75, 700, int(75 + (1770 * self.progress / self.duration)), 715],
            radius=15 // 2,
            fill="#FFFFFF",
        )

        by = io.BytesIO()
        banner.save(by, format="PNG")
        by.seek(0)
        by.name = "banner.png"
        return by


    def old(self):
        w, h = 1920, 768
        title_font = ImageFont.truetype(io.BytesIO(requests.get(self.onest_b).content), 80)
        art_font = ImageFont.truetype(io.BytesIO(requests.get(self.onest_r).content), 55)
        time_font = ImageFont.truetype(io.BytesIO(requests.get(self.onest_b).content), 36)

        track_cov = Image.open(io.BytesIO(self.track_cover)).convert("RGBA")
        banner = (
            track_cov.resize((w, w))
            .crop((0, (w - h) // 2, w, ((w - h) // 2) + h))
            .filter(ImageFilter.GaussianBlur(radius=14))
        )
        banner = ImageEnhance.Brightness(banner).enhance(0.3)

        track_cov = track_cov.resize((banner.size[1] - 150, banner.size[1] - 150))
        mask = Image.new("L", track_cov.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, track_cov.size[0], track_cov.size[1]), radius=35, fill=255
        )
        track_cov.putalpha(mask)
        track_cov = track_cov.crop(track_cov.getbbox())
        banner.paste(track_cov, (75, 75), mask)

        title_lines = textwrap.wrap(self.title, 23)
        if len(title_lines) > 1:
            title_lines[1] = (
                title_lines[1] + "..." if len(title_lines) > 2 else title_lines[1]
            )
        title_lines = title_lines[:2]
        artists_lines = textwrap.wrap(" • ".join(self.artists), width=40)
        if len(artists_lines) > 1:
            for index, art in enumerate(artists_lines):
                if "•" in art[-2:]:
                    artists_lines[index] = art[: art.rfind("•") - 1]

        draw = ImageDraw.Draw(banner)
        x, y = 150 + track_cov.size[0], 110
        for index, line in enumerate(title_lines):
            draw.text((x, y), line, font=title_font, fill="#FFFFFF")
            if index != len(title_lines) - 1:
                y += 70
        x, y = 150 + track_cov.size[0], 110 * 2
        if len(title_lines) > 1:
            y += 70
        for index, line in enumerate(artists_lines):
            draw.text((x, y), line, font=art_font, fill="#A0A0A0")
            if index != len(artists_lines) - 1:
                y += 50

        draw.rounded_rectangle(
            [768, 650, 768 + 1072, 650 + 15], radius=15 // 2, fill="#A0A0A0"
        )
        draw.rounded_rectangle(
            [768, 650, 768 + int(1072 * (self.progress / self.duration)), 650 + 15],
            radius=15 // 2,
            fill="#FFFFFF",
        )
        draw.text(
            (768, 600),
            f"{(self.progress//1000//60):02}:{(self.progress//1000%60):02}",
            font=time_font,
            fill="#FFFFFF",
        )
        draw.text(
            (1745, 600),
            f"{(self.duration//1000//60):02}:{(self.duration//1000%60):02}",
            font=time_font,
            fill="#FFFFFF",
        )

        by = io.BytesIO()
        banner.save(by, format="PNG")
        by.seek(0)
        by.name = "banner.png"
        return by


@loader.tds
class YaMusicMod(loader.Module):
    """The module for Yandex.Music streaming service"""

    strings = {"name": "YaMusic", "iguide": "📜 <b><a href=\"https://yandex-music.rtfd.io/en/main/token.html\">Guide for obtaining access token for Yandex.Music</a></b>"}
    strings_ru = {"_cls_doc": "Модуль для стримингового сервиса Яндекс.Музыка", "iguide": "📜 <b><a href=\"https://yandex-music.rtfd.io/en/main/token.html\">Гайд по получению токена Яндекс.Музыки</a></b>"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                option="token",
                default=None,
                doc=lambda: self.strings["_cfg"]["token"],
                validator=loader.validators.Hidden(),
            ),
            loader.ConfigValue(
                option="now_playing_text",
                default=(
                    "<emoji document_id=5474304919651491706>🎧</emoji> <b>{performer} — {title}</b>\n\n"
                    "<emoji document_id=6039404727542747508>⌨️</emoji> <b>Now is listening on <code>"
                    "{device}</code> (<emoji document_id=6039454987250044861>🔊</emoji> {volume}%)</b>\n"
                    "<emoji document_id=6039630677182254664>🗂</emoji> <b>Playing from:</b> {playing_from}"
                    "\n\n<emoji document_id=5242574232688298747>🎵</emoji> <b>{link} | "
                    '<a href="https://song.link/ya/{track_id}">song.link</a></b>'
                ),
                doc=lambda: self.strings["_cfg"]["now_playing_text"],
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                option="autobio_text",
                default="{performer} — {title}",
                doc=lambda: self.strings["_cfg"]["autobio_text"],
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                option="no_playing_bio_text",
                default="I use Heroku with YaMusic mod btw",
                doc=lambda: self.strings["_cfg"]["no_playing_bio_text"],
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                option="banner_version",
                default="new",
                doc=lambda: self.strings["_cfg"]["banner_version"],
                validator=loader.validators.Choice(["old", "new"]),
            ),
        )

    async def client_ready(self, client, db):
        self._client: telethon.TelegramClient = client
        self._db = db
        if not self.get("guide_sent", False):
            await self.inline.bot.send_message(self._tg_id, self.strings("iguide"))
            self.set("guide_sent", True)
        me = await self._client.get_me()
        self._premium = me.premium if hasattr(me, "premium") else False
        if self.get("autobio", False):
            self.autobio.start()

    @loader.loop(1800, autostart=True)
    async def premium_check(self):
        me = await self._client.get_me()
        self._premium = me.premium if hasattr(me, "premium") else False

    @loader.loop(30)
    async def autobio(self):
        if not self.config["token"]:
            self.autobio.stop()
            self.set("autobio", False)
            return
        now = await self.__get_now_playing()
        if now and (not now["paused"]):
            out = self.config["autobio_text"].format(
                title=now["track"]["title"],
                performer=", ".join(now["track"]["artist"]),
            )
        else:
            out = self.config["no_playing_bio_text"]
        try:
            await self._client(
                telethon.functions.account.UpdateProfileRequest(
                    about=out[: (140 if self._premium else 70)]
                )
            )
        except telethon.errors.rpcerrorlist.FloodWaitError as e:
            logger.info(f"Sleeping {max(e.seconds, 60)} because of floodwait")
            await asyncio.sleep(max(e.seconds, 60))


    @loader.command(ru_doc="👉 Гайд по получению токена Яндекс.Музыки", alias="yg")
    async def yguidecmd(self, message: telethon.types.Message):
        """👉 Guide for obtaining a Yandex.Music token"""
        await utils.answer(message, self.strings("guide"))


    @loader.command(ru_doc="👉 Включить/выключить автобио", alias="yb")
    async def ybiocmd(self, message: telethon.types.Message):
        """👉 Enable/disable autobio"""
        try:
            ym_client = await yandex_music.ClientAsync(self.config["token"]).init()
        except yandex_music.exceptions.UnauthorizedError:
            return await utils.answer(
                message, self.strings("errors")["no_token_or_invalid"]
            )

        bio = not self.get("autobio", False)
        self.set("autobio", bio)
        if bio:
            await self.autobio.func(self)
            self.autobio.start()
        else:
            self.autobio.stop()
            try:
                await self._client(
                    telethon.functions.account.UpdateProfileRequest(
                        about=self.config["no_playing_bio_text"][
                            : (140 if self._premium else 70)
                        ]
                    )
                )
            except:
                pass

        bio = self.get("autobio", False)
        await utils.answer(
            message, self.strings("autobio")["enabled" if bio else "disabled"]
        )


    @loader.command(ru_doc="👉 Поиск треков в Яндекс.Музыке", alias="yq")
    async def ysearchcmd(self, message: telethon.types.Message):
        """👉 Searching tracks in Yandex.Music"""
        try:
            ym_client = await yandex_music.ClientAsync(self.config["token"]).init()
        except yandex_music.exceptions.UnauthorizedError:
            return await utils.answer(
                message, self.strings("errors")["no_token_or_invalid"]
            )
        query = utils.get_args_raw(message)
        if not query:
            return await utils.answer(message, self.strings("errors")["no_query"])
        search = await ym_client.search(query, type_="track")
        if (not search.tracks) or (len(search.tracks.results) == 0):
            return await utils.answer(message, self.strings("errors")["not_found"])

        track = search.tracks.results[0]
        out = self.strings("search").format(
            title=track.title,
            performer=", ".join(track.artists_name()),
            track_id=track.track_id,
        )
        await utils.answer(message, out + self.strings("downloading_track"))

        audio = await self.__download_track(ym_client, search.tracks.results[0].id)
        await utils.answer(
            message=message,
            response=out,
            file=audio,
            attributes=(
                [
                    telethon.types.DocumentAttributeAudio(
                        duration=int(search.tracks.results[0].duration_ms / 1000),
                        title=search.tracks.results[0].title,
                        performer=", ".join(
                            [x.name for x in search.tracks.results[0].artists]
                        ),
                    )
                ]
            ),
        )


    @loader.command(
        ru_doc="👉 Получить баннер трека, который играет сейчас", alias="yn"
    )
    async def ynowcmd(self, message: telethon.types.Message):
        """👉 Get the banner of the track playing right now"""
        try:
            ym_client = await yandex_music.ClientAsync(self.config["token"]).init()
        except yandex_music.exceptions.UnauthorizedError:
            return await utils.answer(
                message, self.strings("errors")["no_token_or_invalid"]
            )
        await utils.answer(message, self.strings("uploading_banner"))
        now = await self.__get_now_playing()
        if not now:
            return await utils.answer(message, self.strings("errors")["no_playing"])
        track_object = (await ym_client.tracks(now["playable_id"]))[0]

        playlist_name = ""
        if now["entity_type"] == "PLAYLIST":
            playlist = (await ym_client.playlists_list(now["entity_id"]))[0]
            playlist_name = (
                f'<b><a href ="https://music.yandex.ru/users/'
                f"{playlist.owner.login}/playlists/{playlist.kind}"
                f'">{playlist.title}</a></b>'
            )
        if now["entity_type"] == "ALBUM":
            album = (await ym_client.albums(now["entity_id"]))[0]
            playlist_name = (
                f'<b><a href ="https://music.yandex.ru/album/'
                f'{album.id}">{album.title}</a></b>'
            )
        if now["entity_type"] == "ARTIST":
            artist = (await ym_client.artists(now["entity_id"]))[0]
            playlist_name = (
                f'<b><a href ="https://music.yandex.ru/artist/'
                f'{artist.id}">{artist.name}</a></b>'
            )
        if now["entity_type"] not in self.strings("_entity_types").keys():
            now["entity_type"] = "VARIOUS"

        device, volume = "Unknown Device", "❔"
        if now["device"]:
            device = now["device"][0]["info"]["title"]
            volume = round(now["device"][0]["volume"] * 100, 2)
        out = self.config["now_playing_text"].format(
            performer=", ".join(now["track"]["artist"]),
            title=now["track"]["title"],
            device=device,
            volume=volume,
            track_id=now["track"]["track_id"],
            album_id=now["track"]["album_id"],
            playing_from=self.strings("_entity_types")
            .get(now["entity_type"])
            .format(playlist_name),
            link=f"<a href=\"https://music.yandex.ru/track/{now['playable_id']}\">Яндекс.Музыка</a>",
        )
        try:
            await utils.answer(message, out + self.strings("uploading_banner"))
        except:
            pass

        banners = Banners(
            title=now["track"]["title"],
            artists=now["track"]["artist"],
            duration=now["duration_ms"],
            progress=now["progress_ms"],
            track_cover=requests.get(now["track"]["img"]).content,
        )
        file = getattr(banners, self.config["banner_version"], banners.new)()
        await utils.answer(message=message, response=out, file=file)


    @loader.command(ru_doc="👉 Получить трек, который играет сейчас", alias="ynt")
    async def ynowtcmd(self, message: telethon.types.Message):
        """👉 Get the track playing right now"""
        try:
            ym_client = await yandex_music.ClientAsync(self.config["token"]).init()
        except yandex_music.exceptions.UnauthorizedError:
            return await utils.answer(
                message, self.strings("errors")["no_token_or_invalid"]
            )
        await utils.answer(message, self.strings("downloading_track"))
        now = await self.__get_now_playing()
        if not now:
            return await utils.answer(message, self.strings("errors")["no_playing"])

        playlist_name = ""
        if now["entity_type"] == "PLAYLIST":
            playlist = (await ym_client.playlists_list(now["entity_id"]))[0]
            playlist_name = (
                f'<b><a href ="https://music.yandex.ru/users/'
                f"{playlist.owner.login}/playlists/{playlist.kind}"
                f'">{playlist.title}</a></b>'
            )
        if now["entity_type"] == "ALBUM":
            album = (await ym_client.albums(now["entity_id"]))[0]
            playlist_name = (
                f'<b><a href ="https://music.yandex.ru/album/'
                f'{album.id}">{album.title}</a></b>'
            )
        if now["entity_type"] == "ARTIST":
            artist = (await ym_client.artists(now["entity_id"]))[0]
            playlist_name = (
                f'<b><a href ="https://music.yandex.ru/artist/'
                f'{artist.id}">{artist.name}</a></b>'
            )
        if now["entity_type"] not in self.strings("_entity_types").keys():
            now["entity_type"] = "VARIOUS"

        device, volume = "Unknown Device", "❔"
        if now["device"]:
            device = now["device"][0]["info"]["title"]
            volume = round(now["device"][0]["volume"] * 100, 2)
        out = self.config["now_playing_text"].format(
            performer=", ".join(now["track"]["artist"]),
            title=now["track"]["title"],
            device=device,
            volume=volume,
            track_id=now["track"]["track_id"],
            album_id=now["track"]["album_id"],
            playing_from=self.strings("_entity_types")
            .get(now["entity_type"])
            .format(playlist_name),
            link=f"<a href=\"https://music.yandex.ru/track/{now['playable_id']}\">Яндекс.Музыка</a>",
        )
        try:
            await utils.answer(message, out + self.strings("downloading_track"))
        except:
            pass

        await utils.answer(
            message=message,
            response=out,
            file=now["track"]["bytes_io"],
            attributes=(
                [
                    telethon.types.DocumentAttributeAudio(
                        duration=int(now["duration_ms"] / 1000),
                        title=now["track"]["title"],
                        performer=", ".join(now["track"]["artist"]),
                    )
                ]
            ),
        )


    @loader.command(ru_doc="👉 Лайкнуть играющий сейчас трек")
    async def ylikecmd(self, message: telethon.types.Message):
        """👉 Like the track playing right now"""
        try:
            ym_client = await yandex_music.ClientAsync(self.config["token"]).init()
        except yandex_music.exceptions.UnauthorizedError:
            return await utils.answer(
                message, self.strings("errors")["no_token_or_invalid"]
            )
        now = await self.__get_now_playing()
        if not now:
            return await utils.answer(message, self.strings("errors")["no_playing"])
        await ym_client.users_likes_tracks_add(now["track"]["track_id"])
        await utils.answer(
            message,
            self.strings("likes")["liked"].format(
                track_id=now["track"]["track_id"],
                track=f"{', '.join(now['track']['artist'])} — {now['track']['title']}",
            ),
        )

    @loader.command(ru_doc="👉 Снять лайк с играющего сейчас трека")
    async def yunlikecmd(self, message: telethon.types.Message):
        """👉 Unlike the track playing right now"""
        try:
            ym_client = await yandex_music.ClientAsync(self.config["token"]).init()
        except yandex_music.exceptions.UnauthorizedError:
            return await utils.answer(
                message, self.strings("errors")["no_token_or_invalid"]
            )
        now = await self.__get_now_playing()
        if not now:
            return await utils.answer(message, self.strings("errors")["no_playing"])
        await ym_client.users_likes_tracks_remove(now["track"]["track_id"])
        await utils.answer(
            message,
            self.strings("likes")["unliked"].format(
                track_id=now["track"]["track_id"],
                track=f"{', '.join(now['track']['artist'])} — {now['track']['title']}",
            ),
        )

    @loader.command(ru_doc="👉 Дизлайкнуть играющий сейчас трек")
    async def ydislikecmd(self, message: telethon.types.Message):
        """👉 Dislike the track playing right now"""
        try:
            ym_client = await yandex_music.ClientAsync(self.config["token"]).init()
        except yandex_music.exceptions.UnauthorizedError:
            return await utils.answer(
                message, self.strings("errors")["no_token_or_invalid"]
            )
        now = await self.__get_now_playing()
        if not now:
            return await utils.answer(message, self.strings("errors")["no_playing"])
        await ym_client.users_dislikes_tracks_add(now["track"]["track_id"])
        await utils.answer(
            message,
            self.strings("likes")["disliked"].format(
                track_id=now["track"]["track_id"],
                track=f"{', '.join(now['track']['artist'])} — {now['track']['title']}",
            ),
        )


    @loader.command(ru_doc="👉 Получить текст играющего сейчас трека")
    async def ylyricscmd(self, message: telethon.types.Message):
        """👉 Get the lyrics of the track playing right now"""
        try:
            ym_client = await yandex_music.ClientAsync(self.config["token"]).init()
        except yandex_music.exceptions.UnauthorizedError:
            return await utils.answer(
                message, self.strings("errors")["no_token_or_invalid"]
            )
        now = await self.__get_now_playing()
        if not now:
            return await utils.answer(message, self.strings("errors")["no_playing"])
        try:
            lyrics = await ym_client.tracks_lyrics(now["track"]["track_id"])
            await utils.answer(
                message,
                self.strings("lyrics").format(
                    track_id=now["track"]["track_id"],
                    track=f"{', '.join(now['track']['artist'])} — {now['track']['title']}",
                    text=requests.get(lyrics.download_url).text,
                    writers=", ".join(lyrics.writers) if lyrics.writers else "Unknown",
                ),
            )
        except yandex_music.exceptions.NotFoundError:
            await utils.answer(
                message,
                self.strings("no_lyrics").format(
                    track_id=now["track"]["track_id"],
                    track=f"{', '.join(now['track']['artist'])} — {now['track']['title']}",
                ),
            )


    async def __download_track(
        self,
        client: yandex_music.ClientAsync,
        track_id: typing.Union[int, str],
        link_only: bool = False,
    ):
        last_exception = None
        for attempt in range(5):
            try:
                info = await client.tracks_download_info(
                    track_id, get_direct_links=True
                )
                if link_only:
                    return info[0].direct_link
                by = io.BytesIO(await info[0].download_bytes_async())
                by.name = "audio.mp3"
                return by
            except Exception as e:
                if attempt != 4:
                    await asyncio.sleep(1)
                    continue
                raise e

    # Original code: https://raw.githubusercontent.com/MIPOHBOPOHIH/YMMBFA/main/main.py
    async def __get_ynison(self):
        async def create_ws(token, ws_proto):
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(
                    "wss://ynison.music.yandex.ru/redirector.YnisonRedirectService/GetRedirectToYnison",
                    headers={
                        "Sec-WebSocket-Protocol": f"Bearer, v2, {json.dumps(ws_proto)}",
                        "Origin": "http://music.yandex.ru",
                        "Authorization": f"OAuth {token}",
                    },
                ) as ws:
                    response = await ws.receive()
                    return json.loads(response.data)

        device_id = "".join(random.choices(string.ascii_lowercase, k=16))
        ws_proto = {
            "Ynison-Device-Id": device_id,
            "Ynison-Device-Info": json.dumps({"app_name": "Chrome", "type": 1}),
        }
        data = await create_ws(self.config["token"], ws_proto)
        ws_proto["Ynison-Redirect-Ticket"] = data["redirect_ticket"]
        payload = {
            "update_full_state": {
                "player_state": {
                    "player_queue": {
                        "current_playable_index": -1,
                        "entity_id": "",
                        "entity_type": "VARIOUS",
                        "playable_list": [],
                        "options": {"repeat_mode": "NONE"},
                        "entity_context": "BASED_ON_ENTITY_BY_DEFAULT",
                        "version": {
                            "device_id": device_id,
                            "version": 9021243204784341000,
                            "timestamp_ms": 0,
                        },
                        "from_optional": "",
                    },
                    "status": {
                        "duration_ms": 0,
                        "paused": True,
                        "playback_speed": 1,
                        "progress_ms": 0,
                        "version": {
                            "device_id": device_id,
                            "version": 8321822175199937000,
                            "timestamp_ms": 0,
                        },
                    },
                },
                "device": {
                    "capabilities": {
                        "can_be_player": True,
                        "can_be_remote_controller": False,
                        "volume_granularity": 16,
                    },
                    "info": {
                        "device_id": device_id,
                        "type": "WEB",
                        "title": "Chrome Browser",
                        "app_name": "Chrome",
                    },
                    "volume_info": {"volume": 0},
                    "is_shadow": True,
                },
                "is_currently_active": False,
            },
            "rid": "ac281c26-a047-4419-ad00-e4fbfda1cba3",
            "player_action_timestamp_ms": 0,
            "activity_interception_type": "DO_NOT_INTERCEPT_BY_DEFAULT",
        }
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                f"wss://{data['host']}/ynison_state.YnisonStateService/PutYnisonState",
                headers={
                    "Sec-WebSocket-Protocol": f"Bearer, v2, {json.dumps(ws_proto)}",
                    "Origin": "http://music.yandex.ru",
                    "Authorization": f"OAuth {self.config['token']}",
                },
            ) as ws:
                await ws.send_str(json.dumps(payload))
                response = await ws.receive()
                ynison: dict = json.loads(response.data)
        return ynison

    async def __get_now_playing(self):
        if not self.config["token"]:
            return {}
        try:
            ym_client = await yandex_music.ClientAsync(self.config["token"]).init()
        except yandex_music.exceptions.UnauthorizedError:
            return {}

        ynison = await self.__get_ynison()
        if (len(ynison.get("player_state", {}).get("player_queue", {}).get("playable_list", [])) == 0):
            return {}
        raw_track = ynison["player_state"]["player_queue"]["playable_list"][
            ynison["player_state"]["player_queue"]["current_playable_index"]
        ]
        ym_client = await yandex_music.ClientAsync(self.config["token"]).init()
        track_object = (await ym_client.tracks(raw_track["playable_id"]))[0]
        return (
            {
                "paused": ynison["player_state"]["status"]["paused"],
                "playable_id": raw_track["playable_id"],
                "duration_ms": int(ynison["player_state"]["status"]["duration_ms"]),
                "progress_ms": int(ynison["player_state"]["status"]["progress_ms"]),
                "entity_id": ynison["player_state"]["player_queue"]["entity_id"],
                "entity_type": ynison["player_state"]["player_queue"]["entity_type"],
                "device": [
                    x
                    for x in ynison["devices"]
                    if x["info"]["device_id"]
                    == ynison.get("active_device_id_optional", "")
                ],
                "track": {
                    "track_id": track_object.track_id,
                    "album_id": track_object.albums[0].id,
                    "title": track_object.title,
                    "artist": track_object.artists_name(),
                    "img": f"https://{track_object.cover_uri[:-2]}1000x1000",
                    "duration": track_object.duration_ms // 1000,
                    "minutes": round(track_object.duration_ms / 1000) // 60,
                    "seconds": round(track_object.duration_ms / 1000) % 60,
                    "bytes_io": (
                        await self.__download_track(ym_client, track_object.track_id)
                    ),
                },
            }
            if raw_track["playable_type"] != "LOCAL_TRACK"
            else {}
        )
