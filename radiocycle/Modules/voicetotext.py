# =======================================
#   _  __         __  __           _
#  | |/ /___     |  \/  | ___   __| |___
#  | ' // _ \    | |\/| |/ _ \ / _` / __|
#  | . \  __/    | |  | | (_) | (_| \__ \
#  |_|\_\___|    |_|  |_|\___/ \__,_|___/
#           @ke_mods
# =======================================

# meta developer: @ke_mods
# scope: ffmpeg
# requires: pydub SpeechRecognition

from .. import loader, utils
import os
import speech_recognition as sr
from pydub import AudioSegment

@loader.tds
class VoiceToTextMod(loader.Module):
    strings = {
        "name": "VoiceToText",
        "process_text": "<emoji document_id=4911241630633165627>✨</emoji> <b>Recognizing the message text...</b>",
        "vtt_success": "<emoji document_id=5116110535565247270>🔥</emoji> <b>Recognized text:</b>\n<blockquote expandable>{}</blockquote>",
        "vtt_failure": "<emoji document_id=5116151848855667552>🚫</emoji> <b>Failed to recognize the message.</b>",
        "vtt_request_error": "<emoji document_id=5116151848855667552>🚫</emoji> <b>Error when contacting the recognition service:</b>\n<code>{}</code>",
        "vtt_invalid": "<emoji document_id=5116151848855667552>🚫</emoji> <b>Please reply to a voice or video message with the command</b> <code>{}vtt</code>",
        "vtt_successful": "<emoji document_id=4916036072560919511>✅</emoji> <b>Text recognized successfully</b>",
    }

    strings_ru = {
        "process_text": "<emoji document_id=4911241630633165627>✨</emoji> <b>Распознаю текст сообщения...</b>",
        "vtt_success": "<emoji document_id=5116110535565247270>🔥</emoji> <b>Распознанный текст:</b>\n<blockquote expandable>{}</blockquote>",
        "vtt_failure": "<emoji document_id=5116151848855667552>🚫</emoji> <b>Не удалось распознать сообщение.</b>",
        "vtt_request_error": "<emoji document_id=5116151848855667552>🚫</emoji> <b>Ошибка при обращении к сервису распознавания:</b>\n<code>{}</code>",
        "vtt_invalid": "<emoji document_id=5116151848855667552>🚫</emoji> <b>Пожалуйста, ответьте на голосовое или видеосообщение командой</b> <code>{}vtt</code>",
        "vtt_successful": "<emoji document_id=4916036072560919511>✅</emoji> <b>Текст успешно распознан</b>",
    }

    @loader.command(
        ru_doc="- распознает текст из голосового или видеосообщения.",
    )
    async def vttcmd(self, message):
        """- recognizes text from voice or video messages."""
        reply = await message.get_reply_message()

        if not reply or not (reply.voice or reply.video_note):
            await utils.answer(message, self.strings["vtt_invalid"].format(self.get_prefix()))
            return

        msg = await utils.answer(
            message, self.strings["process_text"], reply_to=message.id
        )

        media_file = await reply.download_media()
        wav_file = media_file.replace('.mp4', '.wav') if reply.video_note else media_file.replace('.oga', '.wav')

        try:
            AudioSegment.from_file(media_file).export(wav_file, format='wav')
            recognizer = sr.Recognizer()
            with sr.AudioFile(wav_file) as source:
                audio_data = recognizer.record(source)
                try:
                    text = recognizer.recognize_google(audio_data, language='ru-RU')
                    await utils.answer(msg, self.strings["vtt_success"].format(text))
                except sr.UnknownValueError:
                    await utils.answer(msg, self.strings["vtt_failure"])
                except sr.RequestError as e:
                    await utils.answer(msg, self.strings["vtt_request_error"].format(e))
        finally:
            os.remove(media_file)
            os.remove(wav_file)
