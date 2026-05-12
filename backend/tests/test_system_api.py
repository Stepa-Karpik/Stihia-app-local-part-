from httpx import ASGITransport, AsyncClient
import pytest

from app.main import create_app


class FakeOutbox:
    async def flush_once(self):
        return type("Result", (), {"sent": 1, "failed": 0})()


@pytest.mark.asyncio
async def test_system_api_exposes_model_status_and_outbox_flush(tmp_path):
    app = create_app(database_url=f"sqlite+aiosqlite:///{tmp_path / 'system.db'}", enable_background_tasks=False)

    async with app.router.lifespan_context(app):
        app.state.telegram_outbox_service = FakeOutbox()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            models = await client.get("/api/system/models")
            assert models.status_code == 200
            assert "voice_vad" in models.json()
            assert "size_bytes" in models.json()["voice_vad"]

            flush = await client.post("/api/system/telegram-outbox/flush")
            assert flush.status_code == 200
            assert flush.json() == {"sent": 1, "failed": 0}


@pytest.mark.asyncio
async def test_api_allows_frontend_cors_preflight(tmp_path):
    app = create_app(database_url=f"sqlite+aiosqlite:///{tmp_path / 'cors.db'}", enable_background_tasks=False)

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.options(
                "/api/system/models",
                headers={
                    "Origin": "http://localhost:5173",
                    "Access-Control-Request-Method": "GET",
                },
            )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
