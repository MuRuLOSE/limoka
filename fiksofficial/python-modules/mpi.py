#         ______     ___  ___          _       _      
#    ____ | ___ \    |  \/  |         | |     | |     
#   / __ \| |_/ /   _| .  . | ___   __| |_   _| | ___ 
#  / / _` |  __/ | | | |\/| |/ _ \ / _` | | | | |/ _ \
# | | (_| | |  | |_| | |  | | (_) | (_| | |_| | |  __/
#  \ \__,_\_|   \__, \_|  |_/\___/ \__,_|\__,_|_|\___|
#   \____/       __/ |                                
#               |___/                                  

# На модуль распространяется лицензия "GNU General Public License v3.0"
# https://github.com/all-licenses/GNU-General-Public-License-v3.0

# meta developer: @pymodule
# meta fhsdesc: tool, tools, minecraft, game

import aiohttp
import base64
import json
from datetime import datetime
from .. import loader, utils

async def download_image(session: aiohttp.ClientSession, url: str):
    try:
        async with session.get(url, timeout=35) as resp:
            if resp.status == 200:
                return await resp.read()
    except Exception:
        pass
    return None

@loader.tds
class MinecraftPlayerInfo(loader.Module):
    """A module for obtaining information about a Minecraft player by nickname"""
    strings = {
        "name": "MinecraftPlayerInfo",
        "no_args": "<b>❌ Specify the player's nickname</b>",
        "not_found": "<b>❌ Player with this nickname not found</b>",
        "loading": "<b>🔄 Loading information...</b>",
        "no_media": "<b>❌ Failed to load any images</b>",
        "partial_media": "<i>⚠️ Some images failed to load</i>\n\n",
        "no_history": "No nickname history",
        "model_steve": "Classic (Steve)",
        "model_alex": "Slim (Alex)",
        "cape_yes": "Yes ✅",
        "cape_no": "No ❌",
        "cape_failed": " (render failed to load)",
        "history_current": "— current",
        "history_changed": "— changed {}",
        "history_original": "— original",
        "info": (
            "<b>🔍 Minecraft Player Information</b>\n\n"
            "<b>Nickname:</b> <code>{name}</code>\n"
            "<b>UUID:</b> <code>{uuid_dashed}</code>\n"
            "<b>Skin Model:</b> {model}\n"
            "<b>Cape:</b> {cape}\n\n"
            "<b>Nickname History:</b>\n{history}\n\n"
            "<a href=\"https://namemc.com/profile/{uuid_raw}\">🔗 Full profile on NameMC</a>"
        )
    }

    strings_ru = {
        "_cls_doc": "Модуль для получения информации о игроке Minecraft по никнейму",
        "no_args": "<b>❌ Укажите никнейм игрока</b>",
        "not_found": "<b>❌ Игрок с таким никнеймом не найден</b>",
        "loading": "<b>🔄 Загружаю информацию...</b>",
        "no_media": "<b>❌ Не удалось загрузить ни одного изображения</b>",
        "partial_media": "<i>⚠️ Некоторые изображения не загрузились</i>\n\n",
        "no_history": "Нет истории изменений",
        "model_steve": "Classic (Steve)",
        "model_alex": "Slim (Alex)",
        "cape_yes": "Есть ✅",
        "cape_no": "Нет ❌",
        "cape_failed": " (рендер не загрузился)",
        "history_current": "— текущий",
        "history_changed": "— изменён {}",
        "history_original": "— оригинальный",
        "info": (
            "<b>🔍 Информация о игроке Minecraft</b>\n\n"
            "<b>Никнейм:</b> <code>{name}</code>\n"
            "<b>UUID:</b> <code>{uuid_dashed}</code>\n"
            "<b>Модель скина:</b> {model}\n"
            "<b>Плащ:</b> {cape}\n\n"
            "<b>История никнеймов:</b>\n{history}\n\n"
            "<a href=\"https://namemc.com/profile/{uuid_raw}\">🔗 Полный профиль на NameMC</a>"
        )
    }

    async def client_ready(self, client, db):
        self.client = client

    @loader.command(ru_doc="<никнейм> — отображает информацию об игроке Minecraft (3D-рендеринг, история, плащ)")
    async def mcplayer(self, message):
        """<nickname> — show Minecraft player info (3D renders, history, cape)"""
        args = utils.get_args_raw(message)
        if not args:
            return await utils.answer(message, self.strings("no_args"))

        loading_msg = await utils.answer(message, self.strings("loading"))

        nick = args.strip()

        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.mojang.com/users/profiles/minecraft/{nick}") as resp:
                if resp.status == 204 or resp.status != 200:
                    await loading_msg.edit(self.strings("not_found"))
                    return
                data = await resp.json()

            name = data["name"]
            uuid = data["id"]
            uuid_dashed = f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"

            async with session.get(f"https://api.mojang.com/user/profiles/{uuid}/names") as resp:
                names = await resp.json() if resp.status == 200 else [{"name": name}]

            history_lines = []
            for i, entry in enumerate(names):
                uname = entry["name"]
                if i == len(names) - 1:
                    history_lines.append(f"• <b>{uname}</b> {self.strings('history_current')}")
                elif "changedToAt" in entry:
                    changed = datetime.utcfromtimestamp(entry["changedToAt"] / 1000).strftime("%d.%m.%Y")
                    history_lines.append(f"• {uname} {self.strings('history_changed').format(changed)}")
                else:
                    history_lines.append(f"• {uname} {self.strings('history_original')}")

            history = "\n".join(history_lines) or self.strings("no_history")

            async with session.get(f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}?unsigned=false") as resp:
                profile = await resp.json() if resp.status == 200 else {}

            cape_url = None
            model = self.strings("model_steve")
            if profile.get("properties"):
                for prop in profile["properties"]:
                    if prop["name"] == "textures":
                        textures_b64 = prop["value"]
                        textures_json = json.loads(base64.b64decode(textures_b64).decode("utf-8"))
                        textures = textures_json.get("textures", {})
                        skin_data = textures.get("SKIN", {})
                        cape_url = textures.get("CAPE", {}).get("url")
                        if "metadata" in skin_data and skin_data["metadata"].get("model") == "slim":
                            model = self.strings("model_alex")

            has_cape = bool(cape_url)
            cape_text = self.strings("cape_yes") if has_cape else self.strings("cape_no")

            body_urls = [
                f"https://crafthead.net/body/{uuid}.png",
                f"https://api.mineatar.io/body/{uuid}?scale=12",
                f"https://mc-heads.net/body/{uuid}/500",
                f"https://cravatar.eu/helmbody/{uuid}/500.png",
                f"https://minotar.net/body/{uuid}/500.png",
            ]

            head_urls = [
                f"https://crafthead.net/avatar/{uuid}.png",
                f"https://api.mineatar.io/head/{uuid}?scale=12",
                f"https://mc-heads.net/avatar/{uuid}/500",
                f"https://cravatar.eu/head/{uuid}/500.png",
                f"https://minotar.net/avatar/{uuid}/500.png",
            ]

            body_bytes = None
            for url in body_urls:
                body_bytes = await download_image(session, url)
                if body_bytes:
                    break

            head_bytes = None
            for url in head_urls:
                head_bytes = await download_image(session, url)
                if head_bytes:
                    break

            cape_bytes = await download_image(session, cape_url) if cape_url else None
            if not cape_bytes and has_cape:
                cape_fallbacks = [
                    f"https://crafthead.net/cape/{uuid}.png",
                    f"https://api.mineatar.io/cape/{uuid}.png",
                    f"https://mc-heads.net/cape/{uuid}",
                ]
                for url in cape_fallbacks:
                    cape_bytes = await download_image(session, url)
                    if cape_bytes:
                        break
                if not cape_bytes:
                    cape_text += self.strings("cape_failed")

            uploaded_media = []

            if body_bytes:
                uploaded = await self.client.upload_file(body_bytes, file_name=f"{name}_body.png")
                uploaded_media.append(uploaded)

            if head_bytes:
                uploaded = await self.client.upload_file(head_bytes, file_name=f"{name}_head.png")
                uploaded_media.append(uploaded)

            if cape_bytes:
                uploaded = await self.client.upload_file(cape_bytes, file_name=f"{name}_cape.png")
                uploaded_media.append(uploaded)

            if not uploaded_media:
                await loading_msg.edit(self.strings("no_media"))
                return

            caption = self.strings("info").format(
                name=name,
                uuid_dashed=uuid_dashed,
                uuid_raw=uuid,
                model=model,
                cape=cape_text,
                history=history
            )

            if not (body_bytes and head_bytes):
                caption = self.strings("partial_media") + caption

            await self.client.send_file(
                message.peer_id,
                file=uploaded_media,
                caption=caption,
                parse_mode="html",
                reply_to=message.reply_to_msg_id or message.id
            )

        await loading_msg.delete()
        if message.out:
            await message.delete()