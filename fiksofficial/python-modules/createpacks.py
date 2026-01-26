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
# meta fhsdesc: tool, tools, fun, packs
# requires: opencv-python pillow

import os
import shutil
import cv2
import random
import string
import asyncio
import logging
from PIL import Image, UnidentifiedImageError

from telethon.tl.functions.stickers import CreateStickerSetRequest
from telethon.tl.types import InputStickerSetItem, InputDocument
from telethon.errors.rpcerrorlist import PackShortNameOccupiedError

from .. import loader, utils
from telethon.tl.functions.photos import GetUserPhotosRequest


try:
    resample = Image.Resampling.LANCZOS
except AttributeError:
    resample = Image.LANCZOS

logger = logging.getLogger(__name__)



async def process_to_webp(input_path: str, output_path: str, size: int = 512) -> bool:
    try:
        is_video = input_path.lower().endswith(('.mp4', '.webm', '.mov')) or b'ftyp' in open(input_path, 'rb').read(32)
        if is_video:
            cap = cv2.VideoCapture(input_path)
            success, frame = cap.read()
            cap.release()
            if not success:
                logger.warning(f"Video: Unable to read frame {input_path}")
                return False
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA))
        else:
            try:
                img = Image.open(input_path).convert("RGBA")
            except UnidentifiedImageError:
                logger.warning(f"Image: incorrect {input_path}")
                return False

        img.thumbnail((size, size), resample)
        final = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        w, h = img.size
        final.paste(img, ((size - w) // 2, (size - h) // 2))

        final.save(output_path, "WEBP", quality=95, method=6)

        try:
            check = Image.open(output_path)
            if check.size != (size, size):
                logger.warning(f"WEBP: size not {size}x{size}: {check.size}")
                return False
            if os.path.getsize(output_path) > 512 * 1024:
                final.save(output_path, "WEBP", quality=80, method=6)
                if os.path.getsize(output_path) > 512 * 1024:
                    return False
        except Exception as e:
            logger.error(f"WEBP: verification error {output_path}: {e}")
            return False

        return True
    except Exception as e:
        logger.error(f"WEBP: processing error {input_path}: {e}")
        return False



async def process_to_png(input_path: str, output_path: str, size: int = 100) -> bool:
    try:
        is_video = input_path.lower().endswith(('.mp4', '.webm', '.mov')) or b'ftyp' in open(input_path, 'rb').read(32)
        if is_video:
            cap = cv2.VideoCapture(input_path)
            success, frame = cap.read()
            cap.release()
            if not success:
                logger.warning(f"Video: Unable to read frame {input_path}")
                return False
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA))
        else:
            try:
                img = Image.open(input_path).convert("RGBA")
            except UnidentifiedImageError:
                logger.warning(f"Image: incorrect {input_path}")
                return False

        img.thumbnail((size, size), resample)
        final = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        w, h = img.size
        final.paste(img, ((size - w) // 2, (size - h) // 2))

        final.save(output_path, "PNG")  

        try:
            check = Image.open(output_path)
            if check.size != (size, size):
                logger.warning(f"PNG: size not {size}x{size}: {check.size}")
                return False
            if os.path.getsize(output_path) > 512 * 1024:
                logger.warning(f"PNG: file >512KB: {os.path.getsize(output_path)}")
                return False
        except Exception as e:
            logger.error(f"PNG: verification error {output_path}: {e}")
            return False

        return True
    except Exception as e:
        logger.error(f"PNG: processing error {input_path}: {e}")  
        return False


@loader.tds
class CreatePacks(loader.Module):
    """Creates sticker packs and emoji packs from the avatars of chat participants"""
    
    strings = {
        "name": "CreatePacks",
        "processing": "<b>[CreatePacks]</b> Collecting avatars of participants...",
        "no_avatars": "<b>[CreatePacks]</b> No members with avatars",
        "no_valid": "<b>[CreatePacks]</b> Could not process any avatars",
        "done_pack": "<b>[CreatePacks]</b> Sticker pack is ready:\n<b>[CreatePacks]</b> Open: <a href='https://t.me/addstickers/{}'>here</a>",
        "done_emoji_pack": "<b>[CreatePacks]</b> Emoji pack is ready:\n<b>[CreatePacks]</b> Open: <a href='https://t.me/addstickers/{}'>here</a>",
        "already": "<b>[CreatePacks]</b> A sticker pack with this name already exists.",
        "emoji_processing": "<b>[CreatePacks]</b> Creating emoji pack from avatars...",
        "emoji_no_emoji": "<b>[CreatePacks]</b> No emoji specified — using",
    }

    strings_ru = {
        "_cls_doc": "Создаёт стикерпаки и эмодзи-паки из аватаров участников чата",
        "processing": "<b>[CreatePacks]</b> Собираю аватарки участников...",
        "no_avatars": "<b>[CreatePacks]</b> Нет участников с аватарками",
        "no_valid": "<b>[CreatePacks]</b> Не удалось обработать ни одну аватарку",
        "done_pack": "<b>[CreatePacks]</b> Стикерпак готов:\n<b>[CreatePacks]</b> Открыть: <a href='https://t.me/addstickers/{}'>здесь</a>",
        "done_emoji_pack": "<b>[CreatePacks]</b> Эмодзи-пак готов:\n<b>[CreatePacks]</b> Открыть: <a href='https://t.me/addstickers/{}'>здесь</a>",
        "already": "<b>[CreatePacks]</b> Стикерпак с таким именем уже существует",
        "emoji_processing": "<b>[CreatePacks]</b> Создаю эмодзи-пак из аватаров...",
        "emoji_no_emoji": "<b>[CreatePacks]</b> Эмодзи не указан — используется",
    }

    async def _get_avatar_files(self, message, format: str = "webp", size: int = 512) -> tuple[list[str], str]:
        chat = await message.get_chat()
        cid = abs(message.chat_id)
        tmp_dir = f"/tmp/avatars_{cid}_{random.randint(1000, 9999)}"
        os.makedirs(tmp_dir, exist_ok=True)

        users = []
        async for u in self._client.iter_participants(chat.id):
            if u.photo:
                users.append(u)
                if len(users) >= 100:
                    break

        if not users:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return [], tmp_dir

        processed = []
        process_func = process_to_webp if format == "webp" else process_to_png

        for u in users:
            try:
                photos = await self._client(GetUserPhotosRequest(u.id, 0, 0, 1))
                if not photos.photos:
                    continue

                raw_path = os.path.join(tmp_dir, f"{u.id}_raw")
                raw = await self._client.download_media(photos.photos[0], file=raw_path)

                ext = ".webp" if format == "webp" else ".png"
                output_path = os.path.join(tmp_dir, f"{u.id}{ext}")
                success = False

                if isinstance(raw, str):
                    success = await process_func(raw, output_path, size=size)
                    if os.path.exists(raw):
                        os.unlink(raw)
                else:
                    temp_raw = os.path.join(tmp_dir, f"{u.id}_temp_raw")
                    with open(temp_raw, "wb") as f:
                        f.write(raw)
                    success = await process_func(temp_raw, output_path, size=size)
                    if os.path.exists(temp_raw):
                        os.unlink(temp_raw)

                if success:
                    try:
                        img_size = Image.open(output_path).size
                        if img_size != (size, size):
                            logger.warning(f"{format.upper()}: size not {size}x{size}: {img_size}")
                            os.unlink(output_path)
                            continue
                        if os.path.getsize(output_path) > 512 * 1024:
                            logger.warning(f"{format.upper()}: file >512KB: {os.path.getsize(output_path)}")
                            os.unlink(output_path)
                            continue
                        processed.append(output_path)
                    except Exception as e:
                        logger.error(f"{format.upper()}: verification error {output_path}: {e}")
                else:
                    logger.warning(f"{format.upper()}: Failed to process avatar {u.id}")

            except Exception as e:
                logger.error(f"User processing error {u.id}: {e}")
                continue

        return processed, tmp_dir

    @loader.command(
        ru_doc="- Создать стикерпак из аватаров в группе",
        only_groups=True
    )
    async def createavatars(self, message):
        """- Create a sticker pack from avatars in a group"""
        await message.edit(self.strings("processing"))

        files, tmp_dir = await self._get_avatar_files(message, format="webp", size=512)
        if not files:
            return await message.edit(self.strings("no_avatars"))

        tag = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        short_name = f"f{abs(message.chat_id)}_{tag}_by_fcreateavatars"
        title = f"AvaPack {tag}"

        stickers = []
        for path in files:
            try:
                await asyncio.sleep(0.3)
                file = await self._client.upload_file(path)
                msg = await self._client.send_file("me", file, force_document=True)  
                doc = msg.document
                await self._client.delete_messages("me", msg.id)
                stickers.append(InputStickerSetItem(
                    document=InputDocument(doc.id, doc.access_hash, doc.file_reference),
                    emoji="🖼️"
                ))
            except Exception as e:
                logger.error(f"Sticker loading error {path}: {e}")
                continue

        if not stickers:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return await message.edit(self.strings("no_valid"))

        try:
            await self._client(CreateStickerSetRequest(
                user_id="me",
                title=title,
                short_name=short_name,
                stickers=stickers
            ))
            await message.edit(self.strings("done_pack").format(short_name))
        except PackShortNameOccupiedError:
            await message.edit(self.strings("already"))
        except Exception as e:
            error_details = f"❌ Ошибка создания стикерпака:\n<code>{type(e).__name__}: {e}</code>\n"
            error_details += f"Пак: {short_name}\nСтикеров: {len(stickers)}\n"
            if files:
                error_details += f"Последний файл: {files[-1]}\n"
                try:
                    error_details += f"Размер: {Image.open(files[-1]).size}\n"
                    error_details += f"Вес: {os.path.getsize(files[-1])} байт"
                except:
                    pass
            await message.edit(error_details)
            logger.exception("Error creating sticker pack")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    @loader.command(
        ru_doc="[эмодзи] - Создать эмодзи-пак из всех аватаров",
        only_groups=True
    )
    async def createemojis(self, message):
        """[emoji] - Create an emoji pack from all avatars"""
        args = utils.get_args_raw(message)
        emoji = args.strip() if args else "🖼️"
        if not args:
            await message.edit(self.strings("emoji_no_emoji") + f" `{emoji}`")
            await asyncio.sleep(1.5)

        await message.edit(self.strings("emoji_processing"))

        files, tmp_dir = await self._get_avatar_files(message, format="png", size=100)
        if not files:
            return await message.edit(self.strings("no_avatars"))

        tag = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        short_name = f"f{abs(message.chat_id)}_{tag}_by_fcreateemojis"
        title = f"EmojiPack {tag}"

        stickers = []
        for path in files:
            try:
                await asyncio.sleep(0.3)
                file = await self._client.upload_file(path)
                msg = await self._client.send_file("me", file, force_document=True)  
                doc = msg.document
                await self._client.delete_messages("me", msg.id)
                stickers.append(InputStickerSetItem(
                    document=InputDocument(doc.id, doc.access_hash, doc.file_reference),
                    emoji=emoji
                ))
            except Exception as e:
                logger.error(f"Error loading emoji {path}: {e}")
                continue

        if not stickers:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return await message.edit(self.strings("no_valid"))

        try:
            await self._client(CreateStickerSetRequest(
                user_id="me",
                title=title,
                short_name=short_name,
                stickers=stickers,
                emojis=True
            ))
            await message.edit(self.strings("done_emoji_pack").format(short_name))
        except PackShortNameOccupiedError:
            await message.edit(self.strings("already"))
        except Exception as e:
            error_details = f"❌ Ошибка создания эмодзи-пака:\n<code>{type(e).__name__}: {e}</code>\n"
            error_details += f"Пак: {short_name}\nСмайликов: {len(stickers)}\n"
            if files:
                error_details += f"Последний файл: {files[-1]}\n"
                try:
                    error_details += f"Размер: {Image.open(files[-1]).size}\n"
                    error_details += f"Вес: {os.path.getsize(files[-1])} байт"
                except:
                    pass
            await message.edit(error_details)
            logger.exception("Error creating emoji pack")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)