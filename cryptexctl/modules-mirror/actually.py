__version__ = (2, 0, 0)
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
# actually.py
# meta developer: @systemxplore
# scope: hikka_only
# scope: hikka_min 1.6.3
from .. import loader, utils

class ActuallyMod(loader.Module):
    """ehm, actually🤓️."""
    strings = {
        "name": "Actually",
        "example_usage": "Используйте: .actually ur text"
    }

    @loader.command()
    async def actually(self, message):
        """ehm, actually'"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["example_usage"])
            return
        
        # Формируем ответ
        formatted_text = f"ehm,actually {args} {'🤓' * 10}"
        
        # Отправляем текст и удаляем команду
        await message.respond(formatted_text)
        await message.delete()
