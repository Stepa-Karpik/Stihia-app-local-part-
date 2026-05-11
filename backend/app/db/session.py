from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.settings import AppSettings
from app.db.models import Base


def create_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(database_url, future=True)
    return async_sessionmaker(engine, expire_on_commit=False)


SessionFactory = create_session_factory(AppSettings().database_url)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session


async def init_models(session_factory: async_sessionmaker[AsyncSession] = SessionFactory) -> None:
    engine = session_factory.kw["bind"]
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
