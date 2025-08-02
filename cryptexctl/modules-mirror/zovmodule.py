__version__ = (2, 1, 0)
#                                                                                                          
#                                                                                                       88  
#                                                    ,d                                          ,d     88  
#                                                    88                                          88     88  
#  ,adPPYba,  8b,dPPYba,  8b       d8  8b,dPPYba,  MM88MMM  ,adPPYba,  8b,     ,d8  ,adPPYba,  MM88MMM  88  
# a8"     ""  88P'   "Y8  `8b     d8'  88P'    "8a   88    a8P_____88   `Y8, ,8P'  a8"     ""    88     88  
# 8b          88           `8b   d8'   88       d8   88    8PP"""""""     )888(    8b            88     88  
#  "8a,   ,aa  88            `8b,d8'    88b,   ,a8"   88,   "8b,   ,aa   ,d8" "8b,  "8a,   ,aa    88,    88  
#  `"Ybbd8"'  88              Y88'     88`YbbdP"'    "Y888  `"Ybbd8"'  8P'     `Y8  `"Ybbd8"'    "Y888  88  
#                            d8'      88                                                                   
#                           d8'       88                                                                   
#              © Copyright 2024
#           https://t.me/cryptexctl
#
# 🔒      Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html
# leeter.py
# meta developer: @systemxplore
# scope: hikka_only
# scope: hikka_min 1.6.3
from .. import loader, utils

class LeeterMod(loader.Module):
    """Тут либо гойда либо зов\nлибо ZOVишь либо leetируешь"""
    strings = {
        "name": "zover",
        "enabled": "✅ Leeter включен.",
        "disabled": "❌ Leeter выключен.",
        "mode_leet": "⚙️ Режим установлен: Leet",
        "mode_replace": "⚙️ Режим установлен: ZOV"
    }  # Исправлено: убрана лишняя закрывающая скобка

    def __init__(self):
        self.config = loader.ModuleConfig(
            "MODE", "leet",  # Возможные значения: "leet" или "replace"
            lambda: "Режим обработки сообщений: 'leet' для leet-стиля или 'replace' для zov."
        )
        self.active = False

    async def client_ready(self, client, db):
        self.client = client

    @loader.command()
    async def leeter(self, message):
        """Включить/выключить обработку сообщений."""
        self.active = not self.active
        status = self.strings["enabled"] if self.active else self.strings["disabled"]
        await utils.answer(message, status)

    @loader.command()
    async def zovmode(self, message):
        """Переключить режим: leet или zov."""
        new_mode = "leet" if self.config["MODE"] == "replace" else "replace"
        self.config["MODE"] = new_mode
        mode_message = self.strings["mode_leet"] if new_mode == "leet" else self.strings["mode_replace"]
        await utils.answer(message, mode_message)

    async def watcher(self, message):
        """Обрабатывает все ваши сообщения."""
        if not self.active or not message.out:
            return

        text = message.raw_text
        if self.config["MODE"] == "leet":
            # Преобразование в leet-стиль
            text = self.to_leet(text)
        elif self.config["MODE"] == "replace":
            # Замена z-Z, v-V, o-O
            text = self.replace_chars(text)

        # Редактируем сообщение с преобразованным текстом
        await message.edit(text)

    def to_leet(self, text):
        """Преобразует текст в leet-стиль."""
        leet_map = {
            'а': '4', 'б': '6', 'в': '8', 'г': 'r', 'д': 'D', 'е': '3', 'ё': 'E',
            'ж': '>|<', 'з': '3', 'и': 'u', 'й': 'u`', 'к': 'K', 'л': 'JI',
            'м': 'M', 'н': 'H', 'о': '0', 'п': 'n', 'р': 'P', 'с': 'C',
            'т': '7', 'у': 'Y', 'ф': 'F', 'х': 'X', 'ц': 'U,', 'ч': '4',
            'ш': 'W', 'щ': 'W,', 'ъ': "'", 'ы': 'bl', 'ь': "'", 'э': '3',
            'ю': '10', 'я': '9',
            'a': '4', 'b': '8', 'c': '<', 'd': '[)', 'e': '3', 'f': '|=',
            'g': '6', 'h': '#', 'i': '1', 'j': '_|', 'k': '|<', 'l': '1',
            'm': '^^', 'n': '^/', 'o': '0', 'p': '|2', 'q': 'O_', 'r': '12',
            's': '5', 't': '7', 'u': '|_|', 'v': '\\/', 'w': '\\/\\/', 'x': '%',
            'y': '`/', 'z': '2'
        }
        return ''.join(leet_map.get(char.lower(), char) for char in text)

    def replace_chars(self, text):
        """Заменяет z-Z, v-V, o-O в тексте."""
        replace_map = {'з': 'Z', 'З': 'Z', 'в': 'V', 'В': 'V', 'о': 'O', 'О': 'O'}
        return ''.join(replace_map.get(char, char) for char in text)
