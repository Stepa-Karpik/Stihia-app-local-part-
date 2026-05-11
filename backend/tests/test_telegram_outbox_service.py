from datetime import UTC, datetime

import httpx
import pytest

from app.db.session import create_session_factory, init_models
from app.services.poem_service import PoemService
from app.services.telegram_outbox_service import TelegramOutboxService


@pytest.mark.asyncio
async def test_outbox_keeps_item_when_bot_server_is_unavailable(tmp_path):
    session_factory = create_session_factory(f"sqlite+aiosqlite:///{tmp_path / 'outbox.db'}")
    await init_models(session_factory)
    poem_service = PoemService(session_factory)
    poem = await poem_service.create_poem("Стих", "строка", now=datetime(2026, 5, 12, tzinfo=UTC))

    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    outbox = TelegramOutboxService(
        session_factory,
        bot_server_url="http://bot",
        bot_server_token="token",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    result = await outbox.flush_once()

    pending = await poem_service.list_pending_telegram_items()
    assert result.sent == 0
    assert result.failed == 1
    assert pending[0].poem_id == poem.id
    assert pending[0].attempts == 1


@pytest.mark.asyncio
async def test_outbox_saves_message_id_and_removes_item_after_success(tmp_path):
    session_factory = create_session_factory(f"sqlite+aiosqlite:///{tmp_path / 'outbox.db'}")
    await init_models(session_factory)
    poem_service = PoemService(session_factory)
    poem = await poem_service.create_poem("Стих", "строка", now=datetime(2026, 5, 12, tzinfo=UTC))

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-stihia-token"] == "token"
        return httpx.Response(200, json={"poem_id": poem.id, "telegram_message_id": 88, "action": "send"})

    outbox = TelegramOutboxService(
        session_factory,
        bot_server_url="http://bot",
        bot_server_token="token",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://bot"),
    )

    result = await outbox.flush_once()

    refreshed = (await poem_service.list_poems())[0]
    assert result.sent == 1
    assert result.failed == 0
    assert refreshed.telegram_message_id == 88
    assert await poem_service.list_pending_telegram_items() == []
