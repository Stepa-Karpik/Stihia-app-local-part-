from dataclasses import dataclass

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import PoemRecord, TelegramOutboxRecord


@dataclass(frozen=True)
class FlushResult:
    sent: int
    failed: int


class TelegramOutboxService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        bot_server_url: str,
        bot_server_token: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._bot_server_url = bot_server_url.rstrip("/")
        self._bot_server_token = bot_server_token
        self._http_client = http_client or httpx.AsyncClient(timeout=10, trust_env=False)

    async def flush_once(self) -> FlushResult:
        sent = 0
        failed = 0
        async with self._session_factory() as session:
            result = await session.execute(select(TelegramOutboxRecord).order_by(TelegramOutboxRecord.updated_at.asc()))
            items = list(result.scalars())
            for item in items:
                try:
                    response = await self._http_client.post(
                        f"{self._bot_server_url}/v1/telegram/sync",
                        headers={"x-stihia-token": self._bot_server_token},
                        json={
                            "poem_id": item.poem_id,
                            "title": item.title,
                            "text": item.text,
                            "telegram_message_id": item.telegram_message_id,
                        },
                    )
                    response.raise_for_status()
                    body = response.json()
                    poem = await session.get(PoemRecord, item.poem_id)
                    if poem is not None:
                        poem.telegram_message_id = int(body["telegram_message_id"])
                    await session.execute(delete(TelegramOutboxRecord).where(TelegramOutboxRecord.id == item.id))
                    sent += 1
                except (httpx.HTTPError, RuntimeError, KeyError, ValueError) as exc:
                    item.attempts += 1
                    item.last_error = str(exc)
                    failed += 1
            await session.commit()
        return FlushResult(sent=sent, failed=failed)
