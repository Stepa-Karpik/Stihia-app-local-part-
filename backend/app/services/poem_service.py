from datetime import datetime
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import PhraseRecord, PoemRecord, PoemVersionRecord, ProtectedFragmentRecord, TelegramOutboxRecord


class PoemService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_poem(self, title: str, text: str, now: datetime) -> PoemRecord:
        async with self._session_factory() as session:
            poem = PoemRecord(title=title, text=text, created_at=now, updated_at=now)
            session.add(poem)
            await session.flush()
            self._add_version(session, poem, now=now, source="create")
            await self._sync_signature_phrases(session, poem, now=now)
            await self._upsert_outbox(session, poem, now=now)
            await session.commit()
            return poem

    async def edit_poem(self, poem_id: str, title: str, text: str, now: datetime, source: str = "manual") -> PoemRecord:
        async with self._session_factory() as session:
            poem = await session.get(PoemRecord, poem_id)
            if poem is None:
                raise ValueError("Poem not found")
            if poem.title == title and poem.text == text:
                return poem
            poem.title = title
            poem.text = text
            poem.updated_at = now
            await self._sync_signature_phrases(session, poem, now=now)
            if source != "autosave":
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

    async def restore_poem(self, poem_id: str, now: datetime) -> PoemRecord:
        async with self._session_factory() as session:
            poem = await session.get(PoemRecord, poem_id)
            if poem is None:
                raise ValueError("Poem not found")
            poem.is_deleted = False
            poem.deleted_at = None
            poem.updated_at = now
            await session.commit()
            return poem

    async def lock_poem(self, poem_id: str) -> PoemRecord:
        async with self._session_factory() as session:
            poem = await session.get(PoemRecord, poem_id)
            if poem is None:
                raise ValueError("Poem not found")
            poem.is_locked = True
            await session.commit()
            return poem

    async def get_poem(self, poem_id: str) -> PoemRecord:
        async with self._session_factory() as session:
            poem = await session.get(PoemRecord, poem_id)
            if poem is None:
                raise ValueError("Poem not found")
            return poem

    async def list_poems(self, include_deleted: bool = False) -> list[PoemRecord]:
        async with self._session_factory() as session:
            statement = select(PoemRecord).order_by(PoemRecord.updated_at.desc())
            if not include_deleted:
                statement = statement.where(PoemRecord.is_deleted.is_(False))
            result = await session.execute(statement)
            records = list(result.scalars())
            return [record for record in records if include_deleted or not self._is_empty_untouched_draft(record)]

    async def list_versions(self, poem_id: str) -> list[PoemVersionRecord]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(PoemVersionRecord)
                .where(PoemVersionRecord.poem_id == poem_id)
                .order_by(PoemVersionRecord.created_at.asc())
            )
            return list(result.scalars())

    async def create_protected_fragment(
        self,
        poem_id: str,
        text: str,
        start_line: int,
        end_line: int,
        kind: str,
        now: datetime,
    ) -> ProtectedFragmentRecord:
        async with self._session_factory() as session:
            poem = await session.get(PoemRecord, poem_id)
            if poem is None:
                raise ValueError("Poem not found")
            fragment = ProtectedFragmentRecord(
                poem_id=poem_id,
                text=text,
                start_line=start_line,
                end_line=end_line,
                kind=kind,
                created_at=now,
            )
            session.add(fragment)
            await session.commit()
            return fragment

    async def list_protected_fragments(self, poem_id: str) -> list[ProtectedFragmentRecord]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ProtectedFragmentRecord)
                .where(ProtectedFragmentRecord.poem_id == poem_id)
                .order_by(ProtectedFragmentRecord.created_at.asc())
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

    @staticmethod
    def _is_empty_untouched_draft(poem: PoemRecord) -> bool:
        return poem.title.strip() == "Новый стих" and not poem.text.strip()

    async def _sync_signature_phrases(self, session: AsyncSession, poem: PoemRecord, now: datetime) -> None:
        for text, line_number in _extract_signature_phrases(poem.text):
            result = await session.execute(
                select(PhraseRecord).where(
                    PhraseRecord.poem_id == poem.id,
                    PhraseRecord.text == text,
                    PhraseRecord.start_line == line_number,
                    PhraseRecord.end_line == line_number,
                )
            )
            if result.scalar_one_or_none() is not None:
                continue
            session.add(
                PhraseRecord(
                    text=text,
                    poem_id=poem.id,
                    start_line=line_number,
                    end_line=line_number,
                    note="найдено автоматически",
                    created_at=now,
                )
            )


SIGNATURE_WORDS = {
    "агонией",
    "агонии",
    "смертника",
    "пистолете",
    "мольберте",
    "прадети",
    "созвездья",
    "созвездий",
    "бездной",
    "святыни",
    "млечный",
}


def _extract_signature_phrases(text: str) -> list[tuple[str, int]]:
    phrases: list[tuple[str, int]] = []
    seen: set[str] = set()
    for line_number, line in enumerate(text.splitlines(), start=1):
        normalized_line = re.sub(r"[^\w\sёЁ-]+", "", line.lower()).strip()
        words = normalized_line.split()
        if len(words) < 4:
            continue
        if words[0] in {"быть", "и"} and len(words) >= 5:
            words = words[1:]
        if not (set(words) & SIGNATURE_WORDS):
            continue
        phrase_words = words[:6]
        if "агонией" in words and "пистолете" in words:
            start = words.index("агонией")
            end = min(len(words), start + 4)
            phrase_words = words[start:end]
        while phrase_words and phrase_words[-1] in {"в", "во", "на", "из", "и", "под", "над", "для", "с"}:
            phrase_words = phrase_words[:-1]
        phrase = " ".join(phrase_words).strip()
        if len(phrase.split()) < 3 or phrase in seen:
            continue
        seen.add(phrase)
        phrases.append((phrase, line_number))
    return phrases[:8]
