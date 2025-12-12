# На модуль распространяется лицензия "GNU General Public License v3.0"
# https://github.com/all-licenses/GNU-General-Public-License-v3.0

# meta developer: @PyModule
import requests
from bs4 import BeautifulSoup, Tag, NavigableString
import re
from .. import loader, utils

@loader.tds
class LyricsMod(loader.Module):
    """Модуль для поиска текста песни через Genius API напрямую"""

    strings = {"name": "Lyrics"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "GENIUS_TOKEN",
            None,
            lambda: "Токен для доступа к Genius API. Получите его на https://genius.com/api-clients",
        )

    def get_token(self):
        token = self.config["GENIUS_TOKEN"]
        if not token:
            return None
        return token
    
    def lyrics(self, html: str) -> str:
            soup = BeautifulSoup(html, "html.parser")
            for remove in soup.find_all("div", class_=re.compile("LyricsHeader__Container")):
                remove.decompose()
            containers = soup.find_all("div", attrs={"data-lyrics-container": "true"})
            if not containers:
                return None
            lyrics = ""
            for container in containers:
                for elem in container.contents:
                    if isinstance(elem, Tag):
                        if elem.name == "br":
                            lyrics += "\n"
                        else:
                            lyrics += elem.get_text(separator="\n")
                    elif isinstance(elem, NavigableString):
                        lyrics += str(elem)
            lyrics = re.sub(r"\n{3,}", "\n\n", lyrics)
            return lyrics.strip()

    async def lyricscmd(self, message):
        """[запрос] - Найти текст песни по запросу"""
        token = self.get_token()
        if not token:
            return await message.edit(
                "<emoji document_id=5774077015388852135>❌</emoji> <b>Токен Genius API не установлен. Используйте <code>.cfg Lyrics</code>.</b>"
            )

        query = utils.get_args_raw(message)
        if not query:
            return await message.edit("<emoji document_id=5253959125838090076>👁</emoji> <b>Использование:</b> .lyrics [название песни]")

        await message.edit(f"<emoji document_id=5253959125838090076>👁</emoji> <b>Ищу текст песни:</b> {query}...")

        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(f"https://api.genius.com/search?q={requests.utils.quote(query)}", headers=headers, timeout=10)
            if response.status_code != 200:
                return await message.edit(f"<b>Ошибка API Genius:</b> {response.status_code}")

            data = response.json()
            hits = data.get("response", {}).get("hits", [])
            if not hits:
                return await message.edit("<emoji document_id=5774077015388852135>❌</emoji> <b>Песня не найдена.</b>")

            song_info = hits[0]["result"]
            song_url = song_info["url"]
            song_title = song_info["title"]
            artist_name = song_info["primary_artist"]["name"]

            html = requests.get(song_url).text
            lyrics = self.lyrics(html)

            if lyrics and len(lyrics) > 4096:
                lyrics = lyrics[:4000] + "\n\n<b>Текст обрезан из-за ограничения Telegram.</b>"

            text = f"<b><emoji document_id=5938473438468378529>🎶</emoji> {song_title} — {artist_name}</b>\n\n"
            if lyrics:
                text += f"<blockquote expandable><b>{lyrics}</b></blockquote>"
            else:
                text += f"<b><emoji document_id=5774077015388852135>❌</emoji> Текст песни не найден.</b>"

            await message.edit(text)

        except Exception as e:
            await message.edit(f"<b>Ошибка:</b> {str(e)}")
