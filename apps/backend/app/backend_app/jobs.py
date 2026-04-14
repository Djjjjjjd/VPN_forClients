import asyncio
import logging

from backend_app.core.config import get_settings
from backend_app.core.logging import configure_logging
from backend_app.services.application import build_runtime
from db.session import get_async_session


async def run_cleanup() -> int:
    settings = get_settings()
    async for session in get_async_session(settings.database_url):
        service = build_runtime(session, settings)
        try:
            return await service.expire_due_subscriptions()
        finally:
            await service.bot_service.close()
    return 0


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    count = asyncio.run(run_cleanup())
    logging.getLogger(__name__).info("cleanup finished", extra={"expired": count})


if __name__ == "__main__":
    main()
