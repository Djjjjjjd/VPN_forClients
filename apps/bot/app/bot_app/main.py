import asyncio
import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from backend_app.core.config import get_settings
from backend_app.core.logging import configure_logging

router = Router()


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(
        "Webhook mode is the production default. This polling runner exists for local testing only."
    )


async def run() -> None:
    settings = get_settings()
    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    await dispatcher.start_polling(bot)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logging.getLogger(__name__).info("starting polling bot")
    asyncio.run(run())


if __name__ == "__main__":
    main()
