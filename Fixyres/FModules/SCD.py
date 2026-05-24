__version__ = (1, 0, 0)

# ©️ Fixyres, 2026-2030
# 🌐 https://github.com/Fixyres/FModules
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# 🔑 http://www.apache.org/licenses/LICENSE-2.0

# meta banner: https://raw.githubusercontent.com/Fixyres/FModules/refs/heads/main/assets/SCD/banner.png
# meta developer: @NFModules
# meta fhsdesc: SoundCloud, Music, Music downloader, Downloader

# requires: curl_cffi

import io
import re
import json
from telethon.tl.types import DocumentAttributeAudio
from curl_cffi import requests
from .. import loader, utils


@loader.tds
class SCD(loader.Module):
    '''Module for downloading songs from SoundCloud.'''
    
    _client_id = None

    strings = {
        "name": "SCD",
        "_cls_doc": "Module for downloading songs from SoundCloud.",
        "no_args": "✘ <b>You didn't provide a link to the song, example of using the command: <code>{prefix}sc (link)</code></b>",
        "downloading": "↓ <b>Downloading...</b>",
        "not_found": "✘ <b>Song not found.</b>"
    }

    strings_ru = {
        "_cls_doc": "Модуль для скачивания песен с SoundCloud.",
        "no_args": "✘ <b>Вы не указали ссылку на песню, пример использования команды: <code>{prefix}sc (ссылка)</code></b>",
        "downloading": "↓ <b>Скачивание...</b>",
        "not_found": "✘ <b>Песня не найдена.</b>"
    }

    strings_ua = {
        "_cls_doc": "Модуль для завантаження пісень із SoundCloud.",
        "no_args": "✘ <b>Ви не вказали посилання на пісню, приклад використання команди: <code>{prefix}sc (посилання)</code></b>",
        "downloading": "↓ <b>Завантаження...</b>",
        "not_found": "✘ <b>Пісню не знайдено.</b>"
    }

    strings_de = {
        "_cls_doc": "Modul zum Herunterladen von Liedern von SoundCloud.",
        "no_args": "✘ <b>Sie haben keinen Link zum Lied angegeben, Anwendungsbeispiel des Befehls: <code>{prefix}sc (Link)</code></b>",
        "downloading": "↓ <b>Wird heruntergeladen...</b>",
        "not_found": "✘ <b>Lied nicht gefunden.</b>"
    }

    strings_uz = {
        "_cls_doc": "SoundCloud-dan qo'shiqlarni yuklab olish uchun modul.",
        "no_args": "✘ <b>Siz qo'shiq havolasini kiritmadingiz, buyruqdan foydalanish misoli: <code>{prefix}sc (havola)</code></b>",
        "downloading": "↓ <b>Yuklab olinmoqda...</b>",
        "not_found": "✘ <b>Qo'shiq topilmadi.</b>"
    }

    strings_kz = {
        "_cls_doc": "SoundCloud-тан әндерді жүктеп алуға арналған модуль.",
        "no_args": "✘ <b>Сіз әнге сілтеме көрсетпедіңіз, бұйрықты пайдалану мысалы: <code>{prefix}sc (сілтеме)</code></b>",
        "downloading": "↓ <b>Жүктелуде...</b>",
        "not_found": "✘ <b>Ән табылмады.</b>"
    }

    strings_fr = {
        "_cls_doc": "Module pour télécharger des chansons depuis SoundCloud.",
        "no_args": "✘ <b>Vous n'avez pas fourni de lien vers la chanson, exemple d'utilisation de la commande: <code>{prefix}sc (lien)</code></b>",
        "downloading": "↓ <b>Téléchargement...</b>",
        "not_found": "✘ <b>Chanson non trouvée.</b>"
    }

    strings_jp = {
        "_cls_doc": "SoundCloudから曲をダウンロードするためのモジュール。",
        "no_args": "✘ <b>曲へのリンクが指定されていません。コマンドの使用例: <code>{prefix}sc (リンク)</code></b>",
        "downloading": "↓ <b>ダウンロード中...</b>",
        "not_found": "✘ <b>曲が見つかりません。</b>"
    }

    async def _get_client_id(self, ses, html):
        if self._client_id:
            return self._client_id
        for scr in reversed(re.findall(r'src="(https://a-v2\.sndcdn\.com/assets/[^"]+\.js)"', html)):
            m = re.search(r'client_id:"([a-zA-Z0-9]{32})"', (await ses.get(scr)).text)
            if m:
                self._client_id = m.group(1)
                return self._client_id
        raise ValueError()

    @loader.command(
        ru_doc="(ссылка) - скачать песню с SoundCloud.",
        ua_doc="(посилання) - завантажити пісню з SoundCloud.",
        de_doc="(Link) - laden Sie ein Lied von SoundCloud herunter.",
        uz_doc="(havola) - SoundCloud-dan qo'shiq yuklab olish.",
        kz_doc="(сілтеме) - SoundCloud-тан әнді жүктеп алу.",
        fr_doc="(lien) - télécharger une chanson depuis SoundCloud.",
        jp_doc="(リンク) - SoundCloudから曲をダウンロードします。"
    )
    async def scd(self, message):
        '''(link) - download a song from SoundCloud.'''
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["no_args"].format(prefix=self.get_prefix()))
            return

        m = re.search(r"(https?://(?:[a-zA-Z0-9-]+\.)?soundcloud\.com/[^\s]+)", args)
        if not m:
            await utils.answer(message, self.strings["not_found"])
            return

        msg = await utils.answer(message, self.strings["downloading"])

        try:
            async with requests.AsyncSession(impersonate="chrome120") as ses:
                h_resp = await ses.get(m.group(1))
                if h_resp.status_code != 200:
                    raise ValueError()
                
                html = h_resp.text
                c_id = await self._get_client_id(ses, html)
                
                h_m = re.search(r'window\.__sc_hydration\s*=\s*(\[.*?\]);</script>', html)
                if not h_m:
                    raise ValueError()

                t_d = next((i.get("data") for i in json.loads(h_m.group(1)) if i.get("hydratable") == "sound"), None)
                if not t_d or t_d.get('kind') != 'track':
                    raise ValueError()

                art = t_d.get("artwork_url") or t_d.get("user", {}).get("avatar_url")
                if art:
                    art = art.replace("-large.jpg", "-t500x500.jpg")
                
                tr = t_d.get("media", {}).get("transcodings", [])
                if not tr:
                    raise ValueError()

                s_info = next((t for t in tr if t.get("format", {}).get("protocol") == "progressive"), tr[0])
                s_url = s_info.get("url") + f"?client_id={c_id}" + (f"&track_authorization={t_d.get('track_authorization')}" if t_d.get("track_authorization") else "")
                
                s_resp = await ses.get(s_url)
                if s_resp.status_code != 200 or not s_resp.json().get("url"):
                    raise ValueError()

                a_buf = io.BytesIO()
                a_buf.name = "track.mp3"

                if s_info.get("format", {}).get("protocol") == "progressive":
                    m_resp = await ses.get(s_resp.json().get("url"))
                    if m_resp.status_code != 200:
                        raise ValueError()
                    a_buf.write(m_resp.content)
                else:
                    m3_resp = await ses.get(s_resp.json().get("url"))
                    if m3_resp.status_code != 200:
                        raise ValueError()
                    chk = [l for l in m3_resp.text.splitlines() if l and not l.startswith('#')]
                    if not chk:
                        raise ValueError()
                    for c_u in chk:
                        c_r = await ses.get(c_u)
                        if c_r.status_code != 200:
                            raise ValueError()
                        a_buf.write(c_r.content)

                a_buf.seek(0)
                
                t_buf = None
                if art:
                    try:
                        a_r = await ses.get(art)
                        if a_r.status_code == 200:
                            t_buf = io.BytesIO(a_r.content)
                            t_buf.name = "cover.jpg"
                    except:
                        pass

                await message.client.send_file(
                    message.peer_id,
                    a_buf,
                    thumb=t_buf,
                    attributes=[DocumentAttributeAudio(
                        duration=t_d.get("duration", 0) // 1000,
                        title=t_d.get("title", "Unknown"),
                        performer=t_d.get("user", {}).get("username", "Unknown Artist")
                    )],
                    reply_to=message.reply_to_msg_id
                )
                await msg.delete()

        except:
            await utils.answer(msg, self.strings["not_found"])
