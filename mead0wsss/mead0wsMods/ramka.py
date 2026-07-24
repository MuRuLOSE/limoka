# -- version --
__version__ = (1, 1, 0)
# -- version --


# ███╗░░░███╗███████╗░█████╗░██████╗░░█████╗░░██╗░░░░░░░██╗░██████╗░██████╗
# ████╗░████║██╔════╝██╔══██╗██╔══██╗██╔══██╗░██║░░██╗░░██║██╔════╝██╔════╝
# ██╔████╔██║█████╗░░███████║██║░░██║██║░░██║░╚██╗████╗██╔╝╚█████╗░╚█████╗░
# ██║╚██╔╝██║██╔══╝░░██╔══██║██║░░██║██║░░██║░░████╔═████║░░╚═══██╗░╚═══██╗
# ██║░╚═╝░██║███████╗██║░░██║██████╔╝╚█████╔╝░░╚██╔╝░╚██╔╝░██████╔╝██████╔╝
# ╚═╝░░░░░╚═╝╚══════╝╚═╝░░╚═╝╚═════╝░░╚════╝░░░░╚═╝░░░╚═╝░░╚═════╝░╚═════╝░
#                © Copyright 2026
#            ✈ https://t.me/mead0wssMods


# meta developer: @mead0wssMods
# scope: heroku_only
# requires: aiohttp pillow

import io
import aiohttp
import logging
from collections import deque
from PIL import Image, ImageDraw, ImageFont, ImageOps
from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class RamkaMod(loader.Module):
    strings = {
        "name": "Ramka",
        "no_reply_photo": "<b><tg-emoji emoji-id=5870782662234346251>🖼</tg-emoji></b><b> Требуется реплай на фото!</b>",
        "no_reply_msg": "<b><tg-emoji emoji-id=5870782662234346251>🖼</tg-emoji></b><b> Требуется реплай на сообщение!</b>",
        "processing": "<tg-emoji emoji-id=5116476703002068797>⌛️</tg-emoji> <b>Процесс создания рамки...</b>",
        "download_error": "<tg-emoji emoji-id=5078075400408531654>❌</tg-emoji> <b>Ошибка при скачивании ассетов.</b>",
        "process_error": "<tg-emoji emoji-id=5078075400408531654>❌</tg-emoji> <b>Ошибка при обработке:</b> <code>{}</code>"
    }

    async def client_ready(self, client, db):
        self.client = client
        self.frame_photo_url = "https://raw.githubusercontent.com/mead0wsss/mead0wsMods/modules/rama.png"
        self.frame_msg_url = "https://www.clipartmax.com/png/full/283-2835256_golden-frame-png-image-background-frame-gold-png-transparent.png"
        self.font_url = "https://github.com/source-foundry/Hack/raw/refs/heads/master/build/ttf/Hack-Bold.ttf"
    
    async def fetch_bytes(self, url: str) -> bytes:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
        return None

    def _punch_hole(self, img):
        w, h = img.size
        px = img.load()

        def is_dark_opaque(x, y):
            r_, g_, b_, a_ = px[x, y]
            return a_ > 200 and (r_ + g_ + b_) < 90

        cx, cy = w // 2, h // 2
        if not is_dark_opaque(cx, cy):
            return (int(w * 0.17), int(h * 0.23), int(w * 0.84), int(h * 0.77))

        visited = {(cx, cy)}
        q = deque([(cx, cy)])
        inner_pts = []
        while q:
            x, y = q.popleft()
            inner_pts.append((x, y))
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited and is_dark_opaque(nx, ny):
                    visited.add((nx, ny))
                    q.append((nx, ny))

        xs = [p[0] for p in inner_pts]
        ys = [p[1] for p in inner_pts]
        box = (min(xs), min(ys), max(xs), max(ys))

        for (x, y) in inner_pts:
            r_, g_, b_, _ = px[x, y]
            px[x, y] = (r_, g_, b_, 0)

        return box

    def _create_avatar(self, avatar_bytes, name, font_bytes, size=110):
        if avatar_bytes:
            img = Image.open(io.BytesIO(avatar_bytes)).convert("RGB")
            img = ImageOps.fit(img, (size, size), Image.Resampling.LANCZOS)
        else:
            colors = [(255, 99, 71), (60, 179, 113), (65, 105, 225), (238, 130, 238), (255, 165, 0)]
            color = colors[sum(ord(c) for c in name) % len(colors)] if name else colors[0]
            img = Image.new("RGB", (size, size), color)
            draw = ImageDraw.Draw(img)
            letter = name.strip()[0].upper() if name.strip() else "?"
            try:
                font = ImageFont.truetype(io.BytesIO(font_bytes), int(size * 0.45))
            except Exception:
                font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), letter, font=font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text(((size - w) // 2 - bbox[0], (size - h) // 2 - bbox[1]), letter, font=font, fill=(255, 255, 255))

        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        out.paste(img, (0, 0))
        out.putalpha(mask)
        return out

    def _create_message_card(self, avatar_img, name, text, font_bytes, photo_img=None):
        pad, gap, avatar_size, card_width = 40, 30, 110, 760
        font_name = ImageFont.truetype(io.BytesIO(font_bytes), 30)
        font_text = ImageFont.truetype(io.BytesIO(font_bytes), 38)

        text_x = pad + avatar_size + gap
        max_text_width = card_width - text_x - pad

        lines = []
        text_h = 0
        line_h = 0

        if text:
            for para in text.split('\n'):
                words = para.split(' ')
                curr_line = ""
                for word in words:
                    test_line = curr_line + word + " "
                    if font_text.getlength(test_line) <= max_text_width:
                        curr_line = test_line
                    else:
                        if curr_line:
                            lines.append(curr_line)
                        curr_line = word + " "
                if curr_line:
                    lines.append(curr_line)

            line_bbox = font_text.getbbox("Ay")
            line_h = line_bbox[3] - line_bbox[1] + 12
            text_h = len(lines) * line_h

        photo_h = 0
        if photo_img:
            if photo_img.width > max_text_width:
                scale = max_text_width / photo_img.width
                photo_img = photo_img.resize((max_text_width, int(photo_img.height * scale)), Image.Resampling.LANCZOS)
            if photo_img.height > 600:
                scale = 600 / photo_img.height
                photo_img = photo_img.resize((int(photo_img.width * scale), 600), Image.Resampling.LANCZOS)
            
            mask = Image.new("L", photo_img.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, photo_img.width, photo_img.height), radius=16, fill=255)
            photo_img.putalpha(mask)
            
            photo_h = photo_img.height + (20 if text else 0)

        name_bbox = font_name.getbbox(name)
        name_h = name_bbox[3] - name_bbox[1]

        card_height = max(avatar_size, name_h + 16 + text_h + photo_h) + pad * 2
        card = Image.new("RGB", (card_width, card_height), (255, 255, 255))
        draw = ImageDraw.Draw(card)

        card.paste(avatar_img, (pad, pad), avatar_img)
        draw.text((text_x, pad), name, font=font_name, fill=(120, 120, 120))

        current_y = pad + name_h + 16
        if text:
            for line in lines:
                draw.text((text_x, current_y), line, font=font_text, fill=(20, 20, 20))
                current_y += line_h

        if photo_img:
            if text:
                current_y += 20
            card.paste(photo_img, (text_x, current_y), photo_img)

        return card

    @loader.command()
    async def ramka(self, message):
        """- реплай на фото, чтобы вставить его в рамку"""
        reply = await message.get_reply_message()

        if not reply or not reply.photo:
            return await utils.answer(message, self.strings["no_reply_photo"])

        m = await utils.answer(message, self.strings["processing"])

        frame_bytes = await self.fetch_bytes(self.frame_photo_url)
        if not frame_bytes:
            return await utils.answer(message, self.strings["download_error"])

        photo_bytes = await reply.download_media(bytes)

        try:
            frame_img = Image.open(io.BytesIO(frame_bytes)).convert("RGBA")
            bg_color = frame_img.getpixel((0, 0))
            if bg_color[3] != 0:
                data = frame_img.getdata()
                new_data = [(0, 0, 0, 0) if item == bg_color else item for item in data]
                frame_img.putdata(new_data)

            fw, fh = frame_img.size
            user_img = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")

            user_img_stretched = user_img.resize(
                (fw - int(fw * 0.16) - int(fw * 0.16), fh - int(fh * 0.16) - int(fh * 0.15)), 
                Image.Resampling.LANCZOS
            )

            result_img = Image.new("RGBA", (fw, fh), (0, 0, 0, 255))
            result_img.paste(user_img_stretched, (int(fw * 0.16) + 20, int(fh * 0.16)))
            result_img.paste(frame_img, (0, 0), frame_img)

            output = io.BytesIO()
            result_img.save(output, format="PNG")
            output.seek(0)
            output.name = "framed_photo.png"

            await self.client.send_file(
                message.peer_id, 
                file=output,
                reply_to=reply.id
            )
            
            await m.delete()

        except Exception as e:
            logger.error(f"Error in Ramka: {e}")
            await utils.answer(message, self.strings["process_error"].format(str(e)))

    @loader.command()
    async def ramkamsg(self, message):
        # by https://t.me/exteraPluginsSup/904
        """[цифра]* - реплай на сообщение(-ия), чтобы вставить его в рамку. * - необязательный парамет. Можно написать число и будут взяты сообщения выше реплайнутного."""
        reply = await message.get_reply_message()
        if not reply:
            return await utils.answer(message, self.strings["no_reply_msg"])

        args = utils.get_args_raw(message)
        count = 0
        if args and args.isdigit():
            count = int(args)

        m = await utils.answer(message, self.strings["processing"])

        frame_bytes = await self.fetch_bytes(self.frame_msg_url)
        font_bytes = await self.fetch_bytes(self.font_url)
        
        if not frame_bytes or not font_bytes:
            return await utils.answer(message, self.strings["download_error"])

        try:
            msgs = await self.client.get_messages(message.peer_id, offset_id=reply.id + 1, limit=count + 1)
            msgs.reverse()

            blocks = []
            avatars_cache = {}

            for msg in msgs:
                sender = await msg.get_sender()
                if sender:
                    first = getattr(sender, "first_name", "") or ""
                    last = getattr(sender, "last_name", "") or ""
                    name = f"{first} {last}".strip()
                    if not name:
                        name = getattr(sender, "title", "Аноним")
                    sender_id = sender.id
                else:
                    name = "Аноним"
                    sender_id = 0

                photo_bytes = None
                if msg.photo:
                    try:
                        photo_bytes = await self.client.download_media(msg, file=bytes)
                    except Exception:
                        pass

                photo_img = None
                if photo_bytes:
                    try:
                        photo_img = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
                    except Exception:
                        pass

                text = msg.message if msg.message else ""
                if not text and not photo_img:
                    text = "[медиа]"
                
                if sender_id not in avatars_cache:
                    avatar_bytes = None
                    if sender:
                        try:
                            avatar_bytes = await self.client.download_profile_photo(sender, file=bytes)
                        except Exception:
                            pass
                    avatars_cache[sender_id] = self._create_avatar(avatar_bytes, name, font_bytes)

                avatar_img = avatars_cache[sender_id]
                blocks.append(self._create_message_card(avatar_img, name, text, font_bytes, photo_img))

            pad = 40

            if len(blocks) == 1:
                card = blocks[0]
            else:
                max_w = max(b.width for b in blocks)
                total_h = sum(b.height for b in blocks) + pad * (len(blocks) + 1)
                card = Image.new("RGB", (max_w, total_h), (255, 255, 255))
                
                y = pad
                for b in blocks:
                    card.paste(b, (0, y))
                    y += b.height + pad

            frame_img = Image.open(io.BytesIO(frame_bytes)).convert("RGBA")
            box = self._punch_hole(frame_img)
            left, top, right, bottom = box
            inner_w = right - left
            inner_h = bottom - top

            MAX_ASPECT_DISTORTION = 1.35
            target_ratio = inner_w / inner_h
            card_w, card_h = card.size
            card_ratio = card_w / card_h

            padded_card = card
            if card_ratio > target_ratio * MAX_ASPECT_DISTORTION:
                wanted_h = int(card_w / (target_ratio * MAX_ASPECT_DISTORTION))
                extra = max(0, wanted_h - card_h)
                padded_card = Image.new("RGB", (card_w, card_h + extra), (255, 255, 255))
                padded_card.paste(card, (0, 0))
            elif card_ratio < target_ratio / MAX_ASPECT_DISTORTION:
                wanted_w = int(card_h * target_ratio / MAX_ASPECT_DISTORTION)
                extra = max(0, wanted_w - card_w)
                padded_card = Image.new("RGB", (card_w + extra, card_h), (255, 255, 255))
                padded_card.paste(card, (0, 0))

            resized_card = padded_card.resize((inner_w, inner_h), Image.Resampling.LANCZOS)
            
            fw, fh = frame_img.size
            result_img = Image.new("RGBA", (fw, fh), (0, 0, 0, 255))
            result_img.paste(resized_card, (left, top))
            result_img.alpha_composite(frame_img)

            output = io.BytesIO()
            result_img.convert("RGB").save(output, format="JPEG", quality=95)
            output.seek(0)
            output.name = "framed_messages.jpg"

            await self.client.send_file(
                message.peer_id, 
                file=output,
                reply_to=reply.id
            )
            
            await m.delete()

        except Exception as e:
            logger.error(f"Error in Ramka: {e}")
            await utils.answer(message, self.strings["process_error"].format(str(e)))
