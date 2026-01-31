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
# requires: pillow

import io
import asyncio

from telethon import functions, types
from PIL import Image

from .. import loader, utils


@loader.tds
class PicToStoriesMod(loader.Module):
    """Grid for stories"""

    strings = {
        "name": "PicToStories",
        "no_rep": (
            "<emoji document_id=5879813604068298387>❗️</emoji> "
            "<b>Reply to photo!</b>"
        ),
        "work": (
            "<emoji document_id=5841359499146825803>🕔</emoji> "
            "<b>Processing...</b>"
        ),
        "done": (
            "<emoji document_id=5776375003280838798>✅</emoji> "
            "<b>Done! Check your profile.</b>"
        ),
        "err": (
            "<emoji document_id=5778527486270770928>❌</emoji> "
            "<b>Error:</b> {}"
        ),
    }

    strings_ru = {
        "no_rep": (
            "<emoji document_id=5879813604068298387>❗️</emoji> "
            "<b>Реплай на фото!</b>"
        ),
        "work": (
            "<emoji document_id=5841359499146825803>🕔</emoji> "
            "<b>Обрабатываю...</b>"
        ),
        "done": (
            "<emoji document_id=5776375003280838798>✅</emoji> "
            "<b>Готово! Проверяй профиль.</b>"
        ),
        "err": (
            "<emoji document_id=5778527486270770928>❌</emoji> "
            "<b>Ошибка:</b> {}"
        ),
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "period",
                48,
                lambda: "Visibility period in hours",
                validator=loader.validators.Integer(),
            ),
            loader.ConfigValue(
                "blacklist",
                [],
                lambda: "Blacklisted user IDs",
                validator=loader.validators.Series(loader.validators.Integer()),
            ),
            loader.ConfigValue(
                "cooldown",
                0,
                lambda: "Cooldown between stories in seconds",
                validator=loader.validators.Integer(minimum=0),
            ),
        )

    @loader.command(ru_doc="<реплай на фото> [название альбома] - сделать сетку")
    async def ptscmd(self, message):
        """<reply to photo> [album name] - make grid"""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        if not reply or not reply.media:
            await utils.answer(message, self.strings("no_rep"))
            return

        try:
            image_bytes = await reply.download_media(file=bytes)
            img = Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            await utils.answer(message, self.strings("err").format(e))
            return

        await utils.answer(message, self.strings("work"))

        w, h = img.size
        curr_ratio = w / h
        variants = [
            (5 / 4, 2),
            (4 / 5, 3),
            (3 / 5, 4),
            (9 / 16, 5)
        ]
        best_ratio, rows = min(variants, key=lambda x: abs(curr_ratio - x[0]))

        new_h = int(w / best_ratio)
        img = img.resize((w, new_h), Image.LANCZOS)
        w, h = img.size

        parts = []
        pw, ph = w // 3, h // rows
        for r in range(rows):
            for c in range(3):
                x, y = c * pw, r * ph
                parts.append(img.crop((x, y, x + pw, y + ph)))

        parts.reverse()

        privacy = [types.InputPrivacyValueAllowAll()]
        if self.config["blacklist"]:
            entities = []
            for uid in self.config["blacklist"]:
                try:
                    entities.append(await self.client.get_input_entity(uid))
                except Exception:
                    continue
            if entities:
                privacy.append(types.InputPrivacyValueDisallowUsers(users=entities))

        story_ids = []
        for i, p in enumerate(parts):
            out = io.BytesIO()
            p.save(out, "JPEG", quality=95)
            out.seek(0)

            uploaded_file = await self.client.upload_file(out, file_name="s.jpg")
            res = await self.client(
                functions.stories.SendStoryRequest(
                    peer=types.InputPeerSelf(),
                    media=types.InputMediaUploadedPhoto(uploaded_file),
                    privacy_rules=privacy,
                    period=self.config["period"] * 3600,
                )
            )

            sid = next(
                (
                    u.story_id if hasattr(u, "story_id") else u.id
                    for u in res.updates
                    if hasattr(u, "story_id") or hasattr(u, "id")
                ),
                None,
            )

            if sid:
                story_ids.append(sid)

            if self.config["cooldown"] > 0 and i < len(parts) - 1:
                await asyncio.sleep(self.config["cooldown"])

        if not story_ids:
            return

        if args:
            all_albums = await self.client(
                functions.stories.GetAlbumsRequest(peer=types.InputPeerSelf(), hash=0)
            )
            
            target = next(
                (a for a in all_albums.albums if getattr(a, 'title', '') == args),
                None
            )

            if target:
                await self.client(
                    functions.stories.UpdateAlbumRequest(
                        peer=types.InputPeerSelf(),
                        album_id=target.album_id,
                        add_stories=story_ids,
                    )
                )
            else:
                await self.client(
                    functions.stories.CreateAlbumRequest(
                        peer=types.InputPeerSelf(),
                        stories=story_ids,
                        title=args,
                    )
                )
        else:
            await self.client(
                functions.stories.TogglePinnedRequest(
                    peer=types.InputPeerSelf(), id=story_ids, pinned=True
                )
            )

        await utils.answer(message, self.strings("done"))