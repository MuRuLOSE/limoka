__version__ = (1, 0, 0)
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
# notesmod.py
# meta developer: @systemxplore
# scope: hikka_only
import os
from .. import loader, utils


@loader.tds
class NotesFileMod(loader.Module):
    """Модуль для заметок с хранением в файлах"""
    strings = {"name": "NotesFile"}

    def __init__(self):
        self.notes_dir = "notes"

    async def client_ready(self, client, db):
        self.client = client

        if not os.path.exists(self.notes_dir):
            os.makedirs(self.notes_dir)

    @loader.command()
    async def noteadd(self, message):
        """
        Добавить заметку.
        Использование: .noteadd #tag <текст>
        """
        args = utils.get_args_raw(message)
        if not args.startswith("#"):
            await utils.answer(message, "❌ Укажите тег заметки, начиная с `#`.")
            return

        try:
            tag, text = args.split(" ", 1)
        except ValueError:
            await utils.answer(message, "❌ Укажите текст заметки после тега.")
            return

        note_file = os.path.join(self.notes_dir, f"{tag[1:]}.txt")
        with open(note_file, "w", encoding="utf-8") as f:
            f.write(text)

        await utils.answer(message, f"✅ Заметка `{tag}` сохранена.")

    @loader.command()
    async def notedelete(self, message):
        """
        Удалить заметку.
        Использование: .notedelete #tag
        """
        tag = utils.get_args_raw(message)
        if not tag.startswith("#"):
            await utils.answer(message, "❌ Укажите тег заметки, начиная с `#`.")
            return

        note_file = os.path.join(self.notes_dir, f"{tag[1:]}.txt")
        if os.path.exists(note_file):
            os.remove(note_file)
            await utils.answer(message, f"✅ Заметка `{tag}` удалена.")
        else:
            await utils.answer(message, f"❌ Заметка `{tag}` не найдена.")

    @loader.command()
    async def noteview(self, message):
        """
        Просмотреть заметку.
        Использование: .noteview #tag
        """
        tag = utils.get_args_raw(message)
        if not tag.startswith("#"):
            await utils.answer(message, "❌ Укажите тег заметки, начиная с `#`.")
            return

        note_file = os.path.join(self.notes_dir, f"{tag[1:]}.txt")
        if os.path.exists(note_file):
            with open(note_file, "r", encoding="utf-8") as f:
                text = f.read()
            await utils.answer(message, f"📝 Заметка `{tag}`:\n\n{text}")
        else:
            await utils.answer(message, f"❌ Заметка `{tag}` не найдена.")

    @loader.command()
    async def notelist(self, message):
        """
        Показать список всех заметок.
        """
        files = os.listdir(self.notes_dir)
        if not files:
            await utils.answer(message, "📋 Нет сохранённых заметок.")
        else:
            notes_list = "\n".join(f"• `#{os.path.splitext(file)[0]}`" for file in files)
            await utils.answer(message, f"📋 Список заметок:\n\n{notes_list}")
