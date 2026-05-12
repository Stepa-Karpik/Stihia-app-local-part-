from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import PhraseRecord, PoemRecord
from app.services.poem_service import _extract_signature_phrases


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
            existing = await session.execute(
                select(PhraseRecord).where(
                    PhraseRecord.poem_id == poem_id,
                    PhraseRecord.text == text,
                    PhraseRecord.start_line == start_line,
                    PhraseRecord.end_line == end_line,
                )
            )
            phrase = existing.scalars().first()
            if phrase is not None:
                phrase.note = note
                phrase.created_at = now
                await session.commit()
                return phrase
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
            await self._backfill_signature_phrases(session)
            await self._cleanup_auto_phrase_text(session)
            result = await session.execute(select(PhraseRecord).order_by(PhraseRecord.created_at.desc()))
            return list(result.scalars())

    async def _backfill_signature_phrases(self, session: AsyncSession) -> None:
        poems_result = await session.execute(select(PoemRecord).where(PoemRecord.is_deleted.is_(False)))
        changed = False
        for poem in poems_result.scalars():
            for text, line_number in _extract_signature_phrases(poem.text):
                existing = await session.execute(
                    select(PhraseRecord).where(
                        PhraseRecord.poem_id == poem.id,
                        PhraseRecord.text == text,
                        PhraseRecord.start_line == line_number,
                        PhraseRecord.end_line == line_number,
                    )
                )
                if existing.scalars().first() is not None:
                    continue
                session.add(
                    PhraseRecord(
                        text=text,
                        poem_id=poem.id,
                        start_line=line_number,
                        end_line=line_number,
                        note="найдено автоматически",
                        created_at=poem.updated_at,
                    )
                )
                changed = True
        if changed:
            await session.commit()

    async def _cleanup_auto_phrase_text(self, session: AsyncSession) -> None:
        result = await session.execute(select(PhraseRecord).where(PhraseRecord.note == "найдено автоматически"))
        auto_phrases = list(result.scalars())
        changed = False
        for phrase in auto_phrases:
            cleaned = _trim_trailing_stopword(phrase.text)
            if cleaned == phrase.text or len(cleaned.split()) < 3:
                continue
            duplicate = await session.execute(
                select(PhraseRecord).where(
                    PhraseRecord.poem_id == phrase.poem_id,
                    PhraseRecord.text == cleaned,
                    PhraseRecord.start_line == phrase.start_line,
                    PhraseRecord.end_line == phrase.end_line,
                )
            )
            if duplicate.scalars().first() is not None:
                await session.delete(phrase)
            else:
                phrase.text = cleaned
            changed = True
        grouped: dict[tuple[str, int, int], list[PhraseRecord]] = {}
        for phrase in auto_phrases:
            grouped.setdefault((phrase.poem_id, phrase.start_line, phrase.end_line), []).append(phrase)
        for records in grouped.values():
            sorted_records = sorted(records, key=lambda item: len(item.text.split()), reverse=True)
            kept: list[PhraseRecord] = []
            for phrase in sorted_records:
                if any(_is_shorter_duplicate(phrase.text, other.text) for other in kept):
                    await session.delete(phrase)
                    changed = True
                    continue
                kept.append(phrase)
        if changed:
            await session.commit()


def _trim_trailing_stopword(text: str) -> str:
    words = text.split()
    while words and words[-1] in {"в", "во", "на", "из", "и", "под", "над", "для", "с"}:
        words = words[:-1]
    return " ".join(words)


def _is_shorter_duplicate(candidate: str, keeper: str) -> bool:
    candidate_words = candidate.split()
    keeper_words = keeper.split()
    if len(candidate_words) >= len(keeper_words):
        return False
    return " ".join(keeper_words[: len(candidate_words)]) == candidate or set(candidate_words).issubset(set(keeper_words))
