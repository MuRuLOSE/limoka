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

import logging
import platform
import socket
import os
import time
import aiohttp
import psutil
import json
import random
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from collections import OrderedDict

from .. import loader, utils, validators
from herokutl.tl.functions.users import GetFullUserRequest
from herokutl.tl.functions.payments import GetStarsStatusRequest

logger = logging.getLogger(__name__)

class LRUCache:
    """LRU-кэш с TTL"""
    def __init__(self, max_size: int = 100, ttl: int = 300):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl
        self.timestamps = {}

    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None
            
        if time.time() - self.timestamps[key] > self.ttl:
            del self.cache[key]
            del self.timestamps[key]
            return None
            
        self.cache.move_to_end(key)
        return self.cache[key]

    def set(self, key: str, value: Any):
        if len(self.cache) >= self.max_size:
            oldest = next(iter(self.cache))
            del self.cache[oldest]
            del self.timestamps[oldest]
            
        self.cache[key] = value
        self.timestamps[key] = time.time()

@loader.tds
class PlaceholdersMod(loader.Module):
    """Плейсхолдеры"""
    strings = {"name": "Placeholders+"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "timezone",
                5,
                "Часовой пояс (offset от UTC)",
                validator=validators.Integer(),
            ),
            loader.ConfigValue(
                "weather_city",
                "Oral",
                "Город для погоды",
                validator=validators.String(),
            ),
            loader.ConfigValue(
                "lastfm_user",
                "",
                "Last.FM username",
                validator=validators.String(),
            ),
            loader.ConfigValue(
                "crypto_address",
                "YOUR_WALLET_ADDRESS",
                "Крипто-кошелёк",
                validator=validators.String(),
            ),
            loader.ConfigValue(
                "card_number",
                "**** **** **** ****",
                "Номер карты",
                validator=validators.String(),
            ),
            loader.ConfigValue(
                "donate_site",
                "Boosty:https://boosty.to/yourname",
                "Донат: имя:ссылка",
                validator=validators.String(),
            ),
            loader.ConfigValue(
                "channel",
                "@yourchannel",
                "Канал",
                validator=validators.String(),
            ),
            loader.ConfigValue(
                "social_network",
                "https://vk.com/your",
                "Соцсеть",
                validator=validators.String(),
            ),
        )
        self.cache = LRUCache(max_size=100, ttl=300)

    async def client_ready(self):
        self.session = aiohttp.ClientSession()

        self.me = await self._client.get_me()
        self.full_me = await self._client(GetFullUserRequest(self.me))

        try:
            stars_status = await self._client(GetStarsStatusRequest(entity="me"))
            self.stars_balance = stars_status.balance
        except Exception:
            self.stars_balance = 0

        self.tz = timezone(timedelta(hours=self.config["timezone"]))
        self.weekdays_ru = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

        self._register_placeholders()

    def _register_placeholders(self):
        placeholders = [
            ("username", self.get_username, "Username"),
            ("name", self.get_name, "Имя"),
            ("surname", self.get_surname, "Фамилия"),
            ("bio_description", self.get_bio, "Описание"),
            ("user_id", self.get_user_id, "ID"),
            ("phone_number", self.get_phone, "Телефон"),
            ("dc_id", self.get_dc_id, "DC ID"),
            ("amount_stars", self.get_stars, "Stars"),
            ("premium_check", self.get_premium_check, "Дата окончания Premium"),
            
            ("dollars_in_rub", self.get_usd_to_rub, "USD → RUB"),
            ("rub_in_dollars", self.get_rub_to_usd, "RUB → USD"),
            ("usdt_in_rub", self.get_usdt_to_rub, "USDT → RUB"),
            ("rub_in_usdt", self.get_rub_to_usdt, "RUB → USDT"),
            ("ton_in_rub", self.get_ton_to_rub, "TON → RUB"),
            ("rub_in_ton", self.get_rub_to_ton, "RUB → TON"),
            ("btc_in_rub", self.get_btc_to_rub, "BTC → RUB"),
            ("eth_in_rub", self.get_eth_to_rub, "ETH → RUB"),
            ("stars_in_rub", self.get_stars_to_rub, "Stars → RUB"),
            ("stars_in_ton", self.get_stars_to_ton, "Stars → TON"),
            ("stars_in_usdt", self.get_stars_to_usdt, "Stars → USDT"),
                       
            ("os_uptime", self.get_os_uptime, "Аптайм системы"),
            ("internet_usage", self.get_internet_usage, "Статистика трафика"),
            ("speedtest", self.get_speedtest, "Скорость интернета"),
            ("host", self.get_host, "Hostname ОС"),
            ("shell", self.get_shell, "Оболочка"),
            ("gpu", self.get_gpu, "GPU"),
            ("disk", self.get_disk, "Использование диска"),
            ("local_ip", self.get_local_ip, "Локальный IP"),
            ("user_and_hostname", self.get_user_hostname, "user@hostname"),
            
            ("time", self.get_time, "Время"),
            ("date", self.get_date, "Дата"),
            ("day_of_the_week", self.get_weekday, "День недели"),
            ("data_and_time", self.get_date_time, "Дата и время"),
            ("data_and_time_and_day_of_the_week", self.get_full_date_time_weekday, "Дата, время, день недели"),
            ("weather", self.get_weather_condition, "Погода"),
            ("outdoor_temperature", self.get_temperature, "Температура"),
            ("weather_and_temperature", self.get_weather_temp, "Погода и температура"),
            ("humidity", self.get_humidity, "Влажность"),
            ("pressure", self.get_pressure, "Давление"),
            ("wind_speed", self.get_wind_speed, "Скорость ветра"),
            
            ("my_crypto_address", self.get_crypto_address, "Крипто-адрес"),
            ("my_card_number", self.get_card_number, "Номер карты"),
            ("my_donate_site", self.get_donate_site, "Донат"),
            ("my_channel", self.get_channel, "Канал"),
            ("my_social_network", self.get_social, "Соцсеть"),
            
            ("now_playing", self.get_now_playing, "Сейчас играет"),
            ("last_fm_user_and_now_playing", self.get_user_and_playing, "Last.FM + трек"),
            ("song_name", self.get_song_name, "Название трека"),
            ("song_artist", self.get_song_artist, "Артист"),
            ("last_fm_user", self.get_lastfm_user, "Last.FM username"),
            ("lastfm_stats", self.get_lastfm_stats, "Last.FM статистика"),
        ]
        
        for name, func, desc in placeholders:
            utils.register_placeholder(name, func, desc)
    
    async def get_premium_check(self):
        if not getattr(self.me, "premium", False):
            return "Нет Premium"

        # premium_until отсутствует в публичном MTProto API herokutl/Telethon —
        # пробуем достать его, но не падаем если поля нет
        until = None
        try:
            until = getattr(self.full_me.full_user, "premium_until", None)
            # Иногда это datetime, иногда unix timestamp (int)
            if isinstance(until, datetime):
                until = until.timestamp()
        except Exception:
            until = None

        if not until:
            return "✅ Premium активен"

        if until < time.time():
            return "⚠️ Премиум истёк"

        end_date = datetime.fromtimestamp(until, tz=self.tz)
        days_left = (end_date.date() - datetime.now(self.tz).date()).days
        formatted = end_date.strftime("%d.%m.%Y")
        return f"✅ до {formatted} (ещё {days_left} дн.)"

    async def get_username(self): 
        return f"@{self.me.username}" if self.me.username else "Нет"
    
    async def get_name(self): 
        return self.me.first_name or "Нет"
    
    async def get_surname(self): 
        return self.me.last_name or "Нет"
    
    async def get_bio(self): 
        return self.full_me.full_user.about or "Нет описания"
    
    async def get_user_id(self): 
        return str(self.me.id)
    
    async def get_phone(self): 
        return self.me.phone or "Скрыт"
    
    async def get_dc_id(self): 
        return str(self.me.dc_id if hasattr(self.me, "dc_id") else "Неизвестно")
    
    async def get_stars(self): 
        return f"{self.stars_balance:,}".replace(",", " ") if self.stars_balance else "0"

    async def get_usd_to_rub(self):
        cache_key = "usd_rub"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            async with self.session.get("https://www.cbr-xml-daily.ru/daily_json.js") as resp:
                data = await resp.json()
                rate = data["Valute"]["USD"]["Value"]
                result = f"1 USD ≈ {rate:.2f} RUB"
                self.cache.set(cache_key, result)
                return result
        except Exception:
            try:
                async with self.session.get("https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json") as resp:
                    data = await resp.json()
                    rate = data["usd"]["rub"]
                    result = f"1 USD ≈ {rate:.2f} RUB"
                    self.cache.set(cache_key, result)
                    return result
            except Exception:
                return "Курс USD недоступен"
    
    async def get_rub_to_usd(self):
        usd_rub = await self.get_usd_to_rub()
        if "≈" in usd_rub:
            try:
                rate = float(usd_rub.split("≈")[1].strip().split()[0])
                return f"1 RUB ≈ {1/rate:.4f} USD"
            except Exception:
                pass
        return "Курс RUB недоступен"
    
    async def get_usdt_to_rub(self):
        return await self.get_usd_to_rub()  # USDT ≈ USD
    
    async def get_rub_to_usdt(self):
        return await self.get_rub_to_usd()

    async def get_ton_to_rub(self):
        cache_key = "ton_rub"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            async with self.session.get("https://api.coingecko.com/api/v3/simple/price?ids=toncoin&vs_currencies=rub") as resp:
                data = await resp.json()
                rate = data["toncoin"]["rub"]
                result = f"1 TON ≈ {rate:.2f} RUB"
                self.cache.set(cache_key, result)
                return result
        except Exception:
            return "Курс TON недоступен"
    
    async def get_rub_to_ton(self):
        ton_rub = await self.get_ton_to_rub()
        if "≈" in ton_rub:
            try:
                rate = float(ton_rub.split("≈")[1].strip().split()[0])
                return f"1 RUB ≈ {1/rate:.6f} TON"
            except Exception:
                pass
        return "Курс недоступен"
    
    async def get_btc_to_rub(self):
        cache_key = "btc_rub"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            async with self.session.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=rub") as resp:
                data = await resp.json()
                rate = data["bitcoin"]["rub"]
                result = f"1 BTC ≈ {rate:,.0f} RUB"
                self.cache.set(cache_key, result)
                return result
        except Exception:
            return "Курс BTC недоступен"
    
    async def get_eth_to_rub(self):
        cache_key = "eth_rub"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            async with self.session.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=rub") as resp:
                data = await resp.json()
                rate = data["ethereum"]["rub"]
                result = f"1 ETH ≈ {rate:,.0f} RUB"
                self.cache.set(cache_key, result)
                return result
        except Exception:
            return "Курс ETH недоступен"
    
    async def get_stars_to_rub(self): 
        return "1 Star ≈ 85 RUB"
    
    async def get_stars_to_ton(self): 
        return "1 Star ≈ 0.012 TON"
    
    async def get_stars_to_usdt(self): 
        return "1 Star ≈ 0.92 USDT"

    async def get_os_uptime(self):
        boot = datetime.fromtimestamp(psutil.boot_time())
        delta = datetime.now() - boot
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        else:
            return f"{hours}h {minutes}m"
    
    async def get_internet_usage(self):
        try:
            net = psutil.net_io_counters()
            sent_gb = net.bytes_sent // (1024**3)
            recv_gb = net.bytes_recv // (1024**3)
            return f"↑ {sent_gb} GB │ ↓ {recv_gb} GB"
        except Exception:
            return "↑ 0 GB │ ↓ 0 GB"
    
    async def get_speedtest(self):
        cache_key = "speedtest"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        test_urls = [
            "https://proof.ovh.net/files/10Mb.dat",
            "http://ipv4.download.thinkbroadband.com/10MB.zip",
            "https://speedtest.ftp.otenet.gr/files/test10Mb.db"
        ]
        
        for url in test_urls:
            try:
                start = time.time()
                async with self.session.get(url, timeout=10) as resp:
                    chunk_size = 1024 * 1024
                    total = 0
                    async for chunk in resp.content.iter_chunked(chunk_size):
                        total += len(chunk)
                        if total >= chunk_size:
                            break
                
                duration = time.time() - start
                if duration > 0:
                    speed_mbps = (total * 8) / (duration * 1024 * 1024)
                    result = f"≈ {speed_mbps:.1f} Mbps"
                    self.cache.set(cache_key, result)
                    return result
            except Exception:
                continue
        
        return "Тест скорости недоступен"
    
    async def get_host(self): 
        return platform.node() or "Неизвестно"
    
    async def get_shell(self): 
        return os.environ.get("SHELL", "Неизвестно").split("/")[-1]
    
    async def get_gpu(self):
        return "N/A (Cloud)"
    
    async def get_disk(self):
        try:
            usage = psutil.disk_usage("/")
            percent = (usage.used / usage.total) * 100
            used_gb = usage.used // (1024**3)
            total_gb = usage.total // (1024**3)
            return f"{used_gb} GB / {total_gb} GB ({percent:.1f}%)"
        except Exception:
            return "Диск недоступен"
    
    async def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "Неизвестно"
    
    async def get_user_hostname(self): 
        user = os.getlogin() if hasattr(os, 'getlogin') else os.environ.get("USER", "user")
        host = await self.get_host()
        return f"{user}@{host}"

    async def get_time(self): 
        return datetime.now(self.tz).strftime("%H:%M:%S")
    
    async def get_date(self): 
        return datetime.now(self.tz).strftime("%d.%m.%Y")
    
    async def get_weekday(self): 
        return self.weekdays_ru[datetime.now(self.tz).weekday()]
    
    async def get_date_time(self): 
        return datetime.now(self.tz).strftime("%d.%m.%Y %H:%M")
    
    async def get_full_date_time_weekday(self):
        now = datetime.now(self.tz)
        return f"{now.strftime('%d.%m.%Y %H:%M')} ({self.weekdays_ru[now.weekday()]})"
    
    async def get_weather_condition(self):
        data = await self._get_weather_data()
        return data.get("condition", "Неизвестно")
    
    async def get_temperature(self):
        data = await self._get_weather_data()
        return data.get("temp", "??°C")
    
    async def get_weather_temp(self):
        data = await self._get_weather_data()
        return data.get("weather_temp", "??")
    
    async def get_humidity(self):
        data = await self._get_weather_data()
        return data.get("humidity", "??%")
    
    async def get_pressure(self):
        data = await self._get_weather_data()
        return data.get("pressure", "?? гПа")
    
    async def get_wind_speed(self):
        data = await self._get_weather_data()
        return data.get("wind", "?? м/с")
    
    async def _get_weather_data(self):
        city = self.config["weather_city"]
        
        cache_key = f"weather_{city}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            async with self.session.get(f"http://wttr.in/{city}?format=j1&lang=ru") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    c = data["current_condition"][0]
                    weather_data = {
                        "condition": c["lang_ru"][0]["value"],
                        "temp": f"{c['temp_C']}°C",
                        "weather_temp": f"{c['lang_ru'][0]['value']} {c['temp_C']}°C",
                        "humidity": f"{c['humidity']}%",
                        "pressure": f"{c['pressure']} мм",
                        "wind": f"{c['windspeedKmph']} км/ч",
                    }
                    self.cache.set(cache_key, weather_data)
                    return weather_data
        except Exception:
            pass
        
        default = {
            "condition": "Неизвестно",
            "temp": "??°C",
            "weather_temp": "??",
            "humidity": "??%",
            "pressure": "?? мм",
            "wind": "?? км/ч",
        }
        self.cache.set(cache_key, default)
        return default

    async def get_crypto_address(self): 
        return self.config["crypto_address"]
    
    async def get_card_number(self): 
        return self.config["card_number"]
    
    async def get_donate_site(self):
        val = self.config["donate_site"]
        if ":" in val:
            name, link = val.split(":", 1)
            return f'<a href="{link.strip()}">{name.strip()}</a>'
        return val
    
    async def get_channel(self):
        ch = self.config["channel"]
        if ch.startswith("@"):
            return f'<a href="https://t.me/{ch[1:]}">{ch}</a>'
        return ch
    
    async def get_social(self): 
        return self.config["social_network"]

    async def get_lastfm_user(self): 
        return self.config["lastfm_user"] or "Не указан"
    
    async def get_now_playing(self):
        track = await self._get_current_track()
        if not track:
            return "🎵 Ничего не играет"
        return f"🎵 <b>{track['name']}</b> — {track['artist']}"
    
    async def get_user_and_playing(self):
        user = await self.get_lastfm_user()
        track = await self._get_current_track()
        if not track:
            return f"{user}: ничего не играет"
        return f"{user}: {track['name']} — {track['artist']}"
    
    async def get_song_name(self):
        track = await self._get_current_track()
        return track["name"] if track else "—"
    
    async def get_song_artist(self):
        track = await self._get_current_track()
        return track["artist"] if track else "—"
    
    async def get_lastfm_stats(self):
        user = self.config["lastfm_user"]
        if not user:
            return "Укажите Last.FM username"
        
        cache_key = f"lastfm_stats_{user}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        api_key = "460cda35be2fbf4f28e8ea7a38580730"
        
        try:
            async with self.session.get(
                "http://ws.audioscrobbler.com/2.0/",
                params={
                    "method": "user.getinfo",
                    "user": user,
                    "api_key": api_key,
                    "format": "json"
                }
            ) as resp:
                data = await resp.json()
                if "user" in data:
                    stats = data["user"]
                    result = f"🎵 {stats['playcount']} скробблов"
                    self.cache.set(cache_key, result)
                    return result
        except Exception:
            pass
        
        return "Статистика недоступна"
    
    async def _get_current_track(self):
        user = self.config["lastfm_user"]
        if not user:
            return None
        
        cache_key = f"lastfm_track_{user}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        api_key = "460cda35be2fbf4f28e8ea7a38580730"
        
        try:
            async with self.session.get(
                "http://ws.audioscrobbler.com/2.0/",
                params={
                    "method": "user.getrecenttracks",
                    "user": user,
                    "api_key": api_key,
                    "format": "json",
                    "limit": 1
                }
            ) as resp:
                data = await resp.json()
                tracks = data.get("recenttracks", {}).get("track", [])
                
                if tracks:
                    track = tracks[0]
                    now_playing = "@attr" in track and "nowplaying" in track["@attr"]
                    
                    result = {
                        "name": track["name"],
                        "artist": track["artist"]["#text"],
                        "now_playing": now_playing
                    }
                    self.cache.set(cache_key, result)
                    return result
        except Exception:
            pass
        
        return None

    async def on_unload(self):
        utils.unregister_placeholders(self.__class__.__name__)
        try:
            await self.session.close()
        except Exception:
            pass