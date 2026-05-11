from datetime import UTC, datetime

import pytest

from app.db.session import create_session_factory, init_models
from app.services.poem_service import PoemService


@pytest.mark.asyncio
async def test_poem_service_creates_version_and_telegram_outbox(tmp_path):
    session_factory = create_session_factory(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    await init_models(session_factory)
    service = PoemService(session_factory)
    now = datetime(2026, 5, 12, 10, 0, tzinfo=UTC)

    poem = await service.create_poem(title="Первый", text="строка", now=now)

    assert poem.title == "Первый"
    assert len(await service.list_versions(poem.id)) == 1
    assert len(await service.list_pending_telegram_items()) == 1


@pytest.mark.asyncio
async def test_poem_service_edit_preserves_created_at_and_updates_outbox(tmp_path):
    session_factory = create_session_factory(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    await init_models(session_factory)
    service = PoemService(session_factory)
    created_at = datetime(2026, 5, 12, 10, 0, tzinfo=UTC)
    edited_at = datetime(2026, 5, 12, 12, 0, tzinfo=UTC)
    poem = await service.create_poem(title="Первый", text="строка", now=created_at)

    edited = await service.edit_poem(poem.id, title="Первый", text="новая строка", now=edited_at)

    assert edited.created_at == created_at
    assert edited.updated_at == edited_at
    assert len(await service.list_versions(poem.id)) == 2
    outbox = await service.list_pending_telegram_items()
    assert len(outbox) == 1
    assert outbox[0].text == "новая строка"


@pytest.mark.asyncio
async def test_poem_service_soft_deletes_and_lists_deleted_separately(tmp_path):
    session_factory = create_session_factory(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    await init_models(session_factory)
    service = PoemService(session_factory)
    now = datetime(2026, 5, 12, 10, 0, tzinfo=UTC)
    poem = await service.create_poem(title="Первый", text="строка", now=now)

    await service.hide_poem(poem.id, now=now)

    assert await service.list_poems(include_deleted=False) == []
    deleted = await service.list_poems(include_deleted=True)
    assert len(deleted) == 1
    assert deleted[0].is_deleted is True
