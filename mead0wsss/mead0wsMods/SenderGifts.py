# -- version --
__version__ = (1, 2, 1)
# -- version --


# ███╗░░░███╗███████╗░█████╗░██████╗░░█████╗░░██╗░░░░░░░██╗░██████╗░██████╗
# ████╗░████║██╔════╝██╔══██╗██╔══██╗██╔══██╗░██║░░██╗░░██║██╔════╝██╔════╝
# ██╔████╔██║█████╗░░███████║██║░░██║██║░░██║░╚██╗████╗██╔╝╚█████╗░╚█████╗░
# ██║╚██╔╝██║██╔══╝░░██╔══██║██║░░██║██║░░██║░░████╔═████║░░╚═══██╗░╚═══██╗
# ██║░╚═╝░██║███████╗██║░░██║██████╔╝╚█████╔╝░░╚██╔╝░╚██╔╝░██████╔╝██████╔╝
# ╚═╝░░░░░╚═╝╚══════╝╚═╝░░╚═╝╚═════╝░░╚════╝░░░░╚═╝░░░╚═╝░░╚═════╝░╚═════╝░
#                © Copyright 2025
#            ✈ https://t.me/mead0wssMods


# meta developer: @mead0wssMods x @nullmod
# scope: heroku_only

from .. import loader, utils
from herokutl.tl.functions.payments import GetPaymentFormRequest, SendStarsFormRequest, GetStarsStatusRequest
from herokutl.tl.types import InputInvoiceStarGift, TextWithEntities
from herokutl.errors.rpcerrorlist import BadRequestError
import logging
import herokutl

@loader.tds
class SenderGifts(loader.Module):
    """Модуль для отправки подарков Telegram прямиком в чате"""
    
    strings = {
        "name": "SenderGifts",
        "usage": "<emoji document_id=4958526153955476488>❌</emoji> Используйте в формате: <code>.sendgift @username текст</code> или реплай + <code>.sendgift текст</code>",
        "checking_user": "<emoji document_id=5206634672204829887>🔍</emoji> Проверка пользователя...",
        "checking_balance": "<emoji document_id=5206634672204829887>🔍</emoji> Проверка баланса...",
        "user_not_found": "<emoji document_id=4958526153955476488>❌</emoji> Пользователь не найден",
        "gift_menu": "<emoji document_id=5931696400982088015>🎁</emoji> Выберите категорию подарков.\n\n<emoji document_id=6032693626394382504>👤</emoji> Пользователь: {}\n<emoji document_id=5873153278023307367>📄</emoji> Текст: {}\n<emoji document_id=5951810621887484519>⭐</emoji> Баланс: {} звезд",
        "category_menu": "<emoji document_id=5931696400982088015>🎁</emoji> Подарки за {} ⭐\n\n<emoji document_id=6032693626394382504>👤</emoji> Пользователь: {}\n<emoji document_id=5873153278023307367>📄</emoji> Текст: {}",
        "sending_gift": "<emoji document_id=5201691993775818138>🛫</emoji> Отправка подарка...",
        "gift_sent": "<emoji document_id=5021905410089550576>✅</emoji> Подарок успешно отправлен!",
        "not_enough_stars": "<emoji document_id=4958526153955476488>❌</emoji> Недостаточно звезд для отправки подарка {}!",
        "min_stars_error": "<emoji document_id=4958526153955476488>❌</emoji> Недостаточно звезд для отправки минимального подарка!",
        "no_available_gifts": "<emoji document_id=4958526153955476488>❌</emoji> Нет доступных подарков для вашего баланса",
        "balance_error": "<emoji document_id=4958526153955476488>❌</emoji> Ошибка при проверке баланса",
    }
    
    gift_categories = {
        15: [
            {"id": 5170145012310081615, "emoji": "❤️", "name": "Сердце"},
            {"id": 5170233102089322756, "emoji": "🧸", "name": "Мишка"},
        ],
        25: [
            {"id": 5170250947678437525, "emoji": "🎁", "name": "Подарок"},
            {"id": 5168103777563050263, "emoji": "🌹", "name": "Роза"},
        ],
        50: [
            {"id": 5170144170496491616, "emoji": "🎂", "name": "Тортик"},
            {"id": 5170314324215857265, "emoji": "💐", "name": "Цветы"},
            {"id": 5170564780938756245, "emoji": "🚀", "name": "Ракета"},
            {"id": 5922558454332916696, "emoji": "🎄", "name": "Ёлка"},
        ],
        100: [
            {"id": 5168043875654172773, "emoji": "🏆", "name": "Кубок"},
            {"id": 5170690322832818290, "emoji": "💍", "name": "Кольцо"},
            {"id": 5170521118301225164, "emoji": "💎", "name": "Алмаз"},
        ]
    }

    async def client_ready(self, client, db):
        self.client = client

    async def get_star_balance(self):
        try:
            balance_info = (await self.client(GetStarsStatusRequest("me")))
            return balance_info.balance.amount
        except Exception as e:
            logging.error(f"Error getting balance: {e}")
            return 0

    @loader.command()
    async def sendgift(self, message):
        """- <username> <text*> - отправить подарок пользователю (* - необязательный параметр.) Поддерживается реплай режим."""
        args = utils.get_args_html(message)
        reply = await message.get_reply_message()
        if reply:
            user = reply.sender
            text = args if args else ""
        else:
            if not args:
                await utils.answer(message, self.strings["usage"])
                return
            parts = args.split(maxsplit=1)
            if len(parts) < 1:
                await utils.answer(message, self.strings["usage"])
                return
            username = parts[0]
            text = parts[1] if len(parts) > 1 else ""
            if username.startswith('@'):
                username = username[1:]
            msg = await utils.answer(message, self.strings["checking_user"])
            try:
                user = await self.client.get_entity(username)
            except Exception as e:
                logging.error(f"User not found: {e}")
                await utils.answer(msg, self.strings["user_not_found"])
                return

        balance_msg = await utils.answer(message, self.strings["checking_balance"])
        try:
            balance = await self.get_star_balance()
        except Exception as e:
            logging.error(f"Balance error: {e}")
            await utils.answer(balance_msg, self.strings["balance_error"])
            return

        min_price = min(self.gift_categories.keys())
        if balance < min_price:
            await utils.answer(balance_msg, self.strings["min_stars_error"])
            return

        available_categories = [price for price in self.gift_categories.keys() if balance >= price]
        if not available_categories:
            await utils.answer(balance_msg, self.strings["no_available_gifts"])
            return
        buttons = []
        row = []
        for price in sorted(available_categories):
            row.append({
                "text": f"{price} ⭐",
                "callback": self._show_category,
                "args": (user.id, price, text, balance, message.id),
            })
            if len(row) == 2:
                buttons.append(row)
                row = []
        
        if row:
            buttons.append(row)
        
        await utils.answer(
            balance_msg,
            self.strings["gift_menu"].format(
                f"@{user.username}" if user.username else user.first_name,
                text if text else "-",
                balance
            ),
            reply_markup=buttons
        )

    async def _show_category(self, call, user_id, price, text, balance, msg_id):
        gifts = self.gift_categories[price]
        buttons = []
        row = []
        for gift in gifts:
            row.append({
                "text": gift["emoji"],
                "callback": self._send_gift,
                "args": (user_id, gift["id"], text, gift["emoji"], msg_id, balance),
            })
            if len(row) == 3:
                buttons.append(row)
                row = []
        
        if row:
            buttons.append(row)
        buttons.append([{
            "text": "⬅️ Назад",
            "callback": self._back_to_categories,
            "args": (user_id, text, balance, msg_id),
        }])
        
        try:
            user = await self.client.get_entity(user_id)
            user_display = f"@{user.username}" if user.username else user.first_name
        except:
            user_display = f"ID: {user_id}"
        
        await call.edit(
            self.strings["category_menu"].format(
                price,
                user_display,
                text if text else "-"
            ),
            reply_markup=buttons
        )

    async def _back_to_categories(self, call, user_id, text, balance, msg_id):
        try:
            user = await self.client.get_entity(user_id)
        except:
            await call.answer("Ошибка получения пользователя", show_alert=True)
            return
        
        available_categories = [price for price in self.gift_categories.keys() if balance >= price]
        
        buttons = []
        row = []
        for price in sorted(available_categories):
            row.append({
                "text": f"{price} ⭐",
                "callback": self._show_category,
                "args": (user_id, price, text, balance, msg_id),
            })
            if len(row) == 2:
                buttons.append(row)
                row = []
        
        if row:
            buttons.append(row)
        
        await call.edit(
            self.strings["gift_menu"].format(
                f"@{user.username}" if user.username else user.first_name,
                text if text else "-",
                balance
            ),
            reply_markup=buttons
        )

    async def _send_gift(self, call, user_id, gift_id, text, gift_emoji, msg_id, balance):
        try:
            await call.edit(
                self.strings["sending_gift"],
                reply_markup=None
            )

            parse_mode = herokutl.utils.sanitize_parse_mode(
                self.client.parse_mode,
            )
            text, entities = parse_mode.parse(text)

            user = await self.client.get_input_entity(user_id)
            inv = InputInvoiceStarGift(
                user,
                gift_id,
                message=TextWithEntities(text, entities) if text else TextWithEntities("", [])
            )
            form = await self.client(GetPaymentFormRequest(inv))
            result = await self.client(SendStarsFormRequest(form.form_id, inv))
            
            await call.edit(self.strings["gift_sent"])
            
        except BadRequestError as e:
            if "BALANCE_TOO_LOW" in str(e):
                await call.edit(
                    self.strings["not_enough_stars"].format(gift_emoji),
                    reply_markup=None
                )
            else:
                logging.error(f"Error sending gift: {e}")
                await call.edit(
                    f"<emoji document_id=4958526153955476488>❌</emoji> Ошибка при отправке подарка: {str(e)}",
                    reply_markup=None
                )
        except Exception as e:
            logging.error(f"Error sending gift: {e}")
            await call.edit(
                f"<emoji document_id=4958526153955476488>❌</emoji> Ошибка при отправке подарка: {str(e)}",
                reply_markup=None
            )
