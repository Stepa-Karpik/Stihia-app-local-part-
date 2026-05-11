from datetime import UTC, datetime

from app.domain.poems import Poem


def test_edit_updates_last_edited_without_changing_created_at():
    created_at = datetime(2026, 5, 12, 10, 0, tzinfo=UTC)
    edited_at = datetime(2026, 5, 12, 11, 30, tzinfo=UTC)
    poem = Poem.create(title="Первый", text="строка", now=created_at)

    poem.edit(title="Первый", text="новая строка", now=edited_at)

    assert poem.created_at == created_at
    assert poem.updated_at == edited_at
    assert poem.versions[-1].text == "новая строка"


def test_delete_is_soft_delete():
    now = datetime(2026, 5, 12, 10, 0, tzinfo=UTC)
    poem = Poem.create(title="Первый", text="строка", now=now)

    poem.hide(now=now)

    assert poem.is_deleted is True
    assert poem.deleted_at == now


def test_locked_poem_is_session_unlockable():
    now = datetime(2026, 5, 12, 10, 0, tzinfo=UTC)
    poem = Poem.create(title="Закрытый", text="текст", now=now)

    poem.lock()

    assert poem.is_locked is True
    assert poem.visible_state(session_unlocked=False) == "locked"
    assert poem.visible_state(session_unlocked=True) == "unlocked"
