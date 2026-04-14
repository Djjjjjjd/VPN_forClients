from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@lru_cache(maxsize=4)
def get_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(database_url, future=True)
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_async_session(database_url: str) -> AsyncIterator[AsyncSession]:
    factory = get_session_factory(database_url)
    async with factory() as session:
        yield session
