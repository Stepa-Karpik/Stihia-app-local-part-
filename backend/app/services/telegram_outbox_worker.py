import asyncio
from typing import Protocol


class FlushableOutbox(Protocol):
    async def flush_once(self) -> object:
        """Flush pending Telegram backup items once."""


class TelegramOutboxWorker:
    def __init__(self, outbox: FlushableOutbox, interval_seconds: int | float) -> None:
        self._outbox = outbox
        self._interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop_event.set()
        await self._task
        self._task = None

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._outbox.flush_once()
            except Exception:
                pass
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._interval_seconds)
            except TimeoutError:
                pass
