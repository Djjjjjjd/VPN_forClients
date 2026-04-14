from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup

from domain.schemas import AccessSnapshot, PlanInfo


class TelegramBotService:
    def __init__(self, token: str) -> None:
        self._bot = Bot(token=token)

    async def send_welcome(self, chat_id: int, first_name: str | None, plans: list[PlanInfo]) -> None:
        title = first_name or "friend"
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"{plan.name} - {plan.price_amount} {plan.currency}",
                        callback_data=f"plan:{plan.code}",
                    )
                ]
                for plan in plans
            ]
        )
        await self._bot.send_message(
            chat_id=chat_id,
            text=f"Hello, {title}. Choose a VPN plan to continue.",
            reply_markup=keyboard,
        )

    async def send_payment_link(self, chat_id: int, plan_name: str, payment_url: str) -> None:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Pay now", url=payment_url)]]
        )
        await self._bot.send_message(
            chat_id=chat_id,
            text=f"Payment link for {plan_name}. After successful payment your config will arrive here.",
            reply_markup=keyboard,
        )

    async def send_vpn_access(self, chat_id: int, access: AccessSnapshot) -> None:
        if not access.config_path:
            await self._bot.send_message(chat_id=chat_id, text="VPN access is active, but config is not available.")
            return

        await self._bot.send_message(
            chat_id=chat_id,
            text=(
                f"VPN is active until {access.ends_at.isoformat() if access.ends_at else 'unknown'}.\n"
                f"Server IP: {access.server_public_ip or 'unknown'}"
            ),
        )
        await self._bot.send_document(chat_id=chat_id, document=FSInputFile(str(Path(access.config_path))))
        if access.qr_path:
            await self._bot.send_photo(chat_id=chat_id, photo=FSInputFile(str(Path(access.qr_path))))

    async def close(self) -> None:
        await self._bot.session.close()
