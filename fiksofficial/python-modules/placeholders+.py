#         ______     ___  ___          _       _      
#    ____ | ___ \    |  \/  |         | |     | |     
#   / __ \| |_/ /   _| .  . | ___   __| |_   _| | ___ 
#  / / _` |  __/ | | | |\/| |/ _ \ / _` | | | | |/ _ \
# | | (_| |  | |_| | |  | | (_) | (_| | |_| | |  __/
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
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from collections import OrderedDict

from .. import loader, utils, validators
from herokutl.tl.functions.users import GetFullUserRequest
from herokutl.tl.functions.payments import GetStarsStatusRequest

logger = logging.getLogger(__name__)

# Курс Telegram Stars к USD (фиксированный, источник: xvestor.ru/converter/tgstars/usd)
STAR_USD = 0.022


class LRUCache:
    """LRU-кэш с TTL"""
    def __init__(self, max_size: int = 150, ttl: int = 300):
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
    """Placeholders+: profile, time, weather, exchange rates, crypto, system, music, facts and quotes — for bio, name and status"""

    strings_ru = {
        "_cls_doc": "Плейсхолдеры+: профиль, время, погода, курсы валют, крипта, система, музыка, факты и цитаты — для био, имени и статуса",
        "_cmd_doc_phtest": "- Отрендерить текст с плейсхолдерами (.phtest Привет, {name}!)",
        "_cmd_doc_phlist": "- Список всех плейсхолдеров с кнопками",
        "name": "Placeholders+",

        "cat_profile": "Профиль",
        "cat_currency": "Валюты",
        "cat_system": "Система",
        "cat_datetime": "Дата и время",
        "cat_weather": "Погода",
        "cat_personal": "Личное",
        "cat_music": "Музыка",
        "cat_github": "GitHub",
        "cat_fun": "Факты и цитаты",

        "phtest_usage": "<b>Использование:</b> <code>.phtest Привет, {name}! Курс: {dollars_in_rub}</code>",
        "phtest_unknown": "🚫 Неизвестный плейсхолдер: <code>{}</code>",
        "phtest_error": "🚫 Ошибка в шаблоне: <code>{}</code>",
        "phlist_title": "📋 <b>Placeholders+</b>\n\nВсего плейсхолдеров: <b>{}</b>\nВыберите категорию:",
        "phlist_category": "{} <b>{}</b>\n\n{}",
        "btn_back": "⬅️ Назад",
        "btn_close": "❌",

        "weekdays": "Понедельник,Вторник,Среда,Четверг,Пятница,Суббота,Воскресенье",
        "fmt_days": "{}д {}ч {}м",
        "fmt_hours": "{}ч {}м",
        "fmt_minutes": "{}м",

        "ph_username": "Username",
        "ph_name": "Имя",
        "ph_surname": "Фамилия",
        "ph_bio_description": "Описание профиля",
        "ph_user_id": "ID аккаунта",
        "ph_phone_number": "Телефон",
        "ph_dc_id": "DC ID",
        "ph_amount_stars": "Баланс Stars",
        "ph_premium_check": "Дата окончания Premium",

        "ph_dollars_in_rub": "USD → RUB",
        "ph_rub_in_dollars": "RUB → USD",
        "ph_euros_in_rub": "EUR → RUB",
        "ph_rub_in_euros": "RUB → EUR",
        "ph_yuan_in_rub": "CNY → RUB",
        "ph_tenge_in_rub": "KZT → RUB",
        "ph_rub_in_tenge": "RUB → KZT",
        "ph_usdt_in_rub": "USDT → RUB",
        "ph_rub_in_usdt": "RUB → USDT",
        "ph_ton_in_rub": "TON → RUB",
        "ph_rub_in_ton": "RUB → TON",
        "ph_btc_in_rub": "BTC → RUB",
        "ph_eth_in_rub": "ETH → RUB",
        "ph_stars_in_rub": "Star → RUB",
        "ph_stars_in_ton": "Star → TON",
        "ph_stars_in_usdt": "Star → USDT",

        "ph_os_uptime": "Аптайм системы",
        "ph_internet_usage": "Статистика трафика",
        "ph_speedtest": "Скорость интернета",
        "ph_shell": "Оболочка",
        "ph_gpu": "GPU",
        "ph_disk": "Использование диска",
        "ph_local_ip": "Локальный IP",
        "ph_public_ip": "Внешний IP",
        "ph_ip_info": "Геолокация по IP",
        "ph_user_and_hostname": "user@hostname",
        "ph_battery": "Заряд батареи",
        "ph_cpu_usage": "Загрузка CPU",
        "ph_ram_usage": "Использование RAM",

        "ph_time": "Время",
        "ph_date": "Дата",
        "ph_day_of_the_week": "День недели",
        "ph_data_and_time": "Дата и время",
        "ph_data_and_time_and_day_of_the_week": "Дата, время, день недели",
        "ph_moon_phase": "Фаза Луны",
        "ph_zodiac_sign": "Знак зодиака",

        "ph_weather": "Погода",
        "ph_outdoor_temperature": "Температура",
        "ph_weather_and_temperature": "Погода и температура",
        "ph_weather_emoji": "Эмодзи погоды",
        "ph_feels_like": "Ощущается как",
        "ph_humidity": "Влажность",
        "ph_pressure": "Давление",
        "ph_wind_speed": "Скорость ветра",

        "ph_my_crypto_address": "Крипто-адрес",
        "ph_my_card_number": "Номер карты",
        "ph_my_donate_site": "Донат",
        "ph_my_channel": "Канал",
        "ph_my_social_network": "Соцсеть",

        "ph_now_playing": "Сейчас играет",
        "ph_last_fm_user_and_now_playing": "Last.FM + трек",
        "ph_song_name": "Название трека",
        "ph_song_artist": "Артист",
        "ph_last_fm_user": "Last.FM username",
        "ph_lastfm_stats": "Last.FM статистика",

        "ph_github_repos": "Публичные репозитории GitHub",
        "ph_github_followers": "Подписчики GitHub",

        "ph_random_fact": "Случайный факт",
        "ph_quote": "Случайная цитата",
        "ph_joke": "Случайная шутка",
        "ph_advice": "Случайный совет",
        "ph_cat_fact": "Факт о котах",
        "ph_kanye_quote": "Цитата Канье Уэста",
        "ph_affirmation": "Аффирмация",

        "no_premium": "Нет Premium",
        "premium_expired": "Премиум закончился",
        "premium_left": "{} (осталось {} дн.)",
        "no_value": "Нет",
        "no_bio": "Нет описания",
        "hidden": "Скрыт",
        "unknown": "Неизвестно",
        "rate_pair": "1 {} ≈ {:.{digits}f} {}",
        "rate_unavailable": "Курс {} недоступен",
        "rate_generic_unavailable": "Курс недоступен",
        "net_usage": "↑ {} GB │ ↓ {} GB",
        "speedtest_unavailable": "Тест скорости недоступен",
        "disk_unavailable": "Диск недоступен",
        "no_battery": "Нет батареи",
        "na": "N/A",
        "w_condition_na": "Неизвестно",
        "w_temp_na": "??°C",
        "w_unavailable": "Погода недоступна",
        "w_humidity_na": "??%",
        "w_pressure_na": "?? мм рт. ст.",
        "w_wind_na": "?? км/ч",
        "nothing_playing": "🎵 Ничего не играет",
        "not_specified": "Не указан",
        "specify_lastfm": "Укажите Last.FM username",
        "lastfm_stats_unavailable": "Статистика недоступна",
        "scrobbles": "🎵 {} скробблов",
        "dash": "—",
        "specify_github": "Укажите GitHub username",
        "github_not_found": "Пользователь не найден",
        "gh_repos": "📦 {} репозиториев",
        "gh_followers": "👥 {} подписчиков",
        "fact_prefix": "💡 {}",
        "fact_unavailable": "Факт недоступен",
        "quote_fmt": "«{}» — {}",
        "quote_unavailable": "Цитата недоступна",
        "joke_prefix": "😄 {}",
        "joke_unavailable": "Шутка недоступна",
        "advice_prefix": "🧠 {}",
        "advice_unavailable": "Совет недоступен",
        "catfact_prefix": "🐱 {}",
        "catfact_unavailable": "Факт о котах недоступен",
        "kanye_prefix": "🎤 {}",
        "affirmation_prefix": "✨ {}",
        "affirmation_unavailable": "Аффирмация недоступна",

        "gpu_na": "N/A (Cloud)",
        "moon_new": "🌑 Новолуние",
        "moon_waxing_crescent": "🌒 Растущий серп",
        "moon_first_quarter": "🌓 Первая четверть",
        "moon_waxing_gibbous": "🌔 Растущая Луна",
        "moon_full": "🌕 Полнолуние",
        "moon_waning_gibbous": "🌖 Убывающая Луна",
        "moon_last_quarter": "🌗 Последняя четверть",
        "moon_waning_crescent": "🌘 Убывающий серп",
        "zodiac_capricorn": "♑ Козерог",
        "zodiac_aquarius": "♒ Водолей",
        "zodiac_pisces": "♓ Рыбы",
        "zodiac_aries": "♈ Овен",
        "zodiac_taurus": "♉ Телец",
        "zodiac_gemini": "♊ Близнецы",
        "zodiac_cancer": "♋ Рак",
        "zodiac_leo": "♌ Лев",
        "zodiac_virgo": "♍ Дева",
        "zodiac_libra": "♎ Весы",
        "zodiac_scorpio": "♏ Скорпион",
        "zodiac_sagittarius": "♐ Стрелец",

        "unit_kmh": "{} км/ч",
        "unit_ms": "{} м/с",
        "unit_mmhg": "{} мм рт. ст.",
        "unit_hpa": "{} гПа",
    }

    strings = {
        "name": "Placeholders+",

        "cat_profile": "Profile",
        "cat_currency": "Currency",
        "cat_system": "System",
        "cat_datetime": "Date & Time",
        "cat_weather": "Weather",
        "cat_personal": "Personal",
        "cat_music": "Music",
        "cat_github": "GitHub",
        "cat_fun": "Facts & Quotes",

        "phtest_usage": "<b>Usage:</b> <code>.phtest Hello, {name}! Rate: {dollars_in_rub}</code>",
        "phtest_unknown": "🚫 Unknown placeholder: <code>{}</code>",
        "phtest_error": "🚫 Template error: <code>{}</code>",
        "phlist_title": "📋 <b>Placeholders+</b>\n\nTotal placeholders: <b>{}</b>\nChoose a category:",
        "phlist_category": "{} <b>{}</b>\n\n{}",
        "btn_back": "⬅️ Back",
        "btn_close": "❌",

        "weekdays": "Monday,Tuesday,Wednesday,Thursday,Friday,Saturday,Sunday",
        "fmt_days": "{}d {}h {}m",
        "fmt_hours": "{}h {}m",
        "fmt_minutes": "{}m",

        "ph_username": "Username",
        "ph_name": "First name",
        "ph_surname": "Last name",
        "ph_bio_description": "Bio",
        "ph_user_id": "Account ID",
        "ph_phone_number": "Phone",
        "ph_dc_id": "DC ID",
        "ph_amount_stars": "Stars balance",
        "ph_premium_check": "Premium expiry date",

        "ph_dollars_in_rub": "USD → RUB",
        "ph_rub_in_dollars": "RUB → USD",
        "ph_euros_in_rub": "EUR → RUB",
        "ph_rub_in_euros": "RUB → EUR",
        "ph_yuan_in_rub": "CNY → RUB",
        "ph_tenge_in_rub": "KZT → RUB",
        "ph_rub_in_tenge": "RUB → KZT",
        "ph_usdt_in_rub": "USDT → RUB",
        "ph_rub_in_usdt": "RUB → USDT",
        "ph_ton_in_rub": "TON → RUB",
        "ph_rub_in_ton": "RUB → TON",
        "ph_btc_in_rub": "BTC → RUB",
        "ph_eth_in_rub": "ETH → RUB",
        "ph_stars_in_rub": "Star → RUB",
        "ph_stars_in_ton": "Star → TON",
        "ph_stars_in_usdt": "Star → USDT",

        "ph_os_uptime": "System uptime",
        "ph_internet_usage": "Traffic stats",
        "ph_speedtest": "Internet speed",
        "ph_shell": "Shell",
        "ph_gpu": "GPU",
        "ph_disk": "Disk usage",
        "ph_local_ip": "Local IP",
        "ph_public_ip": "Public IP",
        "ph_ip_info": "IP geolocation",
        "ph_user_and_hostname": "user@hostname",
        "ph_battery": "Battery level",
        "ph_cpu_usage": "CPU load",
        "ph_ram_usage": "RAM usage",

        "ph_time": "Time",
        "ph_date": "Date",
        "ph_day_of_the_week": "Day of week",
        "ph_data_and_time": "Date & time",
        "ph_data_and_time_and_day_of_the_week": "Date, time, weekday",
        "ph_moon_phase": "Moon phase",
        "ph_zodiac_sign": "Zodiac sign",

        "ph_weather": "Weather",
        "ph_outdoor_temperature": "Temperature",
        "ph_weather_and_temperature": "Weather & temperature",
        "ph_weather_emoji": "Weather emoji",
        "ph_feels_like": "Feels like",
        "ph_humidity": "Humidity",
        "ph_pressure": "Pressure",
        "ph_wind_speed": "Wind speed",

        "ph_my_crypto_address": "Crypto address",
        "ph_my_card_number": "Card number",
        "ph_my_donate_site": "Donate link",
        "ph_my_channel": "Channel",
        "ph_my_social_network": "Social link",

        "ph_now_playing": "Now playing",
        "ph_last_fm_user_and_now_playing": "Last.FM + track",
        "ph_song_name": "Track name",
        "ph_song_artist": "Artist",
        "ph_last_fm_user": "Last.FM username",
        "ph_lastfm_stats": "Last.FM stats",

        "ph_github_repos": "Public GitHub repos",
        "ph_github_followers": "GitHub followers",

        "ph_random_fact": "Random fact",
        "ph_quote": "Random quote",
        "ph_joke": "Random joke",
        "ph_advice": "Random advice",
        "ph_cat_fact": "Cat fact",
        "ph_kanye_quote": "Kanye West quote",
        "ph_affirmation": "Affirmation",

        "no_premium": "No Premium",
        "premium_expired": "Premium expired",
        "premium_left": "{} ({} days left)",
        "no_value": "None",
        "no_bio": "No bio",
        "hidden": "Hidden",
        "unknown": "Unknown",
        "rate_pair": "1 {} ≈ {:.{digits}f} {}",
        "rate_unavailable": "{} rate unavailable",
        "rate_generic_unavailable": "Rate unavailable",
        "net_usage": "↑ {} GB │ ↓ {} GB",
        "speedtest_unavailable": "Speed test unavailable",
        "disk_unavailable": "Disk unavailable",
        "no_battery": "No battery",
        "na": "N/A",
        "w_condition_na": "Unknown",
        "w_temp_na": "??°C",
        "w_unavailable": "Weather unavailable",
        "w_humidity_na": "??%",
        "w_pressure_na": "?? mmHg",
        "w_wind_na": "?? km/h",
        "nothing_playing": "🎵 Nothing playing",
        "not_specified": "Not set",
        "specify_lastfm": "Set Last.FM username in config",
        "lastfm_stats_unavailable": "Stats unavailable",
        "scrobbles": "🎵 {} scrobbles",
        "dash": "—",
        "specify_github": "Set GitHub username in config",
        "github_not_found": "User not found",
        "gh_repos": "📦 {} repos",
        "gh_followers": "👥 {} followers",
        "fact_prefix": "💡 {}",
        "fact_unavailable": "Fact unavailable",
        "quote_fmt": "\"{}\" — {}",
        "quote_unavailable": "Quote unavailable",
        "joke_prefix": "😄 {}",
        "joke_unavailable": "Joke unavailable",
        "advice_prefix": "🧠 {}",
        "advice_unavailable": "Advice unavailable",
        "catfact_prefix": "🐱 {}",
        "catfact_unavailable": "Cat fact unavailable",
        "kanye_prefix": "🎤 {}",
        "affirmation_prefix": "✨ {}",
        "affirmation_unavailable": "Affirmation unavailable",

        "gpu_na": "N/A (Cloud)",
        "moon_new": "🌑 New moon",
        "moon_waxing_crescent": "🌒 Waxing crescent",
        "moon_first_quarter": "🌓 First quarter",
        "moon_waxing_gibbous": "🌔 Waxing gibbous",
        "moon_full": "🌕 Full moon",
        "moon_waning_gibbous": "🌖 Waning gibbous",
        "moon_last_quarter": "🌗 Last quarter",
        "moon_waning_crescent": "🌘 Waning crescent",
        "zodiac_capricorn": "♑ Capricorn",
        "zodiac_aquarius": "♒ Aquarius",
        "zodiac_pisces": "♓ Pisces",
        "zodiac_aries": "♈ Aries",
        "zodiac_taurus": "♉ Taurus",
        "zodiac_gemini": "♊ Gemini",
        "zodiac_cancer": "♋ Cancer",
        "zodiac_leo": "♌ Leo",
        "zodiac_virgo": "♍ Virgo",
        "zodiac_libra": "♎ Libra",
        "zodiac_scorpio": "♏ Scorpio",
        "zodiac_sagittarius": "♐ Sagittarius",

        "unit_kmh": "{} km/h",
        "unit_ms": "{} m/s",
        "unit_mmhg": "{} mmHg",
        "unit_hpa": "{} hPa",
    }

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
                "lastfm_api_key",
                "460cda35be2fbf4f28e8ea7a38580730",
                "Last.FM API key",
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
            loader.ConfigValue(
                "github_username",
                "",
                "GitHub username (для плейсхолдеров статистики)",
                validator=validators.String(),
            ),
            loader.ConfigValue(
                "time_format",
                "%H:%M:%S",
                "Формат времени (strftime)",
                validator=validators.String(),
            ),
            loader.ConfigValue(
                "date_format",
                "%d.%m.%Y",
                "Формат даты (strftime)",
                validator=validators.String(),
            ),
            loader.ConfigValue(
                "wind_unit",
                "км/ч",
                "Единица скорости ветра",
                validator=validators.Choice(["км/ч", "м/с"]),
            ),
            loader.ConfigValue(
                "pressure_unit",
                "мм рт. ст.",
                "Единица давления",
                validator=validators.Choice(["мм рт. ст.", "гПа"]),
            ),
        )
        self.cache = LRUCache(max_size=150, ttl=300)

    async def client_ready(self, client, db):
        self._client = client
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15)
        )

        self.me = await client.get_me()
        self.full_me = await client(GetFullUserRequest(self.me))

        self._started_at = time.time()
        self.tz = timezone(timedelta(hours=self.config["timezone"]))

        try:
            psutil.cpu_percent(interval=None)
        except Exception:
            pass

        self._register_placeholders()

    # ==================== Команды ====================

    @loader.command()
    async def phtestcmd(self, message):
        """- Render text with placeholders (.phtest Hello, {name}!)"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["phtest_usage"])
            return

        data = {}
        try:
            data = await utils.get_placeholders(data, args)
            out = args.format(**data)
        except KeyError as e:
            out = self.strings["phtest_unknown"].format(e)
        except Exception as e:
            out = self.strings["phtest_error"].format(e)

        await utils.answer(message, out)

    @loader.command()
    async def phlistcmd(self, message):
        """- List all placeholders with buttons"""
        await self.inline.form(
            text=self._main_text(),
            message=message,
            reply_markup=self._main_markup(),
            force_me=True,
        )

    async def _ph_main(self, call):
        await call.edit(self._main_text(), reply_markup=self._main_markup())

    async def _ph_category(self, call, idx: int):
        emoji, title, items = self._groups()[idx]
        lines = "\n".join(
            f"• <code>{{{name}}}</code> — {desc}"
            for name, _, desc in items
        )
        await call.edit(
            self.strings["phlist_category"].format(emoji, title, lines),
            reply_markup=self._category_markup(),
        )

    def _main_text(self):
        total = sum(len(items) for _, _, items in self._groups())
        return self.strings["phlist_title"].format(total)

    def _main_markup(self):
        rows = []
        row = []
        for idx, (emoji, title, _) in enumerate(self._groups()):
            row.append({
                "text": f"{emoji} {title}",
                "callback": self._ph_category,
                "args": (idx,),
            })
            if len(row) == 2:
                rows.append(row)
                row = []
        if row:
            rows.append(row)
        rows.append([{"text": self.strings["btn_close"], "action": "close"}])
        return rows

    def _category_markup(self):
        return [
            [{"text": self.strings["btn_back"], "callback": self._ph_main}],
            [{"text": self.strings["btn_close"], "action": "close"}],
        ]

    # ==================== Хелперы ====================

    def _groups(self):
        s = self.strings
        return [
            ("👤", s["cat_profile"], [
                ("username", self.get_username, s["ph_username"]),
                ("name", self.get_name, s["ph_name"]),
                ("surname", self.get_surname, s["ph_surname"]),
                ("bio_description", self.get_bio, s["ph_bio_description"]),
                ("user_id", self.get_user_id, s["ph_user_id"]),
                ("phone_number", self.get_phone, s["ph_phone_number"]),
                ("dc_id", self.get_dc_id, s["ph_dc_id"]),
                ("amount_stars", self.get_stars, s["ph_amount_stars"]),
                ("premium_check", self.get_premium_check, s["ph_premium_check"]),
            ]),
            ("💱", s["cat_currency"], [
                ("dollars_in_rub", self.get_usd_to_rub, s["ph_dollars_in_rub"]),
                ("rub_in_dollars", self.get_rub_to_usd, s["ph_rub_in_dollars"]),
                ("euros_in_rub", self.get_eur_to_rub, s["ph_euros_in_rub"]),
                ("rub_in_euros", self.get_rub_to_eur, s["ph_rub_in_euros"]),
                ("yuan_in_rub", self.get_cny_to_rub, s["ph_yuan_in_rub"]),
                ("tenge_in_rub", self.get_kzt_to_rub, s["ph_tenge_in_rub"]),
                ("rub_in_tenge", self.get_rub_to_kzt, s["ph_rub_in_tenge"]),
                ("usdt_in_rub", self.get_usdt_to_rub, s["ph_usdt_in_rub"]),
                ("rub_in_usdt", self.get_rub_to_usdt, s["ph_rub_in_usdt"]),
                ("ton_in_rub", self.get_ton_to_rub, s["ph_ton_in_rub"]),
                ("rub_in_ton", self.get_rub_to_ton, s["ph_rub_in_ton"]),
                ("btc_in_rub", self.get_btc_to_rub, s["ph_btc_in_rub"]),
                ("eth_in_rub", self.get_eth_to_rub, s["ph_eth_in_rub"]),
                ("stars_in_rub", self.get_stars_to_rub, s["ph_stars_in_rub"]),
                ("stars_in_ton", self.get_stars_to_ton, s["ph_stars_in_ton"]),
                ("stars_in_usdt", self.get_stars_to_usdt, s["ph_stars_in_usdt"]),
            ]),
            ("🖥", s["cat_system"], [
                ("os_uptime", self.get_os_uptime, s["ph_os_uptime"]),
                ("internet_usage", self.get_internet_usage, s["ph_internet_usage"]),
                ("speedtest", self.get_speedtest, s["ph_speedtest"]),
                ("shell", self.get_shell, s["ph_shell"]),
                ("gpu", self.get_gpu, s["ph_gpu"]),
                ("disk", self.get_disk, s["ph_disk"]),
                ("local_ip", self.get_local_ip, s["ph_local_ip"]),
                ("public_ip", self.get_public_ip, s["ph_public_ip"]),
                ("ip_info", self.get_ip_info, s["ph_ip_info"]),
                ("user_and_hostname", self.get_user_hostname, s["ph_user_and_hostname"]),
                ("battery", self.get_battery, s["ph_battery"]),
                ("cpu_usage", self.get_cpu_usage, s["ph_cpu_usage"]),
                ("ram_usage", self.get_ram_usage, s["ph_ram_usage"]),
            ]),
            ("📅", s["cat_datetime"], [
                ("time", self.get_time, s["ph_time"]),
                ("date", self.get_date, s["ph_date"]),
                ("day_of_the_week", self.get_weekday, s["ph_day_of_the_week"]),
                ("data_and_time", self.get_date_time, s["ph_data_and_time"]),
                ("data_and_time_and_day_of_the_week", self.get_full_date_time_weekday, s["ph_data_and_time_and_day_of_the_week"]),
                ("moon_phase", self.get_moon_phase, s["ph_moon_phase"]),
                ("zodiac_sign", self.get_zodiac_sign, s["ph_zodiac_sign"]),
            ]),
            ("🌤", s["cat_weather"], [
                ("weather", self.get_weather_condition, s["ph_weather"]),
                ("outdoor_temperature", self.get_temperature, s["ph_outdoor_temperature"]),
                ("weather_and_temperature", self.get_weather_temp, s["ph_weather_and_temperature"]),
                ("weather_emoji", self.get_weather_emoji, s["ph_weather_emoji"]),
                ("feels_like", self.get_feels_like, s["ph_feels_like"]),
                ("humidity", self.get_humidity, s["ph_humidity"]),
                ("pressure", self.get_pressure, s["ph_pressure"]),
                ("wind_speed", self.get_wind_speed, s["ph_wind_speed"]),
            ]),
            ("❤️", s["cat_personal"], [
                ("my_crypto_address", self.get_crypto_address, s["ph_my_crypto_address"]),
                ("my_card_number", self.get_card_number, s["ph_my_card_number"]),
                ("my_donate_site", self.get_donate_site, s["ph_my_donate_site"]),
                ("my_channel", self.get_channel, s["ph_my_channel"]),
                ("my_social_network", self.get_social, s["ph_my_social_network"]),
            ]),
            ("🎵", s["cat_music"], [
                ("now_playing", self.get_now_playing, s["ph_now_playing"]),
                ("last_fm_user_and_now_playing", self.get_user_and_playing, s["ph_last_fm_user_and_now_playing"]),
                ("song_name", self.get_song_name, s["ph_song_name"]),
                ("song_artist", self.get_song_artist, s["ph_song_artist"]),
                ("last_fm_user", self.get_lastfm_user, s["ph_last_fm_user"]),
                ("lastfm_stats", self.get_lastfm_stats, s["ph_lastfm_stats"]),
            ]),
            ("🐙", s["cat_github"], [
                ("github_repos", self.get_github_repos, s["ph_github_repos"]),
                ("github_followers", self.get_github_followers, s["ph_github_followers"]),
            ]),
            ("💡", s["cat_fun"], [
                ("random_fact", self.get_random_fact, s["ph_random_fact"]),
                ("quote", self.get_quote, s["ph_quote"]),
                ("joke", self.get_joke, s["ph_joke"]),
                ("advice", self.get_advice, s["ph_advice"]),
                ("cat_fact", self.get_cat_fact, s["ph_cat_fact"]),
                ("kanye_quote", self.get_kanye_quote, s["ph_kanye_quote"]),
                ("affirmation", self.get_affirmation, s["ph_affirmation"]),
            ]),
        ]

    def _register_placeholders(self):
        for _, _, items in self._groups():
            for name, func, desc in items:
                utils.register_placeholder(name, func, desc)

    async def _fetch_json(self, url, params=None):
        try:
            async with self.session.get(url, params=params) as resp:
                if resp.status == 200:
                    return await resp.json(content_type=None)
        except Exception as e:
            logger.debug(f"Fetch error {url}: {e}")
        return None

    async def _get_rates(self):
        cache_key = "fx_rates"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        data = await self._fetch_json("https://open.er-api.com/v6/latest/USD")
        if data and data.get("result") == "success" and "rates" in data:
            rates = data["rates"]
            self.cache.set(cache_key, rates)
            return rates

        data = await self._fetch_json("https://www.cbr-xml-daily.ru/daily_json.js")
        if data and "Valute" in data:
            rates = {
                code: v["Value"] / v["Nominal"]
                for code, v in data["Valute"].items()
            }
            rates["RUB"] = 1.0
            self.cache.set(cache_key, rates)
            return rates

        return None

    async def _fmt_rate(self, code_from: str, code_to: str, digits: int = 2) -> str:
        rates = await self._get_rates()
        if not rates or code_from not in rates or code_to not in rates:
            return self.strings["rate_unavailable"].format(code_from)
        rate = rates[code_to] / rates[code_from]
        return self.strings["rate_pair"].format(code_from, rate, code_to, digits=digits)

    async def _get_crypto(self):
        cache_key = "crypto_prices"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        data = await self._fetch_json(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin,ethereum,toncoin", "vs_currencies": "rub,usd"},
        )
        if not data or "toncoin" not in data:
            data = await self._crypto_fallback()

        if data:
            self.cache.set(cache_key, data)
        return data

    async def _crypto_fallback(self):
        usd_rub = None
        rates = await self._get_rates()
        if rates and "RUB" in rates:
            usd_rub = rates["RUB"]

        data = {}
        ton = await self._fetch_json(
            "https://tonapi.io/v2/rates",
            params={"tokens": "ton", "currencies": "rub,usd"},
        )
        try:
            prices = ton["rates"]["TON"]["prices"]
            data["toncoin"] = {"rub": prices["RUB"], "usd": prices["USD"]}
        except (KeyError, TypeError):
            pass

        for symbol, key in (("BTCUSDT", "bitcoin"), ("ETHUSDT", "ethereum")):
            tick = await self._fetch_json(
                "https://api.binance.com/api/v3/ticker/price",
                params={"symbol": symbol},
            )
            try:
                usd = float(tick["price"])
                entry = {"usd": usd}
                if usd_rub:
                    entry["rub"] = usd * usd_rub
                data[key] = entry
            except (KeyError, TypeError, ValueError):
                pass

        return data or None

    async def _get_github(self):
        user = self.config["github_username"]
        if not user:
            return None

        cache_key = f"github_{user}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        data = await self._fetch_json(f"https://api.github.com/users/{user}")
        if not data or data.get("message"):
            return {}

        result = {
            "repos": data.get("public_repos", 0),
            "followers": data.get("followers", 0),
        }
        self.cache.set(cache_key, result)
        return result

    def _format_delta(self, delta: timedelta) -> str:
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        if days > 0:
            return self.strings["fmt_days"].format(days, hours, minutes)
        if hours > 0:
            return self.strings["fmt_hours"].format(hours, minutes)
        return self.strings["fmt_minutes"].format(minutes)

    def _weather_emoji_for(self, condition: str) -> str:
        c = condition.lower()
        if any(k in c for k in ("гроза", "thunder")):
            return "⛈️"
        if any(k in c for k in ("дожд", "ливень", "морос", "rain", "drizzle", "shower")):
            return "🌧️"
        if any(k in c for k in ("снег", "snow", "sleet")):
            return "❄️"
        if any(k in c for k in ("туман", "дымк", "fog", "mist", "haze")):
            return "🌫️"
        if any(k in c for k in ("пасмурн", "overcast", "облачн", "cloud")):
            return "☁️"
        if any(k in c for k in ("ясно", "солнц", "clear", "sunny")):
            return "☀️"
        return "🌡️"

    def _moon_phase(self) -> str:
        s = self.strings
        ref = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
        days = (datetime.now(timezone.utc) - ref).total_seconds() / 86400
        age = days % 29.53058867
        phases = [
            (1.85, s["moon_new"]),
            (5.54, s["moon_waxing_crescent"]),
            (9.23, s["moon_first_quarter"]),
            (12.92, s["moon_waxing_gibbous"]),
            (16.61, s["moon_full"]),
            (20.30, s["moon_waning_gibbous"]),
            (24.00, s["moon_last_quarter"]),
            (27.69, s["moon_waning_crescent"]),
        ]
        for limit, name in phases:
            if age <= limit:
                return name
        return s["moon_new"]

    def _zodiac_sign(self) -> str:
        s = self.strings
        now = datetime.now(self.tz)
        md = now.month * 100 + now.day
        bounds = [
            (120, s["zodiac_capricorn"]), (219, s["zodiac_aquarius"]), (321, s["zodiac_pisces"]),
            (420, s["zodiac_aries"]), (521, s["zodiac_taurus"]), (621, s["zodiac_gemini"]),
            (723, s["zodiac_cancer"]), (823, s["zodiac_leo"]), (923, s["zodiac_virgo"]),
            (1023, s["zodiac_libra"]), (1122, s["zodiac_scorpio"]), (1222, s["zodiac_sagittarius"]),
            (1232, s["zodiac_capricorn"]),
        ]
        for bound, sign in bounds:
            if md <= bound:
                return sign
        return s["zodiac_capricorn"]

    # ==================== Профиль ====================

    async def get_premium_check(self):
        if not self.me.premium:
            return self.strings["no_premium"]

        until = self.full_me.full_user.premium_until
        if not until or until < time.time():
            return self.strings["premium_expired"]

        end_date = datetime.fromtimestamp(until, tz=self.tz)
        days_left = (end_date.date() - datetime.now(self.tz).date()).days
        formatted = end_date.strftime("%d.%m.%Y")
        return self.strings["premium_left"].format(formatted, days_left)

    async def get_username(self):
        return f"@{self.me.username}" if self.me.username else self.strings["no_value"]

    async def get_name(self):
        return self.me.first_name or self.strings["no_value"]

    async def get_surname(self):
        return self.me.last_name or self.strings["no_value"]

    async def get_bio(self):
        return self.full_me.full_user.about or self.strings["no_bio"]

    async def get_user_id(self):
        return str(self.me.id)

    async def get_phone(self):
        phone = getattr(self.me, "phone", None)
        if not phone:
            try:
                full = await self._client(GetFullUserRequest(self.me))
                phone = full.full_user.phone
            except Exception:
                phone = None
        return phone or self.strings["hidden"]

    async def get_dc_id(self):
        try:
            return str(self._client.session.dc_id)
        except Exception:
            return self.strings["unknown"]

    async def get_stars(self):
        try:
            result = await self._client(GetStarsStatusRequest("me"))
            stars = result.balance.amount if result and result.balance else 0
            return f"{stars:,}".replace(",", " ") if stars else "0"
        except Exception:
            return "0"

    # ==================== Валюты и крипта ====================

    async def get_usd_to_rub(self):
        return await self._fmt_rate("USD", "RUB")

    async def get_rub_to_usd(self):
        return await self._fmt_rate("RUB", "USD", 4)

    async def get_eur_to_rub(self):
        return await self._fmt_rate("EUR", "RUB")

    async def get_rub_to_eur(self):
        return await self._fmt_rate("RUB", "EUR", 4)

    async def get_cny_to_rub(self):
        return await self._fmt_rate("CNY", "RUB")

    async def get_kzt_to_rub(self):
        return await self._fmt_rate("KZT", "RUB")

    async def get_rub_to_kzt(self):
        return await self._fmt_rate("RUB", "KZT", 2)

    async def get_usdt_to_rub(self):
        return await self.get_usd_to_rub()

    async def get_rub_to_usdt(self):
        return await self.get_rub_to_usd()

    async def get_ton_to_rub(self):
        data = await self._get_crypto()
        if data and "toncoin" in data and "rub" in data["toncoin"]:
            rate = data["toncoin"]["rub"]
            return self.strings["rate_pair"].format("TON", rate, "RUB", digits=2)
        return self.strings["rate_unavailable"].format("TON")

    async def get_rub_to_ton(self):
        data = await self._get_crypto()
        if data and "toncoin" in data and "rub" in data["toncoin"]:
            rate = data["toncoin"]["rub"]
            if rate > 0:
                return self.strings["rate_pair"].format("RUB", 1 / rate, "TON", digits=6)
        return self.strings["rate_generic_unavailable"]

    async def get_btc_to_rub(self):
        data = await self._get_crypto()
        if data and "bitcoin" in data and "rub" in data["bitcoin"]:
            rate = data["bitcoin"]["rub"]
            return self.strings["rate_pair"].format("BTC", rate, "RUB", digits=0)
        return self.strings["rate_unavailable"].format("BTC")

    async def get_eth_to_rub(self):
        data = await self._get_crypto()
        if data and "ethereum" in data and "rub" in data["ethereum"]:
            rate = data["ethereum"]["rub"]
            return self.strings["rate_pair"].format("ETH", rate, "RUB", digits=0)
        return self.strings["rate_unavailable"].format("ETH")

    async def get_stars_to_rub(self):
        rates = await self._get_rates()
        if rates and "RUB" in rates:
            return self.strings["rate_pair"].format("Star", STAR_USD * rates["RUB"], "RUB", digits=2)
        return "1 Star ≈ 1.98 RUB"

    async def get_stars_to_ton(self):
        data = await self._get_crypto()
        if data and "toncoin" in data and "usd" in data["toncoin"]:
            ton_usd = data["toncoin"]["usd"]
            if ton_usd > 0:
                return self.strings["rate_pair"].format("Star", STAR_USD / ton_usd, "TON", digits=4)
        return "1 Star ≈ 0.006 TON"

    async def get_stars_to_usdt(self):
        return self.strings["rate_pair"].format("Star", STAR_USD, "USDT", digits=3)

    # ==================== Система и сеть ====================

    async def get_os_uptime(self):
        boot = datetime.fromtimestamp(psutil.boot_time())
        return self._format_delta(datetime.now() - boot)

    async def get_internet_usage(self):
        try:
            net = psutil.net_io_counters()
            sent_gb = net.bytes_sent // (1024**3)
            recv_gb = net.bytes_recv // (1024**3)
            return self.strings["net_usage"].format(sent_gb, recv_gb)
        except Exception:
            return self.strings["net_usage"].format(0, 0)

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
                async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
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

        return self.strings["speedtest_unavailable"]

    async def get_shell(self):
        return os.environ.get("SHELL", self.strings["unknown"]).split("/")[-1]

    async def get_gpu(self):
        return self.strings["gpu_na"]

    async def get_disk(self):
        try:
            usage = psutil.disk_usage("/")
            percent = (usage.used / usage.total) * 100
            used_gb = usage.used // (1024**3)
            total_gb = usage.total // (1024**3)
            return f"{used_gb} GB / {total_gb} GB ({percent:.1f}%)"
        except Exception:
            return self.strings["disk_unavailable"]

    async def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return self.strings["unknown"]

    async def get_public_ip(self):
        cache_key = "public_ip"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        data = await self._fetch_json("https://api.ipify.org?format=json")
        if data and "ip" in data:
            self.cache.set(cache_key, data["ip"])
            return data["ip"]
        return self.strings["unknown"]

    async def get_ip_info(self):
        cache_key = "ip_info"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        data = await self._fetch_json(
            "http://ip-api.com/json/",
            params={"lang": "ru", "fields": "status,country,city,isp"},
        )
        if data and data.get("status") == "success":
            city = data.get("city") or "—"
            country = data.get("country") or "—"
            isp = data.get("isp") or ""
            result = f"{city}, {country}" + (f" · {isp}" if isp else "")
            self.cache.set(cache_key, result)
            return result
        return await self.get_public_ip()

    async def get_user_hostname(self):
        try:
            user = os.environ.get("USER") or os.environ.get("USERNAME") or "user"
        except Exception:
            user = "user"
        host = platform.node() or self.strings["unknown"]
        return f"{user}@{host}"

    async def get_battery(self):
        try:
            battery = psutil.sensors_battery()
        except Exception:
            battery = None

        if battery is None:
            return self.strings["no_battery"]

        percent = round(battery.percent)
        plugged = getattr(battery, "power_plugged", False)
        emoji = "⚡" if plugged else ("🪫" if percent <= 20 else "🔋")
        return f"{emoji} {percent}%"

    async def get_cpu_usage(self):
        try:
            return f"{psutil.cpu_percent(interval=None):.0f}%"
        except Exception:
            return self.strings["na"]

    async def get_ram_usage(self):
        try:
            vm = psutil.virtual_memory()
            used_mb = vm.used // (1024**2)
            total_mb = vm.total // (1024**2)
            return f"{used_mb} MB / {total_mb} MB ({vm.percent:.0f}%)"
        except Exception:
            return self.strings["na"]

    # ==================== Дата и погода ====================

    async def get_time(self):
        return datetime.now(self.tz).strftime(self.config["time_format"])

    async def get_date(self):
        return datetime.now(self.tz).strftime(self.config["date_format"])

    async def get_weekday(self):
        weekdays = self.strings["weekdays"].split(",")
        return weekdays[datetime.now(self.tz).weekday()]

    async def get_date_time(self):
        now = datetime.now(self.tz)
        return now.strftime(f"{self.config['date_format']} {self.config['time_format']}")

    async def get_full_date_time_weekday(self):
        now = datetime.now(self.tz)
        dt = now.strftime(f"{self.config['date_format']} {self.config['time_format']}")
        weekdays = self.strings["weekdays"].split(",")
        return f"{dt} ({weekdays[now.weekday()]})"

    async def get_moon_phase(self):
        return self._moon_phase()

    async def get_zodiac_sign(self):
        return self._zodiac_sign()

    async def get_weather_condition(self):
        data = await self._get_weather_data()
        return data.get("condition", self.strings["w_condition_na"])

    async def get_temperature(self):
        data = await self._get_weather_data()
        return data.get("temp", self.strings["w_temp_na"])

    async def get_weather_temp(self):
        data = await self._get_weather_data()
        return data.get("weather_temp", self.strings["w_unavailable"])

    async def get_weather_emoji(self):
        data = await self._get_weather_data()
        return self._weather_emoji_for(data.get("condition", ""))

    async def get_feels_like(self):
        data = await self._get_weather_data()
        return data.get("feels_like", self.strings["w_temp_na"])

    async def get_humidity(self):
        data = await self._get_weather_data()
        return data.get("humidity", self.strings["w_humidity_na"])

    async def get_pressure(self):
        data = await self._get_weather_data()
        return data.get("pressure", self.strings["w_pressure_na"])

    async def get_wind_speed(self):
        data = await self._get_weather_data()
        return data.get("wind", self.strings["w_wind_na"])

    async def _get_weather_data(self):
        city = self.config["weather_city"]
        cache_key = f"weather_{city}"

        cached = self.cache.get(cache_key)
        if cached:
            return cached

        default = {
            "condition": self.strings["w_condition_na"],
            "temp": self.strings["w_temp_na"],
            "weather_temp": self.strings["w_unavailable"],
            "humidity": self.strings["w_humidity_na"],
            "pressure": self.strings["w_pressure_na"],
            "wind": self.strings["w_wind_na"],
            "feels_like": self.strings["w_temp_na"],
        }

        try:
            url = f"http://wttr.in/{city}?format=j1&lang=ru"
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"wttr.in status {resp.status}")

                data = await resp.json(content_type=None)
                c = data.get("current_condition", [{}])[0]

                lang_ru_list = c.get("lang_ru", [])
                condition = lang_ru_list[0].get("value") if lang_ru_list else None

                if not condition:
                    weather_desc = c.get("weatherDesc", [])
                    condition = (
                        weather_desc[0].get("value") if weather_desc else self.strings["w_condition_na"]
                    )

                try:
                    hpa = float(c.get("pressure", 0))
                    if self.config["pressure_unit"] == "гПа":
                        pressure_str = self.strings["unit_hpa"].format(f"{hpa:.0f}")
                    else:
                        pressure_str = self.strings["unit_mmhg"].format(round(hpa * 0.750062))
                except (TypeError, ValueError):
                    pressure_str = self.strings["na"]

                try:
                    kmph = float(c.get("windspeedKmph", 0))
                    if self.config["wind_unit"] == "м/с":
                        wind_str = self.strings["unit_ms"].format(f"{kmph * 0.277778:.1f}")
                    else:
                        wind_str = self.strings["unit_kmh"].format(f"{kmph:.0f}")
                except (TypeError, ValueError):
                    wind_str = self.strings["na"]

                weather_data = {
                    "condition": condition,
                    "temp": f"{c.get('temp_C', 'N/A')}°C",
                    "weather_temp": f"{self._weather_emoji_for(condition)} {condition}, {c.get('temp_C', 'N/A')}°C",
                    "humidity": f"{c.get('humidity', 'N/A')}%",
                    "pressure": pressure_str,
                    "wind": wind_str,
                    "feels_like": f"{c.get('FeelsLikeC', 'N/A')}°C",
                }

                self.cache.set(cache_key, weather_data)
                return weather_data

        except Exception as e:
            logger.debug(f"Ошибка получения погоды для {city}: {e}")

        self.cache.set(cache_key, default)
        return default

    # ==================== Личное ====================

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

    # ==================== Музыка ====================

    async def get_lastfm_user(self):
        return self.config["lastfm_user"] or self.strings["not_specified"]

    async def get_now_playing(self):
        track = await self._get_current_track()
        if not track:
            return self.strings["nothing_playing"]
        return f"🎵 <b>{track['name']}</b> — {track['artist']}"

    async def get_user_and_playing(self):
        user = await self.get_lastfm_user()
        track = await self._get_current_track()
        if not track:
            return f"{user}: {self.strings['nothing_playing']}"
        return f"{user}: {track['name']} — {track['artist']}"

    async def get_song_name(self):
        track = await self._get_current_track()
        return track["name"] if track else self.strings["dash"]

    async def get_song_artist(self):
        track = await self._get_current_track()
        return track["artist"] if track else self.strings["dash"]

    async def get_lastfm_stats(self):
        user = self.config["lastfm_user"]
        if not user:
            return self.strings["specify_lastfm"]

        cache_key = f"lastfm_stats_{user}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        api_key = self.config["lastfm_api_key"]

        data = await self._fetch_json(
            "https://ws.audioscrobbler.com/2.0/",
            params={
                "method": "user.getinfo",
                "user": user,
                "api_key": api_key,
                "format": "json",
            },
        )
        if data and "user" in data:
            result = self.strings["scrobbles"].format(data["user"]["playcount"])
            self.cache.set(cache_key, result)
            return result

        return self.strings["lastfm_stats_unavailable"]

    async def _get_current_track(self):
        user = self.config["lastfm_user"]
        if not user:
            return None

        cache_key = f"lastfm_track_{user}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        api_key = self.config["lastfm_api_key"]

        data = await self._fetch_json(
            "https://ws.audioscrobbler.com/2.0/",
            params={
                "method": "user.getrecenttracks",
                "user": user,
                "api_key": api_key,
                "format": "json",
                "limit": 1,
            },
        )
        tracks = (data or {}).get("recenttracks", {}).get("track", [])

        if tracks:
            track = tracks[0]
            now_playing = "@attr" in track and "nowplaying" in track["@attr"]

            result = {
                "name": track["name"],
                "artist": track["artist"]["#text"],
                "now_playing": now_playing,
            }
            self.cache.set(cache_key, result)
            return result

        return None

    # ==================== GitHub ====================

    async def get_github_repos(self):
        stats = await self._get_github()
        if stats is None:
            return self.strings["specify_github"]
        if not stats:
            return self.strings["github_not_found"]
        return self.strings["gh_repos"].format(stats["repos"])

    async def get_github_followers(self):
        stats = await self._get_github()
        if stats is None:
            return self.strings["specify_github"]
        if not stats:
            return self.strings["github_not_found"]
        return self.strings["gh_followers"].format(stats["followers"])

    # ==================== Факты, цитаты и прочее ====================

    async def get_random_fact(self):
        data = await self._fetch_json(
            "https://uselessfacts.jsph.pl/api/v2/facts/random",
            params={"language": "ru"},
        )
        if data and data.get("text"):
            return self.strings["fact_prefix"].format(data["text"])
        return self.strings["fact_unavailable"]

    async def get_quote(self):
        data = await self._fetch_json("https://zenquotes.io/api/random")
        if data and isinstance(data, list) and data[0].get("q"):
            return self.strings["quote_fmt"].format(data[0]["q"], data[0].get("a", "?"))
        return self.strings["quote_unavailable"]

    async def get_joke(self):
        data = await self._fetch_json(
            "https://v2.jokeapi.dev/joke/Any",
            params={"type": "single", "safe-mode": ""},
        )
        if data and not data.get("error") and data.get("joke"):
            return self.strings["joke_prefix"].format(data["joke"])
        return self.strings["joke_unavailable"]

    async def get_advice(self):
        data = await self._fetch_json("https://api.adviceslip.com/advice")
        slip = (data or {}).get("slip") or {}
        if slip.get("advice"):
            return self.strings["advice_prefix"].format(slip["advice"])
        return self.strings["advice_unavailable"]

    async def get_cat_fact(self):
        data = await self._fetch_json("https://catfact.ninja/fact")
        if data and data.get("fact"):
            return self.strings["catfact_prefix"].format(data["fact"])
        return self.strings["catfact_unavailable"]

    async def get_kanye_quote(self):
        data = await self._fetch_json("https://api.kanye.rest")
        if data and data.get("quote"):
            return self.strings["kanye_prefix"].format(data["quote"])
        return self.strings["quote_unavailable"]

    async def get_affirmation(self):
        data = await self._fetch_json("https://www.affirmations.dev/")
        if data and data.get("affirmation"):
            return self.strings["affirmation_prefix"].format(data["affirmation"])
        return self.strings["affirmation_unavailable"]

    # ==================== Lifecycle ====================

    async def on_unload(self):
        utils.unregister_placeholders(type(self).__name__)
        await self.session.close()
