import asyncio

import pytest

from app.services.telegram_outbox_worker import TelegramOutboxWorker


class CountingOutbox:
    def __init__(self) -> None:
        self.calls = 0

    async def flush_once(self) -> None:
        self.calls += 1


@pytest.mark.asyncio
async def test_worker_flushes_outbox_until_stopped() -> None:
    outbox = CountingOutbox()
    worker = TelegramOutboxWorker(outbox, interval_seconds=0.01)

    worker.start()
    await asyncio.sleep(0.035)
    await worker.stop()

    assert outbox.calls >= 2
