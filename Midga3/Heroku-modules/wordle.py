# Midga3

# I AM NOT AFFICIATED WITH WORDLE

# meta developer: @midga3_modules

import requests
import random
import logging
from .. import loader, utils
from herokutl.tl.types import Message
__verison__ = (0, 2, 1)  
logger = logging.getLogger(__name__)
@loader.tds
class wordle(loader.Module):
    """Wordle!"""
    strings = {
        "name": "Wordle",
        "loading": "Loading...",
        "language": "Language of the wordle",
        "have_a_good_game": "Have a good game! Try to guess the 5 letter word in {}",
        "attempts_left": "WRONG! Attempts left: {}",
        "gg": "GG! YOU DIDN'T GUESS THE WORD {}",
        "win": "GG! YOU WON! THE WORD WAS {}",
        "already_playing": "ALREADY PLAYING! type .stopwordle to stop the current game",
        "length": "Must be 5 letters",
        "no_game": "No game is currently running",
        "ok": "Game stopped",
        "ad": "I tried to Guess word {}. Check out my result:\n{}",
        "real_word": "This word is not in the word list"
    }
    strings_ru ={
        "name": "Wordle",
        "loading": "Загрузка...",
        "language": "Язык вордла",
        "have_a_good_game": "Хорошей игры! Попытайтесь угадать слово из 5 букв на {}",
        "attempts_left": "НВЕВЕРНО! Осталось попыток: {}",
        "gg": "ГГ! ВЫ НЕ УГАДАЛИ СЛОВО {}",
        "win": "ГГ! ВЫ ВЫИГРАЛИ! СЛОВО БЫЛО {}",
        "already_playing": "УЖЕ ИГРАЕТЕ! напишите .stopwordle чтобы остановить текущую игру",
        "length": "Должно содержать 5 букв",
        "no_game": "Сейчас нет активной игры",
        "ok": "Игра остановлена",
        "ad": "Я попытался угадать слово {}. Чекайте мой результат:\n{}",
        "real_word": "Такого слова нет в списке слов"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "language",
                "en",
                self.strings["language"],
                validator=loader.validators.Choice(["en", "ru"])
            ),
        )

    def _build_markup(self, buttons):
        markup = list(buttons)
        markup.append([{"text": "Введите слово", "input": self.strings("length"), "handler": self.handler}])
        return markup

    def _norm(self, s):
        if isinstance(s, bytes):
            s = s.decode("utf-8", "ignore")
        return (s or "").replace("\ufeff", "").strip().upper()

    async def handler(self, call, data):
        guess = self._norm(data)
        word = self._norm(self._db.get("wordle", "word", ""))
        attempts = self._db.get("wordle", "attempts", 0)
        buttons = self._db.get("wordle", "buttons", []) or []
        markup = self._build_markup(buttons)

        if len(guess) != 5:
            await call.edit(self.strings("length"), reply_markup=markup)
            return

        words = self._db.get("wordle", "words", []) or []
        words_set = set()
        for w in words:
            nw = self._norm(w)
            if nw:
                words_set.add(nw)

        if guess not in words_set and guess != word:
            await call.edit(self.strings("real_word"), reply_markup=markup)
            return

        buttons2 = []
        for i in range(5):
            if guess[i] == word[i]:
                buttons2.append({"text": guess[i], "data": "custom/data", "style": "success"})
            elif guess[i] in word:
                buttons2.append({"text": guess[i], "data": "custom/data", "style": "primary"})
            else:
                buttons2.append({"text": guess[i], "data": "custom/data", "style": "danger"})

        buttons.append(buttons2)

        def _result(btns):
            res = ""
            for btn in btns:
                if not isinstance(btn, list):
                    continue
                line = ""
                for b in btn:
                    if not isinstance(b, dict):
                        continue
                    st = b.get("style")
                    if st == "success":
                        line += "🟩"
                    elif st == "primary":
                        line += "🟨"
                    elif st == "danger":
                        line += "⬛"
                if line:
                    res += line + "\n"
            return res

        if guess == word:
            self._db.set("wordle", "buttons", buttons)
            self._db.set("wordle", "now_playing", False)
            result = _result(buttons)
            buttons.append([{"text": "Поделится резултатом", "copy": self.strings("ad").format(word, result)}])
            await call.edit(self.strings('win').format(word), reply_markup=buttons)
            return

        self._db.set("wordle", "buttons", buttons)
        attempts -= 1
        self._db.set("wordle", "attempts", attempts)

        if attempts == 0:
            result = _result(buttons)
            buttons.append([{"text": "Поделится резултатом", "copy": self.strings("ad").format(word, result)}])
            await call.edit(self.strings('gg').format(word), reply_markup=buttons)
            self._db.set("wordle", "now_playing", False)
        else:
            markup = self._build_markup(buttons)
            await call.edit(self.strings('attempts_left').format(attempts), reply_markup=markup)

    @loader.command()
    async def wordle(self, message: Message):
        """Play wordle!"""
        await utils.answer(message, self.strings("loading"))
        if self._db.get("wordle", "now_playing", False):
            await utils.answer(message, self.strings("already_playing"))
            return
        args = utils.get_args(message)
        if args and args[0].lower():
            if args[0].lower() == "--no-sec":
                self._db.set("wordle", "nosec", True)
                return
        else:
            self._db.set("wordle", "nosec", False)
        try:
            response = requests.get(f"https://raw.githubusercontent.com/mimimishka449/Worlde/refs/heads/main/words_{self.config['language']}.txt")
            if response.status_code == 200:
                raw_words = response.text.splitlines()
                words = []
                seen = set()
                for w in raw_words:
                    nw = self._norm(w)
                    if len(nw) == 5 and nw not in seen:
                        seen.add(nw)
                        words.append(nw)
                if not words:
                    await utils.answer(message, "Word list is empty.")
                    return
                word = random.choice(words)
                self._db.set("wordle", "now_playing", True)
                self._db.set("wordle", "attempts", 6)
                self._db.set("wordle", "word", word)
                self._db.set("wordle", "words", words)
                self._db.set("wordle", "buttons", [])
                await self.inline.form(self.strings("have_a_good_game").format("английском" if self.config['language'] == "en" else "русском"), message, reply_markup=[[{"text":"Введите слово","input":self.strings("length"),"handler": self.handler}]])
            else:
                await utils.answer(message, "Error fetching wordle data.")
        except Exception as e:
            logger.exception(f"Error: {e}")
            await utils.answer(message, "An error occurred while fetching wordle data.")

    @loader.command()
    async def stopwordle(self, message: Message):
        """Stop the wordle game."""
        if not self._db.get("wordle", "now_playing", False):
            await utils.answer(message, self.strings("no_game"))
            return
        self._db.set("wordle", "now_playing", False)
        await utils.answer(message, self.strings("ok"))