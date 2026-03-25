
import asyncio
import mimetypes
import os
import subprocess
import time

from .. import loader, utils
from ..inline.types import InlineCall

def detect_type(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    if not mime:
        return "video"
    if mime.startswith("video"):
        return "video"
    if mime.startswith("audio"):
        return "audio"
    if mime.startswith("image"):
        return "image"
    return "video"

TYPE_ICON = {"video": "🎬", "audio": "🎵", "image": "🖼️"}
PRESETS   = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow"]
TUNES     = ["zerolatency", "film", "animation", "grain", "stillimage", "fastdecode"]
SCALES    = ["off", "426x240", "640x360", "854x480", "1280x720", "1920x1080", "2560x1440"]
FPS_OPT   = [24, 25, 30, 48, 60]

def build_cmd(file_path: str, rtmp_url: str, cfg: dict) -> list:
    preset  = cfg.get("preset",     "veryfast")
    tune    = cfg.get("tune",       "zerolatency")
    vbr     = cfg.get("vbitrate",   "2000k")
    abr     = cfg.get("abitrate",   "128k")
    fps     = str(cfg.get("fps",    30))
    res     = cfg.get("resolution", None)
    threads = str(cfg.get("threads", 0))
    gop     = str(int(fps) * 2)
    bufsize = str(int(vbr.replace("k", "")) * 2) + "k"
    ftype   = detect_type(file_path)

    base = ["ffmpeg", "-re", "-stream_loop", "-1", "-threads", threads]
    vf_scale = f",scale={res}" if res else ""
    common_v = [
        "-c:v", "libx264", "-preset", preset, "-tune", tune,
        "-pix_fmt", "yuv420p", "-profile:v", "baseline",
        "-r", fps, "-g", gop, "-keyint_min", gop, "-sc_threshold", "0",
        "-b:v", vbr, "-maxrate", vbr, "-bufsize", bufsize,
    ]
    common_a = ["-c:a", "aac", "-b:a", abr, "-ar", "44100"]
    out = ["-f", "flv", rtmp_url]

    if ftype == "video":
        vf = ["-vf", f"scale=trunc(iw/2)*2:trunc(ih/2)*2{vf_scale}"] if res else []
        return base + ["-i", file_path] + common_v + vf + common_a + out
    if ftype == "audio":
        size = res or "1280x720"
        return (
            base
            + ["-i", file_path, "-f", "lavfi", "-i", f"color=c=black:s={size}:r={fps}"]
            + ["-shortest"] + common_v + common_a
            + ["-map", "1:v:0", "-map", "0:a:0"] + out
        )
    if ftype == "image":
        scale_vf = f"scale=trunc(iw/2)*2:trunc(ih/2)*2{vf_scale}"
        return (
            base
            + ["-loop", "1", "-i", file_path, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
            + ["-vf", scale_vf] + common_v
            + ["-shortest"] + common_a
            + ["-map", "0:v:0", "-map", "1:a:0"] + out
        )
    raise ValueError(f"Unsupported: {ftype}")

@loader.tds
class StreamMod(loader.Module):
    """📡 RTMP media streaming"""
    strings = {
        "name": "Stream",
        "status_active":  "▶️ <b>Stream is live</b>\n\n{icon} <code>{file}</code>\n⏱ Time: <b>{elapsed}</b>\n🔢 PID: <code>{pid}</code>\n📡 <code>{rtmp}</code>\n🎥 <b>{vbr}</b> | <b>{fps}fps</b> | <b>{preset}</b>\n🔊 <b>{abr}</b>\n📋 Queue: <b>{queue}</b>",
        "status_idle":    "⏸ <b>Stream is not active</b>",
        "status_queue":   "\n📋 Queue: <b>{n}</b>",
        "stopped":        "⏹ <b>Stream stopped.</b>",
        "no_rtmp":        "❌ <b>RTMP not configured!</b>\nTap a button to set it up.",
        "downloading":    "⏳ Downloading…",
        "dl_failed":      "❌ Failed to download file.",
        "queued":         "📋 Added to queue ({n})\n{icon} <code>{file}</code>",
        "not_running":    "Not running",
        "queue_empty":    "Queue is empty",
        "queue_header":   "📋 Queue:\n",
        "settings_title": "⚙️ <b>Stream settings</b>",
        "btn_stop":       "⏹ Stop",
        "btn_queue":      "📋 Queue",
        "btn_refresh":    "🔄 Refresh",
        "btn_settings":   "⚙️ Settings",
        "btn_status":     "📊 Status",
        "btn_back":       "🔙 Back",
        "btn_preset":     "🎞 Preset: {v}",
        "btn_tune":       "🎭 Tune: {v}",
        "btn_vbr":        "🎥 Video: {v}",
        "btn_abr":        "🔊 Audio: {v}",
        "btn_fps":        "📐 FPS: {v}",
        "btn_res":        "🖥 Res: {v}",
        "btn_threads":    "🧵 Threads: {v}",
        "btn_rtmps":      "📡 RTMP URL",
        "btn_key":        "🔑 Stream key",
        "btn_set_rtmps":  "📡 Set RTMP URL",
        "btn_set_key":    "🔑 Set stream key",
        "ph_vbr":         "Video bitrate, e.g. 2000k",
        "ph_abr":         "Audio bitrate, e.g. 128k",
        "ph_threads":     "Thread count (0 = auto)",
        "ph_rtmps":       "rtmp://a.rtmp.youtube.com/live2",
        "ph_key":         "Stream key...",
    }

    strings_ru = {
        "_cls_doc":       "📡 RTMP стриминг медиафайлов",
        "status_active":  "▶️ <b>Трансляция идёт</b>\n\n{icon} <code>{file}</code>\n⏱ Время: <b>{elapsed}</b>\n🔢 PID: <code>{pid}</code>\n📡 <code>{rtmp}</code>\n🎥 <b>{vbr}</b> | <b>{fps}fps</b> | <b>{preset}</b>\n🔊 <b>{abr}</b>\n📋 В очереди: <b>{queue}</b>",
        "status_idle":    "⏸ <b>Трансляция не активна</b>",
        "status_queue":   "\n📋 В очереди: <b>{n}</b>",
        "stopped":        "⏹ <b>Трансляция остановлена.</b>",
        "no_rtmp":        "❌ <b>RTMP не настроен!</b>\nНажми кнопку чтобы задать прямо сейчас.",
        "downloading":    "⏳ Скачиваю…",
        "dl_failed":      "❌ Не удалось скачать файл.",
        "queued":         "📋 Добавлено в очередь ({n} шт.)\n{icon} <code>{file}</code>",
        "not_running":    "Не запущено",
        "queue_empty":    "Очередь пуста",
        "queue_header":   "📋 Очередь:\n",
        "settings_title": "⚙️ <b>Настройки трансляции</b>",
        "btn_stop":       "⏹ Стоп",
        "btn_queue":      "📋 Очередь",
        "btn_refresh":    "🔄 Обновить",
        "btn_settings":   "⚙️ Настройки",
        "btn_status":     "📊 Статус",
        "btn_back":       "🔙 Назад",
        "btn_preset":     "🎞 Пресет: {v}",
        "btn_tune":       "🎭 Tune: {v}",
        "btn_vbr":        "🎥 Видео: {v}",
        "btn_abr":        "🔊 Аудио: {v}",
        "btn_fps":        "📐 FPS: {v}",
        "btn_res":        "🖥 Разр: {v}",
        "btn_threads":    "🧵 Треды: {v}",
        "btn_rtmps":      "📡 RTMP URL",
        "btn_key":        "🔑 Ключ",
        "btn_set_rtmps":  "📡 Задать RTMP URL",
        "btn_set_key":    "🔑 Задать ключ",
        "ph_vbr":         "Битрейт видео, напр. 2000k",
        "ph_abr":         "Битрейт аудио, напр. 128k",
        "ph_threads":     "Потоков (0 = авто)",
        "ph_rtmps":       "rtmp://a.rtmp.youtube.com/live2",
        "ph_key":         "Ключ трансляции...",
    }

    def __init__(self):
        self._proc:    subprocess.Popen | None = None
        self._file:    str | None = None
        self._started: float | None = None
        self._queue:   list[str] = []
        self._qtask:   asyncio.Task | None = None
        self.config = loader.ModuleConfig(
            loader.ConfigValue("rtmps",      "",           "Base RTMP URL (rtmp://...)"),
            loader.ConfigValue("key",        "",           "Stream key"),
            loader.ConfigValue("preset",     "veryfast",   "x264 preset",
                               validator=loader.validators.Choice(PRESETS)),
            loader.ConfigValue("tune",       "zerolatency","x264 tune",
                               validator=loader.validators.Choice(TUNES)),
            loader.ConfigValue("vbitrate",   "2000k",      "Video bitrate (e.g. 1500k, 3000k)"),
            loader.ConfigValue("abitrate",   "128k",       "Audio bitrate (e.g. 64k, 192k)"),
            loader.ConfigValue("fps",        30,           "Frames per second",
                               validator=loader.validators.Integer(minimum=1, maximum=120)),
            loader.ConfigValue("resolution", "",           "Output resolution (e.g. 1280x720, empty = no scaling)"),
            loader.ConfigValue("threads",    0,            "FFmpeg thread count (0 = auto)",
                               validator=loader.validators.Integer(minimum=0, maximum=64)),
            loader.ConfigValue("loop",       True,         "Loop the file indefinitely",
                               validator=loader.validators.Boolean()),
            loader.ConfigValue("reconnect",  True,         "Auto-restart on stream disconnect",
                               validator=loader.validators.Boolean()),
        )

    def _s(self, key: str, **kw) -> str:
        return self.strings[key].format(**kw) if kw else self.strings[key]

    def _running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def _stop(self):
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=5)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            self._proc = None
        if self._file and os.path.exists(self._file):
            try:
                os.remove(self._file)
            except Exception:
                pass
        self._file = None
        self._started = None

    def _launch(self, path: str):
        cfg = {k: self.config[k] for k in ("preset", "tune", "vbitrate", "abitrate", "fps", "threads")}
        cfg["resolution"] = self.config["resolution"] or None
        rtmp = f"{self.config['rtmps'].rstrip('/')}/{self.config['key']}"
        self._proc    = subprocess.Popen(build_cmd(path, rtmp, cfg), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._file    = path
        self._started = time.time()

    def _elapsed(self) -> str:
        if not self._started:
            return "00:00:00"
        e = int(time.time() - self._started)
        return f"{e//3600:02d}:{(e%3600)//60:02d}:{e%60:02d}"

    def _status_text(self) -> str:
        if not self._running():
            txt = self._s("status_idle")
            if self._queue:
                txt += self._s("status_queue", n=len(self._queue))
            return txt
        ftype = detect_type(self._file or "")
        rtmp  = f"{self.config['rtmps'].rstrip('/')}/{self.config['key'][:4]}***"
        return self._s(
            "status_active",
            icon=TYPE_ICON.get(ftype, "📄"),
            file=os.path.basename(self._file or "?"),
            elapsed=self._elapsed(),
            pid=self._proc.pid if self._proc else "—",
            rtmp=rtmp,
            vbr=self.config["vbitrate"],
            fps=self.config["fps"],
            preset=self.config["preset"],
            abr=self.config["abitrate"],
            queue=len(self._queue),
        )

    def _res_label(self) -> str:
        r = self.config["resolution"]
        return r if r else "auto"

    def _thr_label(self) -> str:
        t = self.config["threads"]
        return str(t) if t else "auto"

    def _main_markup(self) -> list:
        running = self._running()
        return [
            [
                {"text": self._s("btn_stop"),    "callback": self._cb_stop}    if running
                else {"text": self._s("btn_queue"), "callback": self._cb_queue},
                {"text": self._s("btn_refresh"), "callback": self._cb_refresh},
            ],
            [
                {"text": self._s("btn_settings"), "callback": self._cb_settings},
                {"text": self._s("btn_status"),   "callback": self._cb_status},
            ],
        ]

    def _settings_markup(self) -> list:
        return [
            [
                {"text": self._s("btn_preset",  v=self.config["preset"]), "callback": self._cb_set_preset},
                {"text": self._s("btn_tune",    v=self.config["tune"]),   "callback": self._cb_set_tune},
            ],
            [
                {"text": self._s("btn_vbr", v=self.config["vbitrate"]),
                 "input": self._s("ph_vbr"), "handler": self._ih_vbr},
                {"text": self._s("btn_abr", v=self.config["abitrate"]),
                 "input": self._s("ph_abr"), "handler": self._ih_abr},
            ],
            [
                {"text": self._s("btn_fps", v=self.config["fps"]),        "callback": self._cb_set_fps},
                {"text": self._s("btn_res", v=self._res_label()),         "callback": self._cb_set_res},
            ],
            [
                {"text": self._s("btn_threads", v=self._thr_label()),
                 "input": self._s("ph_threads"), "handler": self._ih_threads},
            ],
            [
                {"text": self._s("btn_rtmps"),
                 "input": self._s("ph_rtmps"), "handler": self._ih_rtmps},
                {"text": self._s("btn_key"),
                 "input": self._s("ph_key"),   "handler": self._ih_key},
            ],
            [{"text": self._s("btn_back"), "callback": self._cb_back}],
        ]

    async def _ih_vbr(self, call: InlineCall, query: str):
        q = query.strip()
        if q.endswith("k") and q[:-1].isdigit():
            self.config["vbitrate"] = q
        await call.edit(self._s("settings_title"), reply_markup=self._settings_markup())

    async def _ih_abr(self, call: InlineCall, query: str):
        q = query.strip()
        if q.endswith("k") and q[:-1].isdigit():
            self.config["abitrate"] = q
        await call.edit(self._s("settings_title"), reply_markup=self._settings_markup())

    async def _ih_threads(self, call: InlineCall, query: str):
        q = query.strip()
        if q.isdigit():
            self.config["threads"] = int(q)
        await call.edit(self._s("settings_title"), reply_markup=self._settings_markup())

    async def _ih_rtmps(self, call: InlineCall, query: str):
        q = query.strip()
        if q.startswith("rtmp"):
            self.config["rtmps"] = q.rstrip("/")
        await call.edit(self._s("settings_title"), reply_markup=self._settings_markup())

    async def _ih_key(self, call: InlineCall, query: str):
        q = query.strip()
        if q:
            self.config["key"] = q
        await call.edit(self._s("settings_title"), reply_markup=self._settings_markup())

    async def _cb_refresh(self, call: InlineCall):
        await call.edit(self._status_text(), reply_markup=self._main_markup())

    async def _cb_status(self, call: InlineCall):
        await call.answer(self._elapsed() if self._running() else self._s("not_running"))

    async def _cb_stop(self, call: InlineCall):
        self._queue.clear()
        if self._qtask:
            self._qtask.cancel()
            self._qtask = None
        self._stop()
        await call.edit(self._s("stopped"), reply_markup=self._main_markup())

    async def _cb_queue(self, call: InlineCall):
        if not self._queue:
            await call.answer(self._s("queue_empty"), show_alert=True)
            return
        lines = [f"{i}. {TYPE_ICON.get(detect_type(f), '📄')} {os.path.basename(f)}"
                 for i, f in enumerate(self._queue, 1)]
        await call.answer(self._s("queue_header") + "\n".join(lines), show_alert=True)

    async def _cb_back(self, call: InlineCall):
        await call.edit(self._status_text(), reply_markup=self._main_markup())

    async def _cb_settings(self, call: InlineCall):
        await call.edit(self._s("settings_title"), reply_markup=self._settings_markup())

    async def _cb_set_preset(self, call: InlineCall):
        cur = self.config["preset"]
        self.config["preset"] = PRESETS[(PRESETS.index(cur) + 1) % len(PRESETS)]
        await call.edit(self._s("settings_title"), reply_markup=self._settings_markup())

    async def _cb_set_tune(self, call: InlineCall):
        cur = self.config["tune"]
        self.config["tune"] = TUNES[(TUNES.index(cur) + 1) % len(TUNES)]
        await call.edit(self._s("settings_title"), reply_markup=self._settings_markup())

    async def _cb_set_fps(self, call: InlineCall):
        cur = self.config["fps"]
        self.config["fps"] = FPS_OPT[(FPS_OPT.index(cur) + 1) % len(FPS_OPT)] if cur in FPS_OPT else 30
        await call.edit(self._s("settings_title"), reply_markup=self._settings_markup())

    async def _cb_set_res(self, call: InlineCall):
        cur = self.config["resolution"] or "off"
        idx = SCALES.index(cur) if cur in SCALES else 0
        nxt = SCALES[(idx + 1) % len(SCALES)]
        self.config["resolution"] = "" if nxt == "off" else nxt
        await call.edit(self._s("settings_title"), reply_markup=self._settings_markup())

    @loader.command(ru_doc="[ответ на медиа] – запустить трансляцию")
    async def stream(self, message):
        """[reply to media] — start stream or add to queue"""
        if not self.config["rtmps"] or not self.config["key"]:
            await self.inline.form(
                self._s("no_rtmp"),
                message=message,
                reply_markup=[
                    [{"text": self._s("btn_set_rtmps"), "input": self._s("ph_rtmps"), "handler": self._ih_rtmps}],
                    [{"text": self._s("btn_set_key"),   "input": self._s("ph_key"),   "handler": self._ih_key}],
                ],
            )
            return

        reply = await message.get_reply_message()
        if not reply or not reply.media:
            await self.inline.form(
                self._status_text(),
                message=message,
                reply_markup=self._main_markup(),
            )
            return

        status = await utils.answer(message, self._s("downloading"))
        path   = await reply.download_media(file=f"/tmp/stream_{int(time.time())}")
        if not path:
            await status.edit(self._s("dl_failed"))
            return
        await status.delete()

        if self._running():
            self._queue.append(path)
            await self.inline.form(
                self._s("queued", n=len(self._queue), icon=TYPE_ICON.get(detect_type(path), "📄"), file=os.path.basename(path)),
                message=message,
                reply_markup=self._main_markup(),
            )
            return

        self._stop()
        self._launch(path)
        await self.inline.form(
            self._status_text(),
            message=message,
            reply_markup=self._main_markup(),
        )

    @loader.command(ru_doc="– панель управления трансляцией")
    async def streamctl(self, message):
        """– open stream control panel"""
        await self.inline.form(
            self._status_text(),
            message=message,
            reply_markup=self._main_markup(),
        )

    @loader.command(ru_doc="– остановить трансляцию и очистить очередь")
    async def streamstop(self, message):
        """– stop stream and clear queue"""
        self._queue.clear()
        if self._qtask:
            self._qtask.cancel()
            self._qtask = None
        self._stop()
        await utils.answer(message, self._s("stopped"))