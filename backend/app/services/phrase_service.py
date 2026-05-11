from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import PhraseRecord, PoemRecord


class PhraseService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_phrase(
        self,
        text: str,
        poem_id: str,
        start_line: int,
        end_line: int,
        note: str | None,
        now: datetime,
    ) -> PhraseRecord:
        async with self._session_factory() as session:
            if await session.get(PoemRecord, poem_id) is None:
                raise ValueError("Poem not found")
            phrase = PhraseRecord(
                text=text,
                poem_id=poem_id,
                start_line=start_line,
                end_line=end_line,
                note=note,
                created_at=now,
            )
            session.add(phrase)
            await session.commit()
            return phrase

    async def list_phrases(self) -> list[PhraseRecord]:
        async with self._session_factory() as session:
            result = await session.execute(select(PhraseRecord).order_by(PhraseRecord.created_at.desc()))
            return list(result.scalars())
