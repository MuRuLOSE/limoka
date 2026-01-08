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
# Name: MediaTools
# Description: Powerful tools for working with media files
# Author: @hikka_mods
# ---------------------------------------------------------------------------------
# meta developer: @hikka_mods
# scope: MediaTools
# scope: MediaTools 0.0.1
# ---------------------------------------------------------------------------------

import asyncio
import logging
import math
import os
import re
import shutil
from typing import Optional

from telethon.types import Message

from .. import loader, utils

logger = logging.getLogger(__name__)

def check_ffmpeg():
    return shutil.which("ffmpeg") is not None


@loader.tds
class MediaToolsMod(loader.Module):
    """Powerful tools for working with media files"""

    strings = {
        "name": "MediaTools",
        "no_reply": "🚫 Reply to a media file!",
        "no_ffmpeg": "❌ FFmpeg is not installed! Install: apt-get install ffmpeg",
        "processing": "⚙️ Processing...",
        "converted": "✅ Converted to {}",
        "downloaded": "✅ Voice message saved",
        "gif_created": "✅ GIF created",
        "cut_done": "✅ Trimmed",
        "circle_done": "✅ Video circle created",
        "audio_extracted": "✅ Audio extracted",
        "compressed": "✅ Compressed to {}",
        "split_done": "✅ Split into {} parts",
        "merged": "✅ Merged",
        "metadata_removed": "✅ Metadata removed",
        "invalid_args": "❌ Invalid arguments",
        "error": "❌ Error: {}",
        "available_formats": "Available formats:\n🎵 Audio: mp3, flac, wav, aac, ogg, m4a, opus\n🎬 Video: mp4, avi, mkv, mov, wmv, flv, webm, 3gp, hevc, h264",
        "cut_usage": "Usage: .cut 20s6ms:8m16s3ms",
        "compress_usage": "Available qualities: 144p, 240p, 360p, 480p, 720p, 1080p, 1440p, 2160p",
        "split_time_usage": "Example: .split 10m (10 minutes)",
        "split_size_usage": "Usage: .split 10m or .split 5MB",
        "merge_usage": "Reply to first video/audio",
        "min_files": "Need at least 2 media files in chain",
        "downloading": "Downloading {} files...",
        "part": "Part {}/{}",
    }

    strings_ru = {
        "no_reply": "🚫 Ответьте на медиафайл!",
        "no_ffmpeg": "❌ FFmpeg не установлен! Установите: apt-get install ffmpeg",
        "processing": "⚙️ Обрабатываю...",
        "converted": "✅ Конвертировано в {}",
        "downloaded": "✅ Голосовое сохранено",
        "gif_created": "✅ GIF создан",
        "cut_done": "✅ Обрезано",
        "circle_done": "✅ Видео в кружок",
        "audio_extracted": "✅ Аудио извлечено",
        "compressed": "✅ Сжато до {}",
        "split_done": "✅ Разделено на {} частей",
        "merged": "✅ Объединено",
        "metadata_removed": "✅ Метаданные удалены",
        "invalid_args": "❌ Неверные аргументы",
        "error": "❌ Ошибка: {}",
        "available_formats": "Доступные форматы:\n🎵 Аудио: mp3, flac, wav, aac, ogg, m4a, opus\n🎬 Видео: mp4, avi, mkv, mov, wmv, flv, webm, 3gp, hevc, h264",
        "cut_usage": "Используйте: .cut 20с6мс:8м16с3мс",
        "compress_usage": "Доступные качества: 144p, 240p, 360p, 480p, 720p, 1080p, 1440p, 2160p",
        "split_time_usage": "Пример: .split 10m (10 минут)",
        "split_size_usage": "Используйте: .split 10m или .split 5MB",
        "merge_usage": "Ответьте на первое видео/аудио",
        "min_files": "Нужно как минимум 2 медиафайла в цепочке",
        "downloading": "Скачиваю {} файлов...",
        "part": "Часть {}/{}",
    }

    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        if not check_ffmpeg():
            self.logger.warning(self.strings["no_ffmpeg"])

    @loader.command(
        ru_doc="<формат> - конвертировать медиа в указанный формат",
        en_doc="<format> - convert media to specified format",
    )
    async def convert(self, message: Message):
        reply = await message.get_reply_message()
        if not reply or not reply.media:
            return await utils.answer(message, self.strings["no_reply"])

        if not check_ffmpeg():
            return await utils.answer(message, self.strings["no_ffmpeg"])

        args = utils.get_args_raw(message).lower()
        formats = {
            "mp3": "audio",
            "flac": "audio",
            "wav": "audio",
            "aac": "audio",
            "ogg": "audio",
            "m4a": "audio",
            "opus": "audio",
            "mp4": "video",
            "avi": "video",
            "mkv": "video",
            "mov": "video",
            "wmv": "video",
            "flv": "video",
            "webm": "video",
            "3gp": "video",
            "hevc": "video",
            "h264": "video",
        }

        if not args or args not in formats:
            return await utils.answer(message, self.strings["available_formats"])

        msg = await utils.answer(message, self.strings["processing"])

        try:
            file = await reply.download_media(file="temp/")
            output = f"{file.rsplit('.', 1)[0]}_converted.{args}"

            cmd = ["ffmpeg", "-i", file, "-y"]
            if formats[args] == "audio":
                if args == "mp3":
                    cmd.extend(["-codec:a", "libmp3lame", "-q:a", "2"])
                elif args == "flac":
                    cmd.extend(["-codec:a", "flac", "-compression_level", "12"])
                elif args == "opus":
                    cmd.extend(["-codec:a", "libopus", "-b:a", "128k"])
                elif args == "aac":
                    cmd.extend(["-codec:a", "aac", "-b:a", "192k"])
            elif formats[args] == "video":
                if args in ["hevc", "h264"]:
                    codec = "libx265" if args == "hevc" else "libx264"
                    cmd.extend(["-codec:v", codec, "-preset", "medium", "-crf", "23"])
                if args == "webm":
                    cmd.extend(["-codec:v", "libvpx-vp9", "-b:v", "1M"])

            cmd.append(output)

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()

            await message.client.send_file(
                message.peer_id,
                output,
                caption=self.strings["converted"].format(args),
                reply_to=reply.id,
            )

            os.remove(file)
            if os.path.exists(output):
                os.remove(output)

            await msg.delete()

        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))

    @loader.command(
        ru_doc="Скачать голосовое сообщение как файл",
        en_doc="Download voice message as file",
    )
    async def voicedl(self, message: Message):
        reply = await message.get_reply_message()
        if not reply or not reply.voice:
            return await utils.answer(message, self.strings["no_reply"])

        msg = await utils.answer(message, self.strings["processing"])

        try:
            file = await reply.download_media(file="temp/voice.ogg")
            new_file = file.replace(".ogg", ".opus")
            os.rename(file, new_file)

            await message.client.send_file(
                message.peer_id,
                new_file,
                caption=self.strings["downloaded"],
                reply_to=reply.id,
                voice_note=False,
            )

            os.remove(new_file)
            await msg.delete()

        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))

    @loader.command(ru_doc="Преобразовать видео в GIF", en_doc="Convert video to GIF")
    async def gif(self, message: Message):
        if not check_ffmpeg():
            return await utils.answer(message, self.strings["no_ffmpeg"])

        reply = await message.get_reply_message()
        if not reply or not reply.video:
            return await utils.answer(message, self.strings["no_reply"])

        msg = await utils.answer(message, self.strings["processing"])

        try:
            file = await reply.download_media(file="temp/")
            output = f"{file.rsplit('.', 1)[0]}.gif"

            cmd = [
                "ffmpeg",
                "-i",
                file,
                "-vf",
                "fps=10,scale=480:-1:flags=lanczos",
                "-gifflags",
                "+transdiff",
                "-y",
                output,
            ]

            process = await asyncio.create_subprocess_exec(*cmd)
            await process.communicate()

            await message.client.send_file(
                message.peer_id,
                output,
                caption=self.strings["gif_created"],
                reply_to=reply.id,
            )

            os.remove(file)
            os.remove(output)
            await msg.delete()

        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))

    def parse_time(self, time_str: str) -> Optional[float]:
        time_str = time_str.lower()
        total = 0
        pattern = r"(\d+\.?\d*)([мm]?[сc]|[мm][сc]?)"
        matches = re.findall(pattern, time_str)

        for value, unit in matches:
            value = float(value)
            if "м" in unit or "m" in unit:
                total += value * 60
            elif "с" in unit or "c" in unit:
                total += value

        return total if total > 0 else None

    @loader.command(
        ru_doc="<начало:конец> - обрезать медиа по времени",
        en_doc="<start:end> - trim media by time",
    )
    async def cut(self, message: Message):
        if not check_ffmpeg():
            return await utils.answer(message, self.strings["no_ffmpeg"])

        reply = await message.get_reply_message()
        if not reply or not reply.media:
            return await utils.answer(message, self.strings["no_reply"])

        args = utils.get_args_raw(message)
        if not args or ":" not in args:
            return await utils.answer(message, self.strings["cut_usage"])

        start_str, end_str = args.split(":", 1)
        start = self.parse_time(start_str)
        end = self.parse_time(end_str)

        if start is None or end is None or start >= end:
            return await utils.answer(message, self.strings["invalid_args"])

        msg = await utils.answer(message, self.strings["processing"])

        try:
            file = await reply.download_media(file="temp/")
            output = f"{file.rsplit('.', 1)[0]}_cut.{file.rsplit('.', 1)[1]}"

            cmd = [
                "ffmpeg",
                "-i",
                file,
                "-ss",
                str(start),
                "-to",
                str(end),
                "-c",
                "copy",
                "-avoid_negative_ts",
                "make_zero",
                "-y",
                output,
            ]

            process = await asyncio.create_subprocess_exec(*cmd)
            await process.communicate()

            await message.client.send_file(
                message.peer_id,
                output,
                caption=self.strings["cut_done"],
                reply_to=reply.id,
            )

            os.remove(file)
            os.remove(output)
            await msg.delete()

        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))

    @loader.command(
        ru_doc="[начало:конец] - Видео в кружок",
        en_doc="[start:end] - Convert video to circle",
    )
    async def vircle(self, message: Message):
        if not check_ffmpeg():
            return await utils.answer(message, self.strings["no_ffmpeg"])

        reply = await message.get_reply_message()
        if not reply or not (reply.video or reply.gif):
            return await utils.answer(message, self.strings["no_reply"])

        args = utils.get_args_raw(message)
        filter_args = ""

        if args and ":" in args:
            start_str, end_str = args.split(":", 1)
            start = self.parse_time(start_str)
            end = self.parse_time(end_str)

            if start is not None and end is not None and start < end:
                filter_args = f",trim=start={start}:end={end},setpts=PTS-STARTPTS"

        msg = await utils.answer(message, self.strings["processing"])

        try:
            file = await reply.download_media(file="temp/")
            output = f"{file.rsplit('.', 1)[0]}_circle.mp4"

            cmd = [
                "ffmpeg",
                "-i",
                file,
                "-vf",
                f"scale=720:720:force_original_aspect_ratio=increase,crop=720:720{filter_args},format=rgba,geq='if(gt(X,360),if(gt(Y,360),if(lt(sqrt((X-360)^2+(Y-360)^2),360),p(X,Y),0),0),0)'",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-y",
                output,
            ]

            process = await asyncio.create_subprocess_exec(*cmd)
            await process.communicate()

            await message.client.send_file(
                message.peer_id,
                output,
                caption=self.strings["circle_done"],
                reply_to=reply.id,
                video_note=True,
            )

            os.remove(file)
            os.remove(output)
            await msg.delete()

        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))

    @loader.command(
        ru_doc="[начало:конец] - Извлечь аудио из видео",
        en_doc="[start:end] - Extract audio from video",
    )
    async def vsound(self, message: Message):
        if not check_ffmpeg():
            return await utils.answer(message, self.strings["no_ffmpeg"])

        reply = await message.get_reply_message()
        if not reply or not reply.video:
            return await utils.answer(message, self.strings["no_reply"])

        args = utils.get_args_raw(message)
        msg = await utils.answer(message, self.strings["processing"])

        try:
            file = await reply.download_media(file="temp/")
            output = f"{file.rsplit('.', 1)[0]}_audio.mp3"

            cmd = ["ffmpeg", "-i", file]
            if args and ":" in args:
                start_str, end_str = args.split(":", 1)
                start = self.parse_time(start_str)
                end = self.parse_time(end_str)

                if start is not None and end is not None and start < end:
                    cmd.extend(["-ss", str(start), "-to", str(end)])

            cmd.extend(["-q:a", "2", "-map", "a", "-y", output])

            process = await asyncio.create_subprocess_exec(*cmd)
            await process.communicate()

            await message.client.send_file(
                message.peer_id,
                output,
                caption=self.strings["audio_extracted"],
                reply_to=reply.id,
            )

            os.remove(file)
            os.remove(output)
            await msg.delete()

        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))

    @loader.command(
        ru_doc="<качество> - Сжать видео", en_doc="<quality> - Compress video"
    )
    async def compress(self, message: Message):
        if not check_ffmpeg():
            return await utils.answer(message, self.strings["no_ffmpeg"])

        reply = await message.get_reply_message()
        if not reply or not reply.video:
            return await utils.answer(message, self.strings["no_reply"])

        args = utils.get_args_raw(message).lower()
        resolutions = {
            "144p": "256x144",
            "240p": "426x240",
            "360p": "640x360",
            "480p": "854x480",
            "720p": "1280x720",
            "1080p": "1920x1080",
            "1440p": "2560x1440",
            "2160p": "3840x2160",
        }

        if not args or args not in resolutions:
            return await utils.answer(message, self.strings["compress_usage"])

        msg = await utils.answer(message, self.strings["processing"])

        try:
            file = await reply.download_media(file="temp/")
            output = f"{file.rsplit('.', 1)[0]}_compressed.mp4"

            probe_cmd = [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=bit_rate",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                file,
            ]

            process = await asyncio.create_subprocess_exec(
                *probe_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()
            original_bitrate = stdout.decode().strip()

            scale_factor = {
                "144p": 0.1,
                "240p": 0.2,
                "360p": 0.3,
                "480p": 0.4,
                "720p": 0.6,
                "1080p": 0.8,
                "1440p": 0.9,
                "2160p": 1.0,
            }

            target_bitrate = "500k"
            if original_bitrate and original_bitrate.isdigit():
                original_br = int(original_bitrate)
                target_br = int(original_br * scale_factor[args] / 1000)
                target_bitrate = f"{max(200, target_br)}k"

            cmd = [
                "ffmpeg",
                "-i",
                file,
                "-vf",
                f"scale={resolutions[args]}:force_original_aspect_ratio=decrease",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-b:v",
                target_bitrate,
                "-maxrate",
                target_bitrate,
                "-bufsize",
                f"{int(target_bitrate[:-1]) * 2}k",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-y",
                output,
            ]

            process = await asyncio.create_subprocess_exec(*cmd)
            await process.communicate()

            await message.client.send_file(
                message.peer_id,
                output,
                caption=self.strings["compressed"].format(args),
                reply_to=reply.id,
            )

            os.remove(file)
            os.remove(output)
            await msg.delete()

        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))

    @loader.command(
        ru_doc="<время/размер> - Разделить медиа на части",
        en_doc="<time/size> - Split media into parts",
    )
    async def split(self, message: Message):
        if not check_ffmpeg():
            return await utils.answer(message, self.strings["no_ffmpeg"])

        reply = await message.get_reply_message()
        if not reply or not reply.media:
            return await utils.answer(message, self.strings["no_reply"])

        args = utils.get_args_raw(message).lower()
        msg = await utils.answer(message, self.strings["processing"])

        try:
            file = await reply.download_media(file="temp/")
            file_ext = file.rsplit(".", 1)[1]

            if "m" in args or "м" in args:
                duration = self.parse_time(args)
                if not duration:
                    await msg.edit(self.strings["split_time_usage"])
                    os.remove(file)
                    return

                probe_cmd = [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    file,
                ]

                process = await asyncio.create_subprocess_exec(
                    *probe_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await process.communicate()
                total_duration = float(stdout.decode().strip())

                parts = math.ceil(total_duration / duration)

                for i in range(parts):
                    start = i * duration
                    end = min((i + 1) * duration, total_duration)
                    output = f"{file.rsplit('.', 1)[0]}_part{i + 1}.{file_ext}"

                    split_cmd = [
                        "ffmpeg",
                        "-i",
                        file,
                        "-ss",
                        str(start),
                        "-to",
                        str(end),
                        "-c",
                        "copy",
                        "-avoid_negative_ts",
                        "make_zero",
                        "-y",
                        output,
                    ]

                    process = await asyncio.create_subprocess_exec(*split_cmd)
                    await process.communicate()

                    await message.client.send_file(
                        message.peer_id,
                        output,
                        caption=self.strings["part"].format(i + 1, parts),
                        reply_to=reply.id if i == 0 else None,
                    )

                    os.remove(output)

                await msg.edit(self.strings["split_done"].format(parts))

            elif "mb" in args or "мб" in args:
                await utils.answer(
                    message, "Size splitting requires additional implementation"
                )
            else:
                await msg.edit(self.strings["split_size_usage"])

            os.remove(file)

        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))

    @loader.command(
        ru_doc="Объединить несколько медиафайлов", en_doc="Merge multiple media files"
    )
    async def merge(self, message: Message):
        if not check_ffmpeg():
            return await utils.answer(message, self.strings["no_ffmpeg"])

        reply = await message.get_reply_message()
        if not reply:
            return await utils.answer(message, self.strings["merge_usage"])

        messages = []
        current = reply

        while current and current.media:
            messages.append(current)
            current = await current.get_reply_message()

        if len(messages) < 2:
            return await utils.answer(message, self.strings["min_files"])

        msg = await utils.answer(
            message, self.strings["downloading"].format(len(messages))
        )

        try:
            files = []
            file_list = "temp/filelist.txt"

            with open(file_list, "w") as f:
                for i, msg_file in enumerate(messages):
                    filename = f"temp/merge_{i}.{msg_file.file.ext if msg_file.file else 'mp4'}"
                    await msg_file.download_media(file=filename)
                    files.append(filename)
                    f.write(f"file '{os.path.abspath(filename)}'\n")

            output = "temp/merged.mp4"

            cmd = [
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                file_list,
                "-c",
                "copy",
                "-y",
                output,
            ]

            process = await asyncio.create_subprocess_exec(*cmd)
            await process.communicate()

            await message.client.send_file(
                message.peer_id,
                output,
                caption=self.strings["merged"],
                reply_to=reply.id,
            )

            for file in files:
                if os.path.exists(file):
                    os.remove(file)
            os.remove(file_list)
            os.remove(output)

            await msg.delete()

        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))

    @loader.command(
        ru_doc="Удалить метаданные из медиа", en_doc="Remove metadata from media"
    )
    async def removemetadata(self, message: Message):
        if not check_ffmpeg():
            return await utils.answer(message, self.strings["no_ffmpeg"])

        reply = await message.get_reply_message()
        if not reply or not reply.media:
            return await utils.answer(message, self.strings["no_reply"])

        msg = await utils.answer(message, self.strings["processing"])

        try:
            file = await reply.download_media(file="temp/")
            file_ext = file.rsplit(".", 1)[1]
            output = f"{file.rsplit('.', 1)[0]}_nometa.{file_ext}"

            cmd = ["ffmpeg", "-i", file, "-map_metadata", "-1", "-y", output]

            process = await asyncio.create_subprocess_exec(*cmd)
            await process.communicate()

            await message.client.send_file(
                message.peer_id,
                output,
                caption=self.strings["metadata_removed"],
                reply_to=reply.id,
            )

            os.remove(file)
            os.remove(output)
            await msg.delete()

        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))
