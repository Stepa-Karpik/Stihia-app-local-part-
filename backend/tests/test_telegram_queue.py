import pytest

from app.services.telegram_queue import QueueItem, TelegramSyncQueue


class FailingBotClient:
    async def sync_poem(self, item: QueueItem) -> None:
        raise ConnectionError("bot server is unavailable")


class WorkingBotClient:
    def __init__(self) -> None:
        self.synced: list[QueueItem] = []

    async def sync_poem(self, item: QueueItem) -> None:
        self.synced.append(item)


@pytest.mark.asyncio
async def test_queue_keeps_item_when_bot_is_unavailable():
    queue = TelegramSyncQueue()
    item = QueueItem(poem_id="p1", title="Стих", text="строка", telegram_message_id=None)
    queue.enqueue(item)

    await queue.flush(FailingBotClient())

    assert queue.pending() == [item]


@pytest.mark.asyncio
async def test_queue_flushes_when_connection_returns():
    queue = TelegramSyncQueue()
    item = QueueItem(poem_id="p1", title="Стих", text="строка", telegram_message_id=42)
    client = WorkingBotClient()
    queue.enqueue(item)

    await queue.flush(client)

    assert queue.pending() == []
    assert client.synced == [item]
