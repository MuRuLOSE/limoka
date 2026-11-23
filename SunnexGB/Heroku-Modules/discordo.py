# Важно: я утерял релиз версию,но постарался доработать пре-релиз версию.
# requires: pillow cairosvg aiohttp
# meta banner: https://github.com/SunnexGB/Heroku-Modules/blob/main/Assets/Discordo/Discordo.png?raw=true
# meta pic: https://github.com/SunnexGB/Heroku-Modules/blob/main/Assets/Discordo/Discordo.png?raw=true
# meta developer: @H_SunMods
# scope: heroku_only

import contextlib
import json
import logging
import time
from .. import loader, utils
logger = logging.getLogger(__name__)


@loader.tds
class Discordo(loader.Module):
    """Show your activity on discord"""

    strings = {
        'name': 'Discordo',
        'banner_not_loaded': '<b>Banner is not loaded.</b> Details in logs.',
        'guide': """<h1>How to start using the module?</h1>
<p></p>
<h2>1.Getting Discord UserId</h2>
<p>Go to Settings =&gt; developer mode =&gt; enable it. Then click on our profile and copy our ID from there</p>
<p></p>
<p>After that write <code>{prefix}cfg Discordo user_id 15564...225....468</code>, where <code>15564...225....468</code> is your id.
</p>
<p></p>
<h2>2.Join Lanyard to track activity</h2>
<p></p>
<p></p>
<tg-button-row><tg-button type="url" url="https://discord.gg/lanyard">Join!!!!</tg-button></tg-button-row>
""",
        'no_data': '<b>Could not get data from API or use dsguide command</b>',
        'nothing': '<b>No activities at the moment...</b>',
        'ctheme_usage': '<b>Usage: <code>.ctheme name {{"key": "value"}}</code>\n\nColors can be passed as text, reply to message or .json file.\nIf not specified, selected banner is used.\n\nbanner configuration:</b> {keys}',
        'ctheme_unknown_banner': '<b>No such banner.</b>',
        'ctheme_bad_json': '<b>Need format:</b> <code>{"key": "value"}</code>',
        'ctheme_error': '<b>Colors not saved.</b> Details in logs.',
        'ctheme_saved': '<b>Colors for custom saved.</b>',
        'theme_btn': '{theme_name}',
        'theme_btn_selected': '{theme_name} <',
        'theme_chosen': '{theme_name}',
        'preview_show': 'Show preview {cursor}',
        'preview_hide': 'Hide preview {cursor}',
        'author_btn': 'Author: {name}',
        'author_btn_cursor': 'Author {cursor}: {name}',
        'user_id_doc': 'Your discord userId',
        'banners_doc': 'default banners that will be displayed with {prefix}dsnow command',
        'user_banners_doc': 'Pool of banners that will be displayed with {prefix}dsnow command',
        'theme_doc': 'Set custom theme',
        'font_url_doc': 'Set custom font',
        'custom_message_doc': 'Internal placeholders: {name} - activity name, {details} - activity details, {timestamp} - activity duration',
        'def_inf': '<strong>app name:</strong> <code>{name}</code><strong>\ndetails:</strong> <code>{details}</code>\n<tg-emoji emoji-id="5350737576674243497">💠</tg-emoji><code>{timestamp}</code>',
        'log_preview': 'Could not change preview',
        'log_colors': 'Invalid custom colors: {errors}',
    }

    strings_ru = {
        '_cls_doc': 'Показывает вашу активность в дискорде',
        'banner_not_loaded': '<b>Баннер не загружен.</b> Подробности в логах.',
        'guide': """<h1>Как начать пользоватся модулем?</h1>
<p></p>
<h2>1.Получение Discord UserId</h2>
<p>Переходим в Настройки =&gt; режим разработчика =&gt; включаем его. После чего нажимаем на наш профиль и копируем уже от туда наш ID</p>
<p></p>
<p>После чего прописываем <code>{prefix}cfg Discordo user_id 15564...225....468</code>, где <code>15564...225....468</code> это ваш id.
</p>
<p></p>
<h2>2.Войти в Lanyard для отслеживания активности</h2>
<p></p>
<p></p>
<tg-button-row><tg-button type="url" url="https://discord.gg/lanyard">Войти!!!!</tg-button></tg-button-row>""",
        'no_data': '<b>Не удалось получить данные от API или воспользуйтесь командой dsguide</b>',
        'nothing': '<b>В данный момент активностий не наблюдается...</b>',
        'ctheme_usage': '<b>Использование: <code>.ctheme название {{"ключ": "значение"}}</code>\n\nЦвета можно передать текстом, ответом на сообщение или на .json файл.\nЕсли не указать названия берётся выбранный баннер.\n\nконфигурация баннера:</b> {keys}',
        'ctheme_unknown_banner': '<b>Такого баннера нет.</b>',
        'ctheme_bad_json': '<b>Нужен вид:</b> <code>{"ключ": "значение"}</code>',
        'ctheme_error': '<b>Цвета не сохранены.</b> Подробности в логах.',
        'ctheme_saved': '<b>Цвета для custom сохранены.</b>',
        'theme_btn': '{theme_name}',
        'theme_btn_selected': '{theme_name} <',
        'theme_chosen': '{theme_name}',
        'preview_show': 'Показать превью {cursor}',
        'preview_hide': 'Скрыть превью {cursor}',
        'author_btn': 'Автор: {name}',
        'author_btn_cursor': 'Автор {cursor}: {name}',
        'user_id_doc': 'Ваш discord userId',
        'banners_doc': 'дефолтные баннера которые будут отображатся при команде {prefix}dsnow',
        'user_banners_doc': 'Пулл баннеров который будет отображатся при команде {prefix}dsnow',
        'theme_doc': 'Задать кастомную тему',
        'font_url_doc': 'Задать свой шрифт',
        'custom_message_doc': 'Внутренние плейсхолдеры: {name} - название активности, {details} - детали активности, {timestamp} - длительность активности',
        'def_inf': '<strong>сейчас в:</strong> <code>{name}</code><strong>\nдоп.инфо:</strong> <code>{details}</code>\n<tg-emoji emoji-id="5350737576674243497">💠</tg-emoji><code>{timestamp}</code>',
        'log_preview': 'Не удалось изменить превью',
        'log_colors': 'Неверные цвета custom: {errors}',
    }

    def __init__(self):
        self.def_banner_url = "https://github.com/SunnexGB/Heroku-Modules/raw/refs/heads/main/Assets/Discordo/banner.py"
        self.banner_loader = "https://github.com/SunnexGB/Heroku-Modules/raw/refs/heads/main/Assets/Discordo/banner_loader.py"
        self.cfg_btns = "https://github.com/SunnexGB/Heroku-Modules/raw/refs/heads/main/Assets/Discordo/cfg_btns.py"
        self.core_urls = [url.strip() for url in self.def_banner_url.split(",")]
        self.lanyard_api = "https://api.lanyard.rest/v1/users/"
        self.banner_lib = None
        self.btns_lib = None
        self.banners = {}
        self.banner_info = {}
        self.custom_themes = {}
        self.banner_titles = ["Discordo"]
        self.theme_names = ["dark", "light", "custom"]

        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "user_id",
                None,
                lambda: self.strings["user_id_doc"],
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "banners",
                "Discordo",
                lambda: self.strings["banners_doc"].format(prefix=self.get_prefix()),
                validator=loader.validators.Choice(self.banner_titles),
                on_change=self.on_banner_change,
            ),
            loader.ConfigValue(
                "user_banners",
                [],
                lambda: self.strings["user_banners_doc"].format(prefix=self.get_prefix()),
                validator=loader.validators.Series(),
                on_change=self.reload_banners,
            ),
            loader.ConfigValue(
                "theme",
                "dark",
                lambda: self.strings["theme_doc"],
                validator=loader.validators.Choice(self.theme_names),
            ),
            loader.ConfigValue(
                "font_url",
                None,
                lambda: self.strings["font_url_doc"],
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "custom_message",
                None,
                doc=lambda: self.strings["custom_message_doc"],
            ),
        )

    async def client_ready(self, client, db):
        self.custom_themes = self.get("custom_themes", {})
        self.banner_lib = await self.import_lib(
            self.banner_loader,
            suspend_on_error=True,
        )
        self.btns_lib = await self.import_lib(
            self.cfg_btns,
            suspend_on_error=True,
        )

        name = self.strings["name"]
        self.btns_lib.set_cfg_btns(f"{name} theme", self.theme_btns, mod_option=True)
        self.btns_lib.set_cfg_btns(f"{name} banners", self.banners_btns)
        self.btns_lib.set_cfg_btns(f"{name} user_banners", self.user_banners_btns)
        await self.load_banners()
        self.restore_saved_choices()

    async def on_unload(self):
        self.btns_lib.rm_cfg_btns(self.strings["name"])

    async def load_banners(self):
        cache = self.get("banner_cache", {})
        self.banners = {}
        self.banner_info = {}
        for url in self.core_urls + list(self.config["user_banners"]):
            banner = await self.banner_lib.load_banner(url)
            if banner is None:
                info = cache.get(url)
                if info:
                    title = self.pick_title(url, info["title"])
                    self.banner_info[title] = dict(info, title=title)
                continue

            title = self.pick_title(url, banner.title)
            self.banners[title] = banner
            self.banner_info[title] = {
                "url": url,
                "title": title,
                "author_name": banner.author_name,
                "author_url": banner.author_url,
                "preview": banner.preview_url,
                "theme_names": banner.theme_names,
                "color_names": banner.color_names,
            }

        self.set("banner_cache", {info["url"]: info for info in self.banner_info.values()})
        if self.banner_info:
            self.refresh_choice("banners", self.banner_titles, list(self.banner_info))
            self.refresh_banner_choices()

    def pick_title(self, url, banner_title):
        if url == self.core_urls[0]:
            return "Discordo"
        if banner_title in self.banner_info or banner_title == "Discordo":
            return f"{banner_title} ({len(self.banner_info) + 1})"
        return banner_title

    async def reload_banners(self):
        if self.banner_lib is not None:
            await self.load_banners()

    def current_banner(self):
        return self.banners.get(self.config["banners"])

    def current_info(self):
        return self.banner_info.get(self.config["banners"])

    async def on_banner_change(self):
        self.refresh_banner_choices()

    def refresh_banner_choices(self):
        info = self.current_info()
        if info is not None:
            self.refresh_choice("theme", self.theme_names, info["theme_names"] + ["custom"])

    def refresh_choice(self, option_name, choice_list, new_values):
        choice_list[:] = new_values
        if self.config[option_name] not in new_values:
            self.config[option_name] = new_values[0]

    def restore_saved_choices(self):
        saved_config = self.get("__config__", {})
        with contextlib.suppress(loader.validators.ValidationError):
            self.config["banners"] = saved_config.get("banners", self.config["banners"])
        self.refresh_banner_choices()
        with contextlib.suppress(loader.validators.ValidationError):
            self.config["theme"] = saved_config.get("theme", self.config["theme"])

    def theme_btns(self, form_id):
        return [[self.theme_btn(theme_name)] for theme_name in self.theme_names]

    def banners_btns(self, form_id):
        info = self.current_info()
        return [
            [self.preview_btn(form_id, info)],
            [self.author_btn(info, "author_btn")],
        ]

    def user_banners_btns(self, form_id):
        kb = []
        for info in self.banner_info.values():
            if info["url"] in self.config["user_banners"]:
                kb += [
                    [self.preview_btn(form_id, info)],
                    [self.author_btn(info, "author_btn_cursor")],
                ]
        return kb

    def theme_btn(self, theme_name):
        key_msg = "theme_btn_selected" if theme_name == self.config["theme"] else "theme_btn"
        return {
            "text": self.strings[key_msg].format(theme_name=theme_name.capitalize()),
            "callback": self.choose_theme,
            "args": (theme_name,),
        }

    async def choose_theme(self, call, theme_name):
        self.config["theme"] = theme_name
        await call.answer(self.strings["theme_chosen"].format(theme_name=theme_name.capitalize()))

    def preview_link(self, url):
        return f'<a href="{utils.escape_html(url)}">\u200b</a>'

    def preview_msg(self, url, title, form_msg):
        key_msg = "preview_hide" if self.preview_link(url) in form_msg else "preview_show"
        return self.strings[key_msg].format(cursor=title)

    def preview_btn(self, form_id, info):
        if not info or not info["preview"]:
            return None

        form_msg = self.btns_lib.get_form(form_id).get("text", "")
        return {
            "text": self.preview_msg(info["preview"], info["title"], form_msg),
            "callback": self.toggle_preview,
            "args": (info["preview"], info["title"]),
        }

    async def toggle_preview(self, call, url, title):
        form = call.form
        link = self.preview_link(url)
        is_shown = link in form["text"]
        text = form["text"]
        for info in self.banner_info.values():
            if info["preview"]:
                text = text.replace(self.preview_link(info["preview"]), "")
        if not is_shown:
            text = link + text
        for line in form["buttons"]:
            for btn in line:
                if btn.get("callback") == self.toggle_preview:
                    btn["text"] = self.preview_msg(*btn["args"], text)
        old_text = form["text"]
        old_flag = form.get("disable_web_page_preview")
        form["text"] = text
        form["disable_web_page_preview"] = is_shown
        try:
            await call.edit(text, reply_markup=form["buttons"], disable_web_page_preview=is_shown)
        except Exception:
            logger.exception(self.strings["log_preview"])
            form["text"] = old_text
            form["disable_web_page_preview"] = old_flag
            await call.answer(url, show_alert=True)

    def author_btn(self, info, key_msg):
        if not info or not info["author_name"]:
            return None

        autor_key_msg_idk = self.strings[key_msg].format(name=info["author_name"], cursor=info["title"])
        if info["author_url"]:
            return {
                "text": autor_key_msg_idk,
                "url": info["author_url"],
            }
        return {
            "text": autor_key_msg_idk,
            "callback": self.ignore_press,
        }

    async def ignore_press(self, call):
        await call.answer()

    async def data_lanyard(self):
        response = await self.banner_lib.dl_json(self.lanyard_api + self.config["user_id"])
        if not response or not response.get("success"):
            return None
        return response.get("data")

    def format_timestamp(self, activity):
        stamps = activity.get("timestamps", {})
        start = stamps.get("start")
        end = stamps.get("end")

        if not start:
            return ""

        elapsed = max(0, time.time() - start / 1000)

        if end:
            duration = (end - start) / 1000
            position = min(elapsed, duration)
            minutes_pos = int(position // 60)
            seconds_pos = int(position % 60)
            minutes_dur = int(duration // 60)
            seconds_dur = int(duration % 60)
            return f'{minutes_pos:02}:{seconds_pos:02}/{minutes_dur:02}:{seconds_dur:02}'

        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        if hours:
            return f'{hours}:{minutes:02}:{seconds:02}'
        return f'{minutes}:{seconds:02}'

    @loader.command(ru_doc="гайд как начать пользоватся модулем")
    async def dsguide(self, message):
        """usage guide for module"""
        await utils.answer(message, rich_message=self.strings['guide'].format(prefix=self.get_prefix()))

    @loader.command(ru_doc="показать дискорд активность")
    async def dsnow(self, message):
        """show discord activity"""
        banner = self.current_banner()
        if banner is None:
            await utils.answer(message, self.strings['banner_not_loaded'])
            return

        data = await self.data_lanyard()
        if not data:
            await utils.answer(message, self.strings['no_data'])
            return

        theme_name = self.config["theme"]
        custom_colors = self.custom_themes.get(self.config["banners"], {})
        error_syntax = banner.fetch_cfg_error_syntax(theme_name, custom_colors)
        if error_syntax:
            logger.error(self.strings['log_colors'].format(errors="; ".join(error_syntax)))
        image = await banner.render(
            data,
            theme_name=theme_name,
            custom_colors=custom_colors,
            font_url=self.config["font_url"],
        )
        activities = data.get("activities", [])
        if not activities:
            await utils.answer(message, self.strings['nothing'])
            return

        activity = activities[0]
        msg_format = self.config["custom_message"] or self.strings['def_inf']
        name = activity.get("name", "")
        details = activity.get("details", "")
        timestamp = self.format_timestamp(activity)
        placeholders = msg_format.format(
            name=name, 
            details=details, 
            timestamp=timestamp
            )
        if image:
            await utils.answer(message, placeholders, file=image)
        else:
            await utils.answer(message, placeholders)

    @loader.command(ru_doc='<название> {"ключ": "значение"} - цвета для баннера (текстом, ответом на сообщение или .json файл)')
    async def ctheme(self, message):
        """<name> {"key": "value"} - custom colors for a banner (in the command, as a reply to a message or to a .json file)"""
        args = utils.get_args_raw(message)
        json_start = args.find("{")
        if json_start == -1:
            title_str, json_str = args, ""
        else:
            title_str, json_str = args[:json_start], args[json_start:]
        title = self.fetch_title(title_str.strip())
        if title is None:
            await utils.answer(
                message,
                self.strings["ctheme_unknown_banner"].format(
                    titles=utils.escape_html(", ".join(self.banner_info)),
                ),
            )
            return

        await self.save_theme(message, title, json_str)

    def fetch_title(self, name):
        name = name or self.config["banners"]
        for title in self.banner_info:
            if title.lower() == name.lower():
                return title
        return None

    async def save_theme(self, message, title, json_str):
        reply = await message.get_reply_message()
        if not json_str and reply is not None:
            if reply.file:
                json_str = (await reply.download_media(bytes)).decode("utf-8", errors="ignore")
            else:
                json_str = reply.raw_text or ""

        info = self.banner_info[title]
        if not json_str.strip():
            await utils.answer(
                message,
                self.strings["ctheme_usage"].format(
                    titles=utils.escape_html(", ".join(self.banner_info)),
                    keys=utils.escape_html(", ".join(info["color_names"])),
                ),
            )
            return
        try:
            colors = json.loads(json_str)
        except ValueError:
            colors = None
        if not isinstance(colors, dict):
            await utils.answer(message, self.strings["ctheme_bad_json"])
            return

        error_syntax = list(self.banner_lib.allowed_color_syntax(colors, info["color_names"]))
        if error_syntax:
            logger.error(self.strings["log_colors"].format(errors="; ".join(error_syntax)))
            await utils.answer(message, self.strings["ctheme_error"])
            return

        self.custom_themes[title] = colors
        self.set("custom_themes", self.custom_themes)
        if title == self.config["banners"]:
            self.config["theme"] = "custom"
        await utils.answer(message, self.strings["ctheme_saved"].format(count=len(colors)))