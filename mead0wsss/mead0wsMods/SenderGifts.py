# -- version --
__version__ = (1, 2, 3)
# -- version --


# ███╗░░░███╗███████╗░█████╗░██████╗░░█████╗░░██╗░░░░░░░██╗░██████╗░██████╗
# ████╗░████║██╔════╝██╔══██╗██╔══██╗██╔══██╗░██║░░██╗░░██║██╔════╝██╔════╝
# ██╔████╔██║█████╗░░███████║██║░░██║██║░░██║░╚██╗████╗██╔╝╚█████╗░╚█████╗░
# ██║╚██╔╝██║██╔══╝░░██╔══██║██║░░██║██║░░██║░░████╔═████║░░╚═══██╗░╚═══██╗
# ██║░╚═╝░██║███████╗██║░░██║██████╔╝╚█████╔╝░░╚██╔╝░╚██╔╝░██████╔╝██████╔╝
# ╚═╝░░░░░╚═╝╚══════╝╚═╝░░╚═╝╚═════╝░░╚════╝░░░░╚═╝░░░╚═╝░░╚═════╝░╚═════╝░
#                © Copyright 2026
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
        "gift_menu": "<tg-emoji emoji-id=5370781982886220096>🎁</tg-emoji> Выберите категорию подарков.\n\n<tg-emoji emoji-id=6048471184461271609>👤</tg-emoji> Пользователь: {}\n<tg-emoji emoji-id=6048762138430803961>📂</tg-emoji> Текст: {}\n<tg-emoji emoji-id=5321485469249198987>⭐️</tg-emoji> Баланс: {} звезд",
        "category_menu": "<tg-emoji emoji-id=5370781982886220096>🎁</tg-emoji> Подарки за {} ⭐\n\n<tg-emoji emoji-id=6048471184461271609>👤</tg-emoji> Пользователь: {}\n<tg-emoji emoji-id=6048762138430803961>📂</tg-emoji> Текст: {}",
        "unique_category_menu": "<tg-emoji emoji-id=5370781982886220096>🎁</tg-emoji> {}\n\n<tg-emoji emoji-id=6048471184461271609>👤</tg-emoji> Пользователь: {}\n<tg-emoji emoji-id=6048762138430803961>📂</tg-emoji> Текст: {}",
        "privacy_menu": "<tg-emoji emoji-id=5370781982886220096>🎁</tg-emoji> Выбран подарок: {}\n\nКак отправить подарок?",
        "sending_gift": "<emoji document_id=5201691993775818138>🛫</emoji> Отправка подарка...",
        "gift_sent": "<emoji document_id=5021905410089550576>✅</emoji> Подарок успешно отправлен!",
        "not_enough_stars": "<emoji document_id=4958526153955476488>❌</emoji> Недостаточно звезд для отправки подарка {}!",
        "min_stars_error": "<emoji document_id=4958526153955476488>❌</emoji> Недостаточно звезд для отправки минимального подарка!",
        "no_available_gifts": "<emoji document_id=4958526153955476488>❌</emoji> Нет доступных подарков для вашего баланса",
        "balance_error": "<emoji document_id=4958526153955476488>❌</emoji> Ошибка при проверке баланса",
        "btn_public": "📢 Публично",
        "btn_anon": "🕵️ Анонимно",
    }

    regular_gifts = {
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
        ],
        100: [
            {"id": 5168043875654172773, "emoji": "🏆", "name": "Кубок"},
            {"id": 5170690322832818290, "emoji": "💍", "name": "Кольцо"},
            {"id": 5170521118301225164, "emoji": "💎", "name": "Алмаз"},
        ]
    }

    unique_gifts = {
        "new_year": {
            "name": "🎄 Новогодние подарки",
            "gifts": [
                {"id": 5922558454332916696, "emoji": "🎄", "name": "Ёлка", "price": 50},
                {"id": 5956217000635139069, "emoji": "🧸", "name": "Новогодний мишка", "price": 50},
            ]
        },
        "valentines": {
            "name": "💘 День святого валентина",
            "gifts": [
                {"id": 5800655655995968830, "emoji": "🧸", "name": "14 Февраля мишка", "price": 50},
                {"id": 5801108895304779062, "emoji": "💘", "name": "14 Февраля сердце", "price": 50},
            ]
        },
        "march_8th": {
            "name": "🌷 8 Марта",
            "gifts": [  
                {"id": 5866352046986232958, "emoji": "🧸", "name": "8 Марта мишка", "price": 50},
            ]
        }
    }

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
            try:
                username = int(username)
            except ValueError:
                pass
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

        min_price = min(self.regular_gifts.keys())
        if balance < min_price:
            await utils.answer(balance_msg, self.strings["min_stars_error"])
            return

        helper_msg = await self.inline.form("🪐", balance_msg)
        

        await self._show_main_menu_logic(helper_msg, user.id, text, balance, message.id, answer=True)

    async def _show_main_menu_logic(self, msg_or_call, user_id, text, balance, msg_id, answer=False):
        try:
            user = await self.client.get_entity(user_id)
            user_display = f"@{user.username}" if user.username else user.first_name
        except:
            user_display = f"ID: {user_id}"

        buttons = [
            [{
                "text": "🎁 Обычные подарки",
                "callback": self._show_regular_categories,
                "args": (user_id, text, balance, msg_id),
            }],
            [{
                "text": "✨ Уникальные подарки",
                "callback": self._show_unique_categories,
                "args": (user_id, text, balance, msg_id),
            }]
        ]
        
        text_menu = self.strings["gift_menu"].format(user_display, text if text else "-", balance)
        
        if answer:
            await utils.answer(msg_or_call, text_menu, reply_markup=buttons)
        else:
            await msg_or_call.edit(text_menu, reply_markup=buttons)

    async def _show_main_menu(self, call, user_id, text, balance, msg_id):
        await self._show_main_menu_logic(call, user_id, text, balance, msg_id)

    async def _show_regular_categories(self, call, user_id, text, balance, msg_id):
        try:
            user = await self.client.get_entity(user_id)
            user_display = f"@{user.username}" if user.username else user.first_name
        except:
            user_display = f"ID: {user_id}"

        available_categories = [price for price in self.regular_gifts.keys() if balance >= price]
        
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
            
        buttons.append([{
            "text": "⬅️ Назад",
            "callback": self._show_main_menu,
            "args": (user_id, text, balance, msg_id),
        }])

        await call.edit(
            self.strings["gift_menu"].format(user_display, text if text else "-", balance),
            reply_markup=buttons
        )

    async def _show_unique_categories(self, call, user_id, text, balance, msg_id):
        try:
            user = await self.client.get_entity(user_id)
            user_display = f"@{user.username}" if user.username else user.first_name
        except:
            user_display = f"ID: {user_id}"

        buttons = []
        for cat_id, cat_data in self.unique_gifts.items():
            if any(balance >= gift["price"] for gift in cat_data["gifts"]):
                buttons.append([{
                    "text": cat_data["name"],
                    "callback": self._show_unique_category_gifts,
                    "args": (user_id, cat_id, text, balance, msg_id),
                }])

        if not buttons:
            buttons.append([{
                "text": "❌ Нет доступных (баланс)",
                "callback": self._show_main_menu,
                "args": (user_id, text, balance, msg_id),
            }])

        buttons.append([{
            "text": "⬅️ Назад",
            "callback": self._show_main_menu,
            "args": (user_id, text, balance, msg_id),
        }])

        await call.edit(
            self.strings["gift_menu"].format(user_display, text if text else "-", balance),
            reply_markup=buttons
        )

    async def _show_category(self, call, user_id, price, text, balance, msg_id):
        gifts = self.regular_gifts[price]
        buttons = []
        row = []
        for gift in gifts:
            row.append({
                "text": gift["emoji"],
                "callback": self._select_privacy,
                "args": (user_id, gift["id"], text, gift["emoji"], msg_id, balance, "regular", price),
            })
            if len(row) == 3:
                buttons.append(row)
                row = []
        
        if row:
            buttons.append(row)
        buttons.append([{
            "text": "⬅️ Назад",
            "callback": self._show_regular_categories,
            "args": (user_id, text, balance, msg_id),
        }])
        
        try:
            user = await self.client.get_entity(user_id)
            user_display = f"@{user.username}" if user.username else user.first_name
        except:
            user_display = f"ID: {user_id}"
        
        await call.edit(
            self.strings["category_menu"].format(price, user_display, text if text else "-"),
            reply_markup=buttons
        )

    async def _show_unique_category_gifts(self, call, user_id, cat_id, text, balance, msg_id):
        category = self.unique_gifts[cat_id]
        buttons = []
        row = []
        for gift in category["gifts"]:
            if balance >= gift["price"]:
                row.append({
                    "text": gift["emoji"],
                    "callback": self._select_privacy,
                    "args": (user_id, gift["id"], text, gift["emoji"], msg_id, balance, "unique", cat_id),
                })
            if len(row) == 3:
                buttons.append(row)
                row = []
        
        if row:
            buttons.append(row)
        buttons.append([{
            "text": "⬅️ Назад",
            "callback": self._show_unique_categories,
            "args": (user_id, text, balance, msg_id),
        }])
        
        try:
            user = await self.client.get_entity(user_id)
            user_display = f"@{user.username}" if user.username else user.first_name
        except:
            user_display = f"ID: {user_id}"
        
        await call.edit(
            self.strings["unique_category_menu"].format(category["name"], user_display, text if text else "-"),
            reply_markup=buttons
        )

    async def _select_privacy(self, call, user_id, gift_id, text, gift_emoji, msg_id, balance, gift_type, type_arg):
        if gift_type == "regular":
            back_callback = self._show_category
        else:
            back_callback = self._show_unique_category_gifts

        buttons = [
            [
                {
                    "text": self.strings["btn_public"],
                    "callback": self._send_gift,
                    "args": (user_id, gift_id, text, gift_emoji, msg_id, balance, False)
                },
                {
                    "text": self.strings["btn_anon"],
                    "callback": self._send_gift,
                    "args": (user_id, gift_id, text, gift_emoji, msg_id, balance, True)
                }
            ],
            [
                {
                    "text": "⬅️ Назад",
                    "callback": back_callback,
                    "args": (user_id, type_arg, text, balance, msg_id)
                }
            ]
        ]
        
        await call.edit(
            self.strings["privacy_menu"].format(gift_emoji),
            reply_markup=buttons
        )

    async def _send_gift(self, call, user_id, gift_id, text, gift_emoji, msg_id, balance, hide_name):
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
                hide_name=hide_name,
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
