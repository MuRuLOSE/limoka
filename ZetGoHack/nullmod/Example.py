# Этот модуль - наглядный пример для интересующихся разработчиков
# Здесь (TODO: планируется добавить и объяснить в принципе все функции
# и возможности модулей... мета теги, инлайн и т.д.), чтобы Ты смог 
# начать создавать модули и стал их разработчиком. Добро пожаловать!


# ⬇️ Обрати внимание! ⬇️

# В принципе, этот код не планируется адаптировать в пошаговый гайд.
# Скорее, я сделал справочник по функционалу и возможностям модулей с
# теорией и примерами использования.

# То есть, если у тебя появился вопрос "А как сделать это?", "А как
# это работает?" - этот пример поможет тебе найти ответ.

# ⬆️ Обрати внимание! ⬆️


# ⬇️ Обновление (Heroku 2.1.0+) ⬇️

# С Heroku 2.1.0 инлайн-бот работает через herokutl, а не через aiogram.
# aiogram оставлен только ради обратной совместимости - self.inline.bot
# по-прежнему доступен для тех, кто хочет работать с ботом напрямую

# ⬆️ Обновление (Heroku 2.1.0+) ⬆️


# Каждая "глава" отмечена тегами # region и # endregion. Если вы читаете
# этот код в редакторе с Code View/Minimap (например, в VSCode), вы можете
# ориентироваться по этим тегам на миникарте



# Направление модуля: актуальные версии Heroku (с парой помарок для совместимости с Hikka-подобными)



# region ВСТУПЛЕНИЕ

# Итак. Перед тобой пустой файл. С чего начнём? Немного теории:
# - Модули пишутся на Herokutl (форк Telethon с примочками юзербота). Инлайн-бот
#   тоже работает на нём с Heroku 2.1.0 (см. заметку про 2.1.0+ в начале файла)

# - Общий вид и начальные требования модуля настраиваются с помощью
#   мета-тегов (они необязательны)

#- Всё, что нужно для твоего модуля из модулей от юзербота: loader 
#  (вся настройка модуля, команд) и utils (инструменты для облегчения
#  каких-либо задач)

# endregion ВСТУПЛЕНИЕ


# region META-ТЕГИ
# 1. Версия модуля. Длина кортежа не валидируется, но до Heroku 2.0.0
#    невозможно было открыть .help у модулей с версией короче трёх элементов.
#    Ради совместимости со старыми юзерботами лучше всегда указывать три элемента
__version__ = ("beta", "test", 7) # будет отображено как "vbeta.test.7"


# 2. Разработчик - имя, юзернейм или канал разработчика модуля

# meta developer: @ZetGo
#                 ^^^^^^ - может быть чем угодно. Если указан юзернейм
#                          твоего канала, то юзербот предложит человеку
#                          подписаться на него после установки модуля


# 3. Минимальная версия юзербота - версия, с которой модуль будет работать. 
#                                  Если версия юзербота старее - юзер не сможет
#                                  установить модуль, пока не обновит юзербот до нужной версии

# scope: heroku_min 1.7.2

# для Hikka (допустим, если модуль использует функции, которых нет в Hikka)
# scope: hikka_min 1.7.2


# 4. Отключить отображение всех команд в сообщении об успешной установке модуля

# scope: disable_onload_docs


# 5. Баннер - ссылка на медиа, которое будет отображено в поисковиках
#             модулей. Может быть GIF, фото или видео. Ссылка обязательно
#             должна указывать на файл, а не на страницу с ним

# meta banner: https://github.com/ZetGoHack/Nullmod/raw/main/20250401_100043.jpg


# 6. Инлайн-иконка - ссылка на фото, которое будет отображено в инлайн-режиме,
#                    если у модуля есть инлайн-команды. Ссылка должна указывать
#                    на файл, а не на страницу с ним

# meta pic: https://github.com/ZetGoHack/Nullmod/raw/main/20250401_100043.jpg


# 7. Langpack - ссылка на yaml-файл с переводами для модуля. Пример формата такого
#               файла: https://github.com/ZetGoHack/TestingModules/blob/main/chess.yml.

#               P.S. ⚠️ Не полагайся только на свой лангпак по ссылке. Он не всегда может нормально
#               загрузиться, допустим, из-за проблем с сетью. Если лангпак не загрузится, а в модуле не 
#               будет указано внутренних strings, то вместо всех строк будет написано "Unknown strings"
#               до следующей перезагрузки юб

# packurl: https://github.com/ZetGoHack/TestingModules/raw/main/chess.yml


# endregion


# region ЗАВИСИМОСТИ

# Если твоему модулю нужны какие-то внешние библиотеки/системные пакеты, которых нет в юзерботе/системе,
# то их можно указать в зависимостях. Юзербот при установке модуля попытается установить эти
# библиотеки/пакеты. Если установка не удалась, то модуль не будет установлен

# 1. Requires - установка зависимостей через pip. Список через пробел

# requires: requests beautifulsoup4 git+https://github.com/ZetGoHack/TStickers.git
#                                   ^^^^ - так можно установить библиотеку прямо из репозитория


# 2. Packages - если твоему модулю нужны какие-то системные пакеты, которые можно установить через менеджер
#                   твоей системы, юзербот попытается установить их. Если установка не удалась, то модуль не будет установлен
# FROM HEROKU VERSION 2.0.0+


# packages: ffmpeg


# 3. FFmpeg - если модуль использует функции, для которых нужен ffmpeg. При отсутствии юзербот вернёт ошибку
#             пользователю с требованием установить ffmpeg. Модуль не будет установлен

##scope: ffmpeg
#^ тут лишний #


# 4. Inline - укажите, если модуль использует инлайн-бота для работы. Юзербот проверит, работает ли он.
#             Если инлайн-бот не инициализирован, будет возвращена ошибка. Модуль не будет установлен

# scope: inline


# endregion


import asyncio
from typing import TYPE_CHECKING, Literal
from ..types import BotInlineCall, InlineCall, InlineQuery
# ⚠️ Module и Library - специально импортируются под TYPE_CHECKING
#    Loader ищет класс твоего модуля как первый попавшийся в файле подкласс от Module (vars(module).values()),
#    а Module - подкласс самого себя. Если импортировать его ДО объявления своего класса - loader найдёт сам Module
#    раньше твоего класса, создаст пустой Module() и юзербот загрузит модуль как буквально нерабочую пустышку.
#    Аннотации, использующие эти типы, надо оборачивать в строку
if TYPE_CHECKING:
    from ..types import Module, Library

import telethon

# region ИМПОРТЫ

# В самой основе используется loader. Он отвечает за регистрацию команд, хендлеров и т.д.
# В общем, за всё, что нужно для работы модуля

from .. import loader

# В utils - всякие инструменты для облегчения задач. Получение аргументов, отправка сообщений и т.д.

from .. import utils

# Все импорты из Telethon (или hikkatl) берутся из herokutl. Сам юзербот на уровне загрузчика патчит 
# импорты с "Telethon", или "hikkatl" на "herokutl". Если ты делаешь универсальный модуль под Hikka и Heroku,
# то рекомендую просто использовать общий "from telethon import ...". Оба юб заменят его на свою библиотеку

from herokutl.tl.custom import Message # такой импорт уже будет принят только Heroku
from telethon.tl.types import UpdateUserStatus, UserStatusOnline, UserStatusOffline # для raw_handler


# endregion




# region СТРУКТУРА МОДУЛЯ


# Сам модуль - это класс, который наследуется от loader.Module. Несёт в себе self.db, self.client и т.д.
# Все доступные атрибуты можно посмотреть в dir(self)

# tds - translatable docstring. Этот декоратор позволяет использовать многоязычные описания для команд и модуля.
@loader.tds
class TheBestExampleEverMod(loader.Module):
    """Это описание модуля. Оно отображается после установки и в меню команды `.help TheBestExampleEverMod`"""

    # region ПЕРЕВОДЫ
    # strings - словарь строк для модуля. Ключи - это идентификаторы строк, по которым к ним можно обратиться в коде.
    #           Значения - это сами строки на разных языках. Язык выбирается пользователем в настройках юзербота.
    #           Если строка не найдётся для выбранного языка, будет показано значение по умолчанию (то есть взято из strings)
    #           Если строка не найдётся вообще, будет показано "Unknown strings"

    #           Переводы указываются в словарях strings_{код языка}, например, strings_ru для русского. Код языка - это
    #           стандартный код ISO 639-1 (ru, en, de и т.д.)

    #           ⚠️ В коде всегда используйте ключи из strings - strings["ключ"]. Юзербот сам по установленному языку человека выбирает источник строк

    strings = {
        "name": "TheBestExampleEver", # имя модуля. Этот ключ обязателен. В других переводах можно не указывать, будет использоваться это значение
        "_cls_doc": "This is the best example module ever!", # описание самого модуля. Он заменяет указанный выше docstring. Переводимый ключ (можно использовать в других языках)
        "cfg_changed": "Config value changed to {}!", # строка для использования в коде
        "loading": "<emoji document_id=5382187328670282655>🐱</emoji> Your result is loading...", # не забываем про возможность использовать html разметку в сообщениях!
        "loaded": "<emoji emoji-id=5382147531503319073>😶</emoji> Just kidding! I haven't loaded anything, here are the arguments you entered: {}", # строка с аргументами команды. В коде можно использовать .format для подстановки аргументов
        "user_online": "<emoji document_id=5323703983066324828>🟢</emoji> <b>{} is online!</b>",
        "user_offline": "<emoji document_id=5325738268556271707>🔴</emoji> <b>{} is offline!</b>",
        "inl__a_message": "This is a simple message",
        "inl__a_message_desc": "Example of a simple message",
        "inl__a_message_text": "<b>You entered in inline arguments: {}!</b>",
        "inl__mrk_example": "Example of a message with buttons",
        "inl__a_photo": "This is an example of a message with photo",
        "inl__a_photo_desc": "Example of a message with photo for inline",
        "inl__a_photo_caption": "<b>This is a photo with caption!</b>",
        "inl__gallery": "Example gallery",
        "inl__gallery_desc": "Example of inline gallery from query",
        "inl__gallery_caption": "<b>This photo was opened from query_gallery</b>",
        "inl__button": "Button in inline",
        "inl__insert_query": "Insert query",
        "inl__a_gif": "Example GIF",
        "inl__a_gif_desc": "Example of a gif result",
        "inl__a_gif_caption": "<b>This is a gif with caption!</b>",
        "inl__a_video": "Example video",
        "inl__a_video_desc": "Example of a video result",
        "inl__a_video_caption": "<b>This is a video with caption!</b>",
        "inl__a_file": "Example file",
        "inl__a_file_desc": "Example of a document result",
        "inl__a_file_caption": "<b>This is a PDF file!</b>",
    }

    strings_ru = {
        "_cls_doc": "Это лучший пример модуля!",
        "cfg_changed": "Значение конфига изменено на {}!",
        "loading": "<emoji document_id=5382187328670282655>🐱</emoji> Ваш пример загружается...",
        "loaded": "<emoji document_id=5382147531503319073>😶</emoji> Шучу! Я ничего не загружал, вот аргументы, которые вы ввели: {}",
        "user_online": "<emoji document_id=5323703983066324828>🟢</emoji> <b>{} вошёл в сеть!</b>",
        "user_offline": "<emoji document_id=5325738268556271707>🔴</emoji> <b>{} вышел из сети!</b>",
        "inl__a_message": "Это простое сообщение",
        "inl__a_message_desc": "Пример простого сообщения",
        "inl__a_message_text": "<b>Вы ввели в аргументы инлайна: {}!</b>",
        "inl__mrk_example": "Пример сообщения с кнопками",
        "inl__a_photo": "Это пример сообщения с фото",
        "inl__a_photo_desc": "Пример сообщения с фото для инлайна",
        "inl__a_photo_caption": "<b>Это фото с подписью!</b>",
        "inl__gallery": "Пример галереи",
        "inl__gallery_desc": "Пример инлайн-галереи из запроса",
        "inl__gallery_caption": "<b>Это фото открыто через query_gallery</b>",
        "inl__button": "Кнопка в инлайне",
        "inl__insert_query": "Вставить запрос",
        "inl__a_gif": "Пример GIF",
        "inl__a_gif_desc": "Пример результата с gif",
        "inl__a_gif_caption": "<b>Это gif с подписью!</b>",
        "inl__a_video": "Пример видео",
        "inl__a_video_desc": "Пример результата с видео",
        "inl__a_video_caption": "<b>Это видео с подписью!</b>",
        "inl__a_file": "Пример файла",
        "inl__a_file_desc": "Пример результата с документом",
        "inl__a_file_caption": "<b>Это PDF-файл!</b>",
    }

    strings_jp = { # JP вместо JA - исключение! юзербот использует ключ JP для японского.
        "_cls_doc": "これは最高のモジュールの例です！",
        "cfg_changed": "構成値が{}に変更されました！",
        "loading": "<emoji document_id=5382187328670282655>🐱</emoji> 結果を読み込んでいます...",
        "loaded": "<emoji document_id=5382147531503319073>😶</emoji> 冗談です！何も読み込んでいません。入力した引数は次のとおりです：{}",
        "user_online": "<emoji document_id=5323703983066324828>🟢</emoji> <b>{}がオンラインです！</b>",
        "user_offline": "<emoji document_id=5325738268556271707>🔴</emoji> <b>{}がオフラインです！</b>",
        "inl__a_message": "これは単純なメッセージです",
        "inl__a_message_desc": "単純なメッセージの例",
        "inl__a_message_text": "<b>インライン引数に入力した内容：{}！</b>",
        "inl__mrk_example": "ボタン付きメッセージの例",
        "inl__a_photo": "これは写真付きメッセージの例です",
        "inl__a_photo_desc": "インラインの写真付きメッセージの例",
        "inl__a_photo_caption": "<b>これはキャプション付きの写真です！</b>",
        "inl__gallery": "ギャラリーの例",
        "inl__gallery_desc": "クエリから開くインラインギャラリーの例",
        "inl__gallery_caption": "<b>この写真は query_gallery から開かれました</b>",
        "inl__button": "インラインのボタン",
        "inl__insert_query": "クエリを挿入",
        "inl__a_gif": "GIF の例",
        "inl__a_gif_desc": "GIF 結果の例",
        "inl__a_gif_caption": "<b>これはキャプション付きの GIF です！</b>",
        "inl__a_video": "動画の例",
        "inl__a_video_desc": "動画結果の例",
        "inl__a_video_caption": "<b>これはキャプション付きの動画です！</b>",
        "inl__a_file": "ファイルの例",
        "inl__a_file_desc": "ドキュメント結果の例",
        "inl__a_file_caption": "<b>これは PDF ファイルです！</b>",
    }


    # endregion ПЕРЕВОДЫ


    # region ИНИЦИАЛИЗАЦИЯ


    # Инициализация. Обычно тут регистрируется конфиг self.config модуля (если он нужен)
    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                option="example_option", # имя опции. По этому имени к ней можно обратиться в коде
                default=42, # значение по умолчанию
                doc="This is an example option", # описание опции. Отображается в конфиге модуля
                validator=loader.validators.Integer(), # валидатор для опции. Проверяет, что значение, которое пользователь вводит в конфиге, соответствует требованиям.
                                                       # ℹ️ Все валидаторы ищите в Heroku/heroku/validators.py
                                                       #     Список классов валидаторов: ["Boolean", "Integer", "Float", "String", "Choice", "MultiChoice",
                                                       #                                  "Series", "Link", "RegExp", "TelegramID", "Union", "NoneType",
                                                       #                                  "Hidden", "Emoji", "EntityLike", "RandomLink"]

                on_change=self._on_config_change, # функция, которая будет вызвана при изменении опции. Может быть асинхронной, или синхронной.
                                                  # Ничего не будет передано в аргументы
            ),
            loader.ConfigValue(
                "hidden_value",
                "some_hidden_data",
                "Data that should not be displayed in the settings menu",
                validator=loader.validators.Hidden(       # Hidden - буквально скрывает данные и заменяет на * в основном меню модуля. >
                    loader.validators.String(), #          При открытии меню самого значения, данные можно "подсмотреть", нажав на кнопку >
                ),                                        #          [Показать значение]. Значение раскрывается только в его меню. Незаменимо для >
            ),                                            #          конфигов API ключей и прочих чувствительных данных
            loader.ConfigValue(
                "list_example",
                [1, 2, 3],
                "This is an example list option",
                validator=loader.validators.Series( # валидатор для списков. Проверяет каждый элемент списка на соответствие требованиям.
                                                    # В данном случае - что каждый элемент - это число от 0 до 42 включительно
                                                    # ⚠️ list/dict-опции нельзя редактировать напрямую, типа - self.config["list_example"].append(4).
                                                    #     Оно не пройдёт через __setitem__, поэтому не сохранится в базу и не вызовет on_change.
                                                    #     Переприсваивай целиком: self.config["list_example"] = self.config["list_example"] + [4]
                    loader.validators.Integer(minimum=0, maximum=42)
                ),
                on_change=self._on_config_change,
            ),
            loader.ConfigValue("nothing"), # а можно просто оставить лишь одно название значения. Это, конечно, ничего полезного не даст пользователю...
            loader.ConfigValue(
                "watcher",
                True,
                "Should wathcer be running?",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "raw_handler",
                True,
                "Should raw handler be runnig?",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "handler_targets",
                [],
                "A targets list to track online",
                validator=loader.validators.Series(
                    loader.validators.Integer(),
                ),
            ),
        )

        self._loop_iterations = 0 # переменная для loop

    # Действия при загрузке модуля через .dlm или .lm. Обычно используется для начальной настройки, которая не должна выполняться при каждом запуске модуля.
    # Вызывается ДО client_ready. В self уже готовы все атрибуты (self.client, self.db и т.д.)
    async def on_dlmod(self):
        """
        Called after the module is first time loaded with .dlmod or .loadmod

        Possible use-cases:
        - Send reaction to author's channel message
        - Create asset folder
        - ...

        ⚠️ Note, that any error there will not interrupt module load, and will just
        send a message to logs with verbosity INFO and exception traceback
        """ # < - взято из докстринга функции
        pass
        

    # Клиент готов. Вызывается после __init__ и config_loaded.
    # Обычно тут загружаются какие-то данные из базы, или выполняются действия, которые должны быть при каждом запуске модуля (например, установка базовых
    # значений в self из датабазы)
    async def client_ready(self):
        pass


    # endregion ИНИЦИАЛИЗАЦИЯ

    
    async def _on_config_change(self):

        # region ДАТАБАЗА

        # self.set, self.get, self.pointer - установка, получение и указатель в датабазе модуля соответсвенно. Сокращения от self.db.*(self.__class__.__name__, ...)
        # self.db.set(owner, key, value) - установить значение ключа. Возвращает True или False в зависимости от результата установки значения. 
        #                        ⚠️ Значения должны быть сериализуемыми в JSON! Вы не можете сохранить кастомные классы!
        #                        ℹ️ Учти, что числовые ключи будут автоматически конвертироваться в string-ключ. 1 > "1". Указывай в ключе только string!

        # self.db.get(owner, key, default) - получить значение ключа. Если такого не сущетсвует - возвращается значение из default
        #                        ℹ️ Учти, что числовые ключи будут автоматически конвертироваться в string-ключ. 1 > "1". Указывай в ключе только string!

        # self.db.pointer(owner, key, default) - получить указатель (в случае, если в значении стоит dict, или list).
        #                                       Можно обращаться, как pointer["key"] = 42. Это изменение будет сразу же сохранено в датабазе, а указателем можно
        #                                       пользоваться дальше
        #                        ℹ️ Учти, что числовые ключи будут автоматически конвертироваться в string-ключ. 1 > "1". Указывай в ключе только string!

        value = self.get("cfg_value")

        if (opt := self.config["example_option"]) != value:
            self.set("cfg_value", opt)
        else:
            return

        # endregion ДАТАБАЗА

        await self.client.send_message(
            self.client.heroku_me.id, self.strings["cfg_changed"].format(self.config["example_option"])
        )


    # region КОМАНДЫ


    # Команды. Функции, вызываемые юзерботом при вводе команды (имя команды - это имя функции). Регистрируются в юб с помощью декоратора @loader.command,
    # или `cmd` в конце функции (def examplecmd). При написании команды вызывается с `herokutl.tl.custom.Message` в аргументах
    @loader.command(ru_doc="Пример описания для команды на русском", jp_doc="コマンドの日本語の説明の例")
    async def example(self, message: Message):
        """Example description for a command in English"""
        # Аргументы команды. Следующие функции из utils (это лишь часть) возвращают аргументы команды, исключая её саму. ".example arg1" > "arg1"
        args_tuple = utils.get_args(message) # (arg1, arg2, arg3) - разделение по пробелу
        args_string = utils.get_args_raw(message) # arg1 arg2 arg3 - сырой текст без html оформления
        args_html = utils.get_args_html(message) # <b>arg1</b> arg2 <n>arg3</n> - сырой текст с html оформлением


        # У тебя есть три варианта взаимодействия с сообщением для ответа - редактирование; ответ; ответ с инлайн-формой. Вот первые два варианта:

        # Вариант 1 - utils.answer
        m = await utils.answer(message, self.strings["loading"]) # utils.answer - универсальный способ ответить на команду. Если команда 
                                                                                  # была отправлена от вашего имени (с парой помарок), то сообщение будет отредактировано.
                                                                                  # Если от другого пользователя - будет отправлено новое сообщение с ответом.
                                                                                  # Если указан reply_markup, то будет отправлено новое сообщение с инлайн-кнопками.
                                                                                  # Подробнее о кнопках - в другом примере (L TODO)
                                                                                  # Всегда возврващает объект затронутого сообщения (редакт или отправленное)

        await asyncio.sleep(1) # делаем задержку между отправкой "загрузка..." и результатом. 
                                     # Частые запросы к API могут привести к флудвейту. Не забывайте про задержки!

        # Вариант 2 - использовать методы из Telethon напрямую
        await m.reply(self.strings["loaded"].format(args_html)) # все сообщения обрабатываются с помощью html-разметки автоматически. Рекомендуется использовать только её


    # endregion КОМАНДЫ


    async def example_callback(self, call: InlineCall, message_id: int, chat_id: int, **kwargs):
        # call - объект InlineCall (с Heroku 2.1.0 не связан с aiogram). Содержит в себе всю информацию о клике по кнопке,
        # а также методы для взаимодействия с ним (ответить на клик, отредактировать сообщение и т.д.)
        # message_id, chat_id - аргументы, которые мы передали в "args" кнопки. Они нужны для того,
        # чтобы понять, на какое сообщение была нажата кнопка и в каком чате оно находится. 
        # kwargs - аргументы из "kwargs" кнопки. В данном случае - {"random_num": 42}

        await call.answer(
            f"You clicked the button! Here are the arguments you passed: {message_id}, {chat_id}, {kwargs['random_num']}",
            show_alert = True,
        )

        async def _back(call: InlineCall):
            await call.edit(
                self.strings["inl__mrk_example"],
                reply_markup=self.repl_mrkp,
            )

        await call.edit(
            "Ты только что нажал на кнопку! Ты можешь изменить сообщение прямо через call.edit(), как тут",
            reply_markup={"text": "Назад", "callback": _back},
        )

    async def example_input(self, call: InlineCall, data: str):
        # call - объект InlineCall (с Heroku 2.1.0 не связан с aiogram). Содержит в себе всю информацию о клике по кнопке,
        # а также методы для взаимодействия с ним (ответить на клик, отредактировать сообщение и т.д.)
        # data - текст, который пользователь ввёл в инлайн-режиме после клика на кнопку с "input"

        await call.answer(f"You entered in inline mode: {data}")


    async def example_gallery_photo(self):
        # функция должна вернуть ссылку на фотографию, или список из них
        return ["https://github.com/ZetGoHack/TestingModules/raw/main/ex_thumb.jpg"]


    @loader.callback_handler()
    async def example_callback_handler(self, call: BotInlineCall):
        if call.data != "example/hello":
            return

        await call.answer("You clicked the button with custom data! {}".format(call.data))


    # region ИНЛАЙН-КОМАНДЫ


    @loader.command(ru_doc="Пример команды с инлайн-кнопками", jp_doc="インラインボタンを使用したコマンドの例")
    async def exmplmkp(self, message: Message):
        """Example of a command with inline buttons"""


        # region КНОПКИ


        # Инлайн-кнопки - словарь, или список словарей с определёнными ключевыми параметрами. Кнопки имеют несколько типов.


        # region СТРУКТУРА КНОПОК


        # Полная структура кнопок:
        self.repl_mrkp = reply_markup = [ 
           [ # первый ряд
              {
                  "text": "кнопка с обработчиком клика",
                  "callback": self.example_callback,
                  "args": (message.id, message.chat_id),
                  "kwargs": {"random_num": 42},
              }, # первая кнопка 
           ],
           [ # второй ряд
              {
                  "text": "кнопка без обработчика", "data": "example/hello",
              } # вторая кнопка
           ],

           [ # третий ряд
              {
                  "text": "кнопка-ссылка", "url": "https://t.me/ZetGo",
              }, # третья кнопка
           ],

           [ # четвёртый ряд
              {
                  "text": "кнопка приёма ввода",
                  "input": "Пример приёма ввода",
                  "handler": self.example_input,
              }, # четвёртая кнопка 
              {
                  "text": "кнопка копирования", "copy": "copy text",
              }, # ...
              {
                  "text": "кнопка-ответ",
                  "action": "answer",
                  "message": "Ты клацнул по кнопке!",
                  "disable_security": True,
                  "show_alert": True,
              },
           ],
           [
                {
                    "text": "webapp-кнопка",
                    "url": ( # спустя 20 минут тестов и одного вопроса к одному крутому человеку выяснилось,
                             # что web_app кнопки невозможно отправить через инлайн (только в личке)...
                             # В любом случае, многие клиенты отображают url кнопку с webapp-подобными ссылками
                             # как webapp кнопку
                        "https://t.me/xgift?startapp=profile-1226061708_ref-b1e785f69fb4ac258f97898b37b72536"
                    ),
                },
           ],
           [{"text": "Закрыть форму", "action": "close"}],
           [{"text": "Выгрузить форму", "action": "unload"}],
        ]


        # endregion СТРУКТУРА КНОПОК


        # region ТИПЫ КНОПОК

        # ⚠️ Типы кнопок не могут использоваться вместе в одной кнопке!
        # Типы кнопок:
        # "callback" - функция-обработчик клика по кнопке. Функция должна быть
        #              асинхронной и принимать как минимум один аргумент - CallbackQuery

        # "input" - заголовок для результата, выданного в инлайн-режиме. При клике на кнопку
        #           юзербот откроет инлайн для ввода текста. После ввода вызывается хендлер из
        #           "handler"

        # "handler" - функция-обработчик инлайн результата. Работает в паре с "input". Функция
        #             должна быть асинхронной и принимать как минимум два аргумента -
        #             CallbackQuery и текст, введённый пользователем в инлайн-режиме

        # "data" - callback data для кнопки. Вместо генерации рандомной callback data, которая
        #          привязывается к обработчику, ты указываешь свою. Эта data не будет привязана
        #          ни к чему. В таком случае, тебе нужно создать callback_handler с фильтром на
        #          эту data.
        #          ⚠️ Не оставляй хендлер без фильтра на data, так как юзербот при получении
        #              callback отправляет его абсолютно всем хендлерам абсолютно всех модулей!

        # "url" - кнопка-ссылка. При клике открывает ссылку. Ссылка должна быть валидной,
        #         иначе кнопка не будет создана

        # "web_app" - кнопка для открытия webapp. При клике открывает webapp. Может быть
        #             строкой (url), или словарём с ключом "url".
        #             На практике, Телеграм позволяет использовать её только в обычных,
        #             сообщениях бота, не в инлайн-формах

        # "copy" - кнопка для копирования текста внутри неё "copy": "текст для копирования"

        # "action" - быстрые действия при нажатии кнопки:
        #            1. "action": "answer" - работает вместе с "show_alert" и "message".
        #                                    "message" - текст, отображаемый при клике на кнопку
        #                                    "show_alert" - флаг, отвечающий за вид отображения
        #                                                   сообщения

        #            2. "action": "close" - закрыть (удалить и выгрузить) инлайн-форму

        #            3. "action": "unload" - только выгрузить форму из памяти юзербота. Сообщение
        #                                    останется, но кнопки больше не будут обрабатываться


        # endregion ТИПЫ КНОПОК


        # region ПАРАМЕТРЫ КНОПОК


        # Параметры кнопок:
        # "text" - текст кнопки. Обязательный параметр для всех типов кнопок

        # "args" - tuple или list аргументов для передачи в "callback", или "handler"

        # "kwargs" - dict аргументов (аргумент: значение) для передачи в "callback", или
        #            "handler". О последовательности аргументов в кнопках - (L535)

        # "always_allow" - список ID пользователей (whitelist), которым всегда разрешено нажимать
        #                  на кнопку. Проверка безопасности пропустит этих пользователей

        # "disable_security" - отключить проверку безопасности для кнопки. Проверка проверяет,
        #                      является ли нажавший пользователь одним из владельцев юзербота,
        #                      или есть ли его ID в списке разрешённых пользователей

        # "force_me" - разрешить кнопку только владельцу юзербота

        # "style" - цвет кнопки: "danger" - красный, "primary" - синий, "success" - зелёный

        # "emoji_id" - document_id кастомного эмодзи для иконки кнопки. Не работает в Inline-сообщениях,
        #              только в обычных сообщениях бота


        # endregion ПАРАМЕТРЫ КНОПОК



        # О последовательности аргументов

        # Аргументы в функции-хендлеры передаются в последовательности func(call, *args, **kwargs),
        # или func(call, data, *args, **kwargs) в зависимости от типа хендлера (callback/input)


        # Сообщение message при наличии reply_markup будет удалено, а вместо него будет открыта инлайн-форма
        await utils.answer(message, self.strings["inl__mrk_example"], reply_markup=reply_markup)

        # utils.answer с reply_markup - это почти всегда вызов self.inline.form (кроме случая, когда message
        # это уже call).

        await self.inline.form(
            self.strings["inl__mrk_example"],
            message,
            reply_markup,
            always_allow=[25, 50, 149], # Да, эти оба параметра могут быть локальными для каждой кнопки,
            disable_security=False,     # так и глобальными для всей формы - но это OR логикв:
                                        # True с любой стороны убирает проверку. Если True указан глобально,
                                        # то локально для кнопки защиту с False уже не включить
        )



        # endregion КНОПКИ


    # region БОТ

    # self.inline.bot - клиент бота. До Heroku 2.1.0+ (Hikka-вайбы) - Aiogram клиент, после - Telethon.
    #                   Через него можно работать напрямую от лица бота

    @loader.command(ru_doc="Пример отправки сообщения с кнопками от лица бота")
    async def exmplnotify(self, message: Message):
        """Example of sending message with buttons from the bot"""
        # region ГЕНЕРАЦИЯ КНОПОК
        reply_markup = self.inline.generate_markup(
            # generate_markup - тот же парсер кнопок, что и для инлайн-сообщений. Полезен, когда нужно 
            #                   отправить сообщение от имени бота с кнопками, созданными через удобный
            #                   обработчик юзербота. (Разумеется ты можешь создавать свои кнопки через
            #                   telethon-билдер Button и ловить его через сырой callback_handler для
            #                   каких-то более сложных задач. Но удобный генератор ведь легче :3)
            [
                [
                    {
                        "text": "Да",
                        "callback": self.exmplnotify_yes,
                        "args": (await message.link(thread=True),),
                    },
                    {"text": "Нет", "callback": self.exmplnotify_no},
                ],
            ]
        )
        # endregion ГЕНЕРАЦИЯ КНОПОК

        # вообще, self.inline.bot - ещё один прокси для обратной совместимости со старыми модулями на
        # Aiogram-логике. В self.inline.bot.client уже лежит реальный клиент Telethon-бота, через него
        # и можно инвокать методы
        await self.inline.bot.send_message(
            self.tg_id, # тут мы, разумеется, укажем айди владельца юзербота
            "<b>Привет, это тестовое сообщения от <code>TheBestExampleEver</code></b>",
            reply_markup=reply_markup,
        )
        await utils.answer(message, "Уведомление отправлено в личку с ботом")

    async def exmplnotify_yes(self, call: BotInlineCall, source_message_link: str):
        await call.answer("Подтверждено!")
        await utils.answer(call, f"Готово! (из сообщения {source_message_link})")

    async def exmplnotify_no(self, call: BotInlineCall):
        await call.answer("Отменено")
        await utils.answer(call, "Отменено юзером")

    # endregion БОТ


    # Инлайн-команды. Функции, вызываемые при вводе инлайн-команды в виде @ur_inline_bot inlexample query1 query2.
    # Регистрируются в юб с помощью декоратора @loader.inline_handler, как и обычные команды. В аргументы функции при вызове
    # получает объект `InlineQuery` (с Heroku 2.1.0 не связан с aiogram).
    @loader.inline_handler(ru_doc="Пример описания для инлайн-команды на русском", jp_doc="インラインコマンドの日本語の説明の例")
    async def inlexample(self, query: InlineQuery):
        """Example description for an inline command in English"""
        # Чтобы вернуть результаты инлайн-команды, нужно вернуть либо словарь, либо список словарей. Ниже все случаи использования

        # Для query_gallery можно ответить на query самостоятельно и ничего не возвращать:
        if query.args == "gallery":
            # query_gallery - функция для ответа на inline-запрос несколькими результатами-галереями,
            # например, если фото/данные для них берутся из разных источников
            await self.inline.query_gallery(
                query,
                [
                    {
                        "title": self.strings["inl__gallery"],
                        "description": self.strings["inl__gallery_desc"],
                        "next_handler": self.example_gallery_photo,
                        "caption": self.strings["inl__gallery_caption"],
                    },
                ],
            )
            return

        # Ниже основные типы контента, которые ты можешь вернуть из inline_handler:

        results = [
        # 1. Простое сообщение:
            {
                "title": self.strings["inl__a_message"],
                "description": self.strings["inl__a_message_desc"],
                "message": self.strings["inl__a_message_text"].format(query.args),
                "thumb": "https://github.com/ZetGoHack/TestingModules/raw/main/ex_thumb.jpg",
                "reply_markup": [
                    {"text": self.strings["inl__insert_query"], "switch_inline_query_current_chat": "inlexample "},
                    # switch_inline_query(_current_chat) - подставить пользователю начальный шаблон твоей команды,
                    # например: "@ZetGoBot inlexample". Работает только в результатах inline_handler
                ],
            },
        # 2. Фото:
            {
                "title": self.strings["inl__a_photo"],
                "description": self.strings["inl__a_photo_desc"],
                "photo": "https://github.com/ZetGoHack/TestingModules/raw/main/ex_thumb.jpg",
                "caption": self.strings["inl__a_photo_caption"],
            },

        # 3. GIF:
            {
                "title": self.strings["inl__a_gif"],
                "description": self.strings["inl__a_gif_desc"],
                "gif": "https://github.com/ZetGoHack/TestingModules/raw/main/dooo.gif",
                "caption": self.strings["inl__a_gif_caption"],
            },

        # 4. Видео
            {
                "title": self.strings["inl__a_video"],
                "description": self.strings["inl__a_video_desc"],
                "video": "https://github.com/ZetGoHack/TestingModules/raw/main/example_cat.mp4",
                "thumb": "https://github.com/ZetGoHack/TestingModules/raw/main/ex_thumb.jpg",
                "caption": self.strings["inl__a_video_caption"],
            },
        # 5. Документ:
            {
                "title": self.strings["inl__a_file"],
                "description": self.strings["inl__a_file_desc"],
                "file": "https://sample-files.com/downloads/documents/pdf/basic-text.pdf",
                "mime_type": "application/pdf", # Для file обязателен параметр mime_type
                "caption": self.strings["inl__a_file_caption"],
            },
        ]

        return results


    # endregion ИНЛАЙН-КОМАНДЫ


    # region WATCHER


    # watcher - функция, которая вызывается при каждом новом сообщении (❗ даже если это сервисное сообщение,
    # то есть без текста), полученным диспатчером юзербота, а так же подходящим под условия самого watcher.
    # Функция получает объект `herokutl.tl.custom.Message`. Условия watcher устанавливаются в аргументы
    # декоратора @loader.watcher, или @loader.tag
    # ℹ️ Подробнее про теги: https://dev.heroku-ub.xyz/watchers

    @loader.watcher(no_commands=True)   # Не пропускать команды в этот watcher
    async def example_watcher(self, message: Message):
        if not self.config["watcher"]: # Включать/Выключать wathcer можно через локальные настройки
            return
        
        if not hasattr(message, "message"): # В нашем случае нужно исключить сервисные сообщения,
            return                          # у которых нет текста

        if not message.message or not message.message.startswith("testwatcher"):
            return
        
        prefix = self.get_prefix()
        
        await message.reply(
            "Watcher from TheBestExampleEverMod is working!\n"
            "You can turn the watcher off in <code>{prefix}cfg TheBestExampleEverMod</code>".format(prefix=prefix)
        )


    # endregion WATCHER


    # region ЦИКЛЫ


    @loader.loop(
        interval=60, # default int 5
        autostart=True, # default bool False
        wait_before=True, # default bool False
        stop_clause="IS_LOOP_RUNNING" # default NoneType None
    )
    async def loop(self): 
        # loop - декоратор, который помечает функцию как InfiniteLoop для запуска цикла функции каждые interval
        #        секунд. loop по дефолту сам не запускается, если не указан autostart. Ручной запуск через 
        #        self.loop.start(), ручная остановка цикла - self.loop.stop(). NOTE: stop() до Heroku 2.2.2 
        #        НЕ очищал поле loop._task, что мешало повторному запуску loop.start(). В Heroku 2.2.2+ ошибка
        #        исправлена. wait_before - переносит задержку с окончания цикла в его начало. stop_clause - имя
        #        ключа в датабазе модуля (self.get(KEY, bool)), который является знаком полной остановки цикла.
        #        NOTE: stop_clause до Heroku 2.2.2 так же НЕ очищал поле loop._task. Для совместимых с Hikka
        #        модулей делайте обход через очистку поля _task и status после явной остановки цикла, если
        #        собираетесь стартовать цикл по-новой.
        self._loop_iterations += 1

        if self._loop_iterations > 10:
            self.set("IS_LOOP_RUNNING", False)
            return


        # region LOOKUP


        tester_module: "Literal[False] | Module | Library" = self.lookup(
            "TestMod"
        )
        # ^ аннотация в кавычках - см. предупреждение у импорта Module/Library в начале файла
        # self.lookup("module_classname_or_name") - метод, буквально возвращающий объект класса активного Модуля/Библиотеки.
        #                                           с ним вы получаете доступ к self модуля и вызывать его функции, получать
        #                                           его данные и прочее. можно переиспользовать одну функцию одного модуля в
        #                                           других. неплохо подходит для интеграций модулей. если lookup не нашёл
        #                                           модуль, будет возвращено False.

        if tester_module is not False:
            log_level = tester_module.config["tglog_level"]
        else:
            log_level = 0


        # endregion LOOKUP


        # region INVOKE

        # self.invoke(command, args=None, *, peer=None, message=None, edit=False) - вызывает команду
        #             по её имени, как будто её реально ввели в чат: либо новым сообщением в peer, либо
        #             через существующий message (.edit, если edit=True, иначе .respond; если указан
        #             peer - message игнорируется). Удобен, когда известно только имя команды (например,
        #             задано пользователем/конфигом), а не конкретный модуль и метод - lookup() тут не
        #             поможет, раз не знаешь, с какого модуля тянуть

        # ⚠️ команда должна быть в self.allmodules.commands (т.е. модуль с этой
        #     командой должен быть загружен), иначе будет ValueError

        # Пример (закомментирован, чтобы не дёргать реальную команду каждый тик loop):
        # result_message = await self.invoke("ping", peer=self.tg_id)
        # ^ отправит ".ping" в личку с самим собой и тут же вызовет
        #   хендлер команды ping, если она загружена

        # endregion INVOKE


    # endregion ЦИКЛЫ


    # region RAW_HANDLER

    # raw_handler - функция, которая вызывается при каждом новом событии, полученным диспатчером юзербота, если это событие
    # является одним из типов, указанных в аргументах декоратора @loader.raw_handler. Функция получает объект события 
    # (например тут - UpdateUserStatus).
    @loader.raw_handler(UpdateUserStatus)
    async def raw_handler(self, event: UpdateUserStatus):
        if not self.config["raw_handler"]:
            return

        user_id = event.user_id
        
        if user_id in self.config["handler_targets"]:
            user = await self.client.get_entity(user_id)
            if isinstance(event.status, UserStatusOnline):
                status = "user_online"
            else:
                status = "user_offline"

            await self.client.send_message(
                "me",
                self.strings[status].format(
                    telethon.utils.get_display_name(user) + f" ({user_id})",
                ),
            )

    # endregion RAW_HANDLER


    # region ВЫГРУЗКА


    # Действия при выгрузке/обновлении модуля. Вызывается при каждом обновлении и выгрузке модуля.
    # Обычно используется для очистки ресурсов, остановки циклов и т.д.
    async def on_unload(self):
        pass


    # endregion ВЫГРУЗКА


# endregion СТРУКТУРА МОДУЛЯ
