from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class QueueItem:
    poem_id: str
    title: str
    text: str
    telegram_message_id: int | None


class BotSyncClient(Protocol):
    async def sync_poem(self, item: QueueItem) -> None:
        """Send or edit a poem backup on the Telegram bot server."""


class TelegramSyncQueue:
    def __init__(self) -> None:
        self._items: list[QueueItem] = []

    def enqueue(self, item: QueueItem) -> None:
        existing_index = next((index for index, queued in enumerate(self._items) if queued.poem_id == item.poem_id), None)
        if existing_index is None:
            self._items.append(item)
            return
        self._items[existing_index] = item

    def pending(self) -> list[QueueItem]:
        return list(self._items)

    async def flush(self, client: BotSyncClient) -> None:
        remaining: list[QueueItem] = []
        for item in self._items:
            try:
                await client.sync_poem(item)
            except ConnectionError:
                remaining.append(item)
        self._items = remaining
