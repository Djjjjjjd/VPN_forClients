from collections.abc import AsyncIterator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend_app.core.config import Settings, get_settings
from db.session import get_async_session


async def get_db_session(
    settings: Settings = Depends(get_settings),
) -> AsyncIterator[AsyncSession]:
    async for session in get_async_session(settings.database_url):
        yield session


def require_internal_token(
    x_internal_token: str = Header(default=""),
    settings: Settings = Depends(get_settings),
) -> None:
    if x_internal_token != settings.internal_api_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid internal token")
