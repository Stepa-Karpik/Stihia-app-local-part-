from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import PoemRecord, PoemVersionRecord, TelegramOutboxRecord


class PoemService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_poem(self, title: str, text: str, now: datetime) -> PoemRecord:
        async with self._session_factory() as session:
            poem = PoemRecord(title=title, text=text, created_at=now, updated_at=now)
            session.add(poem)
            await session.flush()
            self._add_version(session, poem, now=now, source="create")
            await self._upsert_outbox(session, poem, now=now)
            await session.commit()
            return poem

    async def edit_poem(self, poem_id: str, title: str, text: str, now: datetime, source: str = "manual") -> PoemRecord:
        async with self._session_factory() as session:
            poem = await session.get(PoemRecord, poem_id)
            if poem is None:
                raise ValueError("Poem not found")
            poem.title = title
            poem.text = text
            poem.updated_at = now
            self._add_version(session, poem, now=now, source=source)
            await self._upsert_outbox(session, poem, now=now)
            await session.commit()
            return poem

    async def hide_poem(self, poem_id: str, now: datetime) -> None:
        async with self._session_factory() as session:
            poem = await session.get(PoemRecord, poem_id)
            if poem is None:
                raise ValueError("Poem not found")
            poem.is_deleted = True
            poem.deleted_at = now
            poem.updated_at = now
            await session.commit()

    async def list_poems(self, include_deleted: bool = False) -> list[PoemRecord]:
        async with self._session_factory() as session:
            statement = select(PoemRecord).order_by(PoemRecord.updated_at.desc())
            if not include_deleted:
                statement = statement.where(PoemRecord.is_deleted.is_(False))
            result = await session.execute(statement)
            return list(result.scalars())

    async def list_versions(self, poem_id: str) -> list[PoemVersionRecord]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(PoemVersionRecord)
                .where(PoemVersionRecord.poem_id == poem_id)
                .order_by(PoemVersionRecord.created_at.asc())
            )
            return list(result.scalars())

    async def list_pending_telegram_items(self) -> list[TelegramOutboxRecord]:
        async with self._session_factory() as session:
            result = await session.execute(select(TelegramOutboxRecord).order_by(TelegramOutboxRecord.updated_at.asc()))
            return list(result.scalars())

    def _add_version(self, session: AsyncSession, poem: PoemRecord, now: datetime, source: str) -> None:
        session.add(
            PoemVersionRecord(
                poem_id=poem.id,
                title=poem.title,
                text=poem.text,
                created_at=now,
                source=source,
            )
        )

    async def _upsert_outbox(self, session: AsyncSession, poem: PoemRecord, now: datetime) -> None:
        result = await session.execute(select(TelegramOutboxRecord).where(TelegramOutboxRecord.poem_id == poem.id))
        outbox = result.scalar_one_or_none()
        if outbox is None:
            session.add(
                TelegramOutboxRecord(
                    poem_id=poem.id,
                    title=poem.title,
                    text=poem.text,
                    telegram_message_id=poem.telegram_message_id,
                    created_at=now,
                    updated_at=now,
                )
            )
            return
        outbox.title = poem.title
        outbox.text = poem.text
        outbox.telegram_message_id = poem.telegram_message_id
        outbox.updated_at = now
