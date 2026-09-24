__version__ = (1, 0, 0)
# ░░░███░███░███░███░███
# ░░░░░█░█░░░░█░░█░░░█░█
# ░░░░█░░███░░█░░█░█░█░█
# ░░░█░░░█░░░░█░░█░█░█░█
# ░░░███░███░░█░░███░███

# meta developer: @nullmod
# packages: ffmpeg

import asyncio
import base64
import io
import os
import tempfile

from PIL import Image, ImageChops, ImageStat
from telethon.tl.custom import Message
from telethon.tl.types import DocumentAttributeVideo

from .. import loader, utils

BUBBLE_B64 = (
    "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"
)


DEFAULT_GIF_DURATION = 1
DEFAULT_COVERAGE_PERCENT = 30


def _make_bubble(
    cutout: Image.Image, base: Image.Image, width: int, height: int, coverage_percent: int
) -> Image.Image:
    bh = max(1, height * coverage_percent // 100)
    interior = cutout.resize((width, bh), Image.LANCZOS).split()[-1]

    region = base.convert("L").crop((0, 0, width, bh))
    weighted = ImageChops.multiply(region, interior)
    weight_sum = ImageStat.Stat(interior).sum[0]
    avg_luma = (
        ImageStat.Stat(weighted).sum[0] * 255.0 / weight_sum if weight_sum else 255.0
    )

    color = (255, 255, 255) if avg_luma < 128 else (0, 0, 0)
    bubble = Image.new("RGBA", (width, bh), color + (0,))
    bubble.putalpha(interior)
    return bubble


async def _get_media(message: Message):
    reply = await message.get_reply_message()
    for m in ((reply, message) if reply else (message,)):
        if not m:
            continue
        if m.video or m.gif:
            return m, "video"
        if m.photo or (
            m.document and "image/" in (getattr(m.document, "mime_type", "") or "")
        ):
            return m, "photo"
    return None, None


async def _run(*args, timeout: int = 120) -> bytes:
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        raise RuntimeError("ffmpeg timeout")

    if proc.returncode != 0:
        raise RuntimeError(stderr.decode(errors="ignore")[-2000:])

    return stdout


async def _process_photo(m: Message, cutout: Image.Image, coverage_percent: int) -> io.BytesIO:
    raw = await m.download_media(bytes)
    base = Image.open(io.BytesIO(raw)).convert("RGBA")
    w, h = base.size

    bubble = _make_bubble(cutout, base, w, h, coverage_percent)
    base.alpha_composite(bubble, (0, 0))

    out = io.BytesIO()
    base.save(out, format="PNG")
    out.seek(0)
    out.name = "says.png"
    return out


async def _photo_to_gif(
    m: Message, cutout: Image.Image, duration: int, coverage_percent: int
) -> tuple[bytes, int, int, float]:
    raw = await m.download_media(bytes)
    base = Image.open(io.BytesIO(raw)).convert("RGBA")
    w, h = base.size

    bubble = _make_bubble(cutout, base, w, h, coverage_percent)
    base.alpha_composite(bubble, (0, 0))
    base = base.convert("RGB")
    ew, eh = w - w % 2, h - h % 2

    with tempfile.TemporaryDirectory(prefix="gifsays_") as td:
        frame_path = os.path.join(td, "frame.png")
        base.save(frame_path)

        out_path = os.path.join(td, "out.mp4")

        await _run(
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            frame_path,
            "-t",
            str(duration),
            "-vf",
            f"scale={ew}:{eh},fps=25,format=yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-movflags",
            "+faststart",
            "-an",
            out_path,
        )

        with open(out_path, "rb") as f:
            data = f.read()

    return data, ew, eh, float(duration)


async def _process_video(
    m: Message, cutout: Image.Image, force_gif: bool, coverage_percent: int
) -> tuple[bytes, int, int, float]:
    with tempfile.TemporaryDirectory(prefix="gifsays_") as td:
        in_path = os.path.join(td, "in.mp4")
        await m.download_media(in_path)

        frame_path = os.path.join(td, "frame.png")
        await _run("ffmpeg", "-y", "-i", in_path, "-vframes", "1", frame_path)
        frame = Image.open(frame_path).convert("RGB")
        w, h = frame.size
        ew, eh = w - w % 2, h - h % 2

        bubble = _make_bubble(cutout, frame, ew, eh, coverage_percent)
        bubble_path = os.path.join(td, "bubble.png")
        bubble.save(bubble_path)

        has_audio = bool(
            (
                await _run(
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "a",
                    "-show_entries",
                    "stream=index",
                    "-of",
                    "csv=p=0",
                    in_path,
                )
            ).strip()
        )

        duration = float(
            (
                await _run(
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "csv=p=0",
                    in_path,
                )
            ).strip()
            or 0
        )

        out_path = os.path.join(td, "out.mp4")
        filter_complex = f"[0:v]scale={ew}:{eh}[base];[base][1:v]overlay=0:0[v]"
        base_args = [
            "ffmpeg",
            "-y",
            "-i",
            in_path,
            "-i",
            bubble_path,
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
        ]
        tail_args = [
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            out_path,
        ]

        keep_audio = has_audio and not force_gif
        try:
            await _run(
                *base_args,
                *(["-map", "0:a", "-c:a", "copy"] if keep_audio else ["-an"]),
                *tail_args,
            )
        except RuntimeError:
            if not keep_audio:
                raise
            await _run(*base_args, "-an", *tail_args)

        if not os.path.exists(out_path) or not os.path.getsize(out_path):
            raise RuntimeError("ffmpeg produced empty output")

        with open(out_path, "rb") as f:
            data = f.read()

    return data, ew, eh, duration


class GifSays(loader.Module):
    """Наложение спич пузыря на фото/видео/гиф"""

    strings = {
        "name": "GifSays",
        "no_media": "<emoji document_id=5019523782004441717>❌</emoji> Reply to a photo, gif or video!",
        "processing": "<emoji document_id=5886667040432853038>🔁</emoji> Processing...",
        "error": "<emoji document_id=5019523782004441717>❌</emoji> Error: {}",
    }
    strings_ru = {
        "no_media": "<emoji document_id=5019523782004441717>❌</emoji> Ответьте на фото, гифку или видео!",
        "processing": "<emoji document_id=5886667040432853038>🔁</emoji> Обрабатываю...",
        "error": "<emoji document_id=5019523782004441717>❌</emoji> Ошибка: {}",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "coverage",
                DEFAULT_COVERAGE_PERCENT,
                "Какую часть высоты медиа в процентах занимает пузырь",
                validator=loader.validators.Integer(minimum=5, maximum=100),
            ),
        )

    async def client_ready(self):
        self._cutout = Image.open(io.BytesIO(base64.b64decode(BUBBLE_B64))).convert(
            "RGBA"
        )

    async def _handle(self, message: Message, force_gif: bool):
        m, kind = await _get_media(message)
        if not m:
            return await utils.answer(message, self.strings["no_media"])

        await utils.answer(message, self.strings["processing"])

        coverage = self.config["coverage"]

        try:
            if kind == "photo" and not force_gif:
                result = await _process_photo(m, self._cutout, coverage)
                await utils.answer(message, "", file=result, force_document=False)
                return

            if kind == "photo":
                data, w, h, duration = await _photo_to_gif(
                    m, self._cutout, DEFAULT_GIF_DURATION, coverage
                )
            else:
                data, w, h, duration = await _process_video(
                    m, self._cutout, force_gif, coverage
                )

            file = io.BytesIO(data)
            file.name = "says.mp4"
            await utils.answer(
                message,
                "",
                file=file,
                force_document=False,
                attributes=[
                    DocumentAttributeVideo(
                        duration=duration,
                        w=w,
                        h=h,
                        supports_streaming=True,
                    ),
                ],
            )
        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))

    @loader.command(
        ru_doc="[reply на фото/гиф/видео] - наложить пузырь. вернёт медиа того же типа"
    )
    async def says(self, message: Message):
        """[reply to photo/gif/video] - overlay a speech bubble. returns the same media type"""
        await self._handle(message, force_gif=False)

    @loader.command(
        ru_doc="[reply на фото/гиф/видео] - наложить пузырь. вернёт результат как гифку"
    )
    async def saysg(self, message: Message):
        """[reply to photo/gif/video] - overlay a speech bubble. returns the result as a gif"""
        await self._handle(message, force_gif=True)
