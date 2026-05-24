# =======================================
#   _  __         __  __           _
#  | |/ /___     |  \/  | ___   __| |___
#  | ' // _ \    | |\/| |/ _ \ / _` / __|
#  | . \  __/    | |  | | (_) | (_| \__ \
#  |_|\_\___|    |_|  |_|\___/ \__,_|___/
#           @ke_mods
# =======================================

# meta developer: @ke_mods

from .. import loader, utils
from telethon.tl.types import ChatBannedRights
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.types import ChannelParticipantsKicked

@loader.tds
class UnbanAllMod(loader.Module):
    strings = {
        "name": "UnbanAll",
        "no_rights": "<b>❌ I don't have administrator rights to remove restrictions.</b>",
        "success": "<b>✅ All banned chat members have been unbanned.</b>",
        "unban_in_process": "<b>👀 Unbanning users...</b>",
        "no_banned": "<b>ℹ️ There are no banned members in this chat.</b>",
        "error_occured": "<b>💢 An error occurred while unbanning user <code>{}</code>:</b>\n<code>{}</code>",
    }
    strings_ru = {
        "no_rights": "<b>❌ У меня нет прав администратора для снятия ограничений.</b>",
        "success": "<b>✅ Все забаненные участники чата были разблокированы.</b>",
        "unban_in_process": "<b>👀 Разбаниваю пользователей...</b>",
        "no_banned": "<b>ℹ️ В этом чате нет забаненных участников.</b>",
        "error_occured": "<b>💢 Произошла ошибка при разблокировке пользователя <code>{}</code>:</b>\n<code>{}</code>",
    }
    
    @loader.command(ru_doc="- Разбанить всех забаненных пользователей")
    async def unbanallcmd(self, message):
        """- Unban all banned users"""
        chat = await message.get_chat()
    
        if not chat.admin_rights and not chat.creator:
            await utils.answer(message, self.strings["no_rights"])
            return

        await utils.answer(message, self.strings["unban_in_process"])

        no_banned = True

        async for user in self.client.iter_participants(
            message.chat_id, filter=ChannelParticipantsKicked
        ):
        
            no_banned = False
            
            try:
                await self.client(EditBannedRequest(
                    message.chat_id,
                    user.id,
                    ChatBannedRights(until_date=0)
                ))
                
            except Exception as e:
                await utils.answer(message, self.strings["error_occured"].format(user.id, e))
                pass

        if no_banned:
            await utils.answer(message, self.strings["no_banned"])
            return

        await utils.answer(message, self.strings["success"])
