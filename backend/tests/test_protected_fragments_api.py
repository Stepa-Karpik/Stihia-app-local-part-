from httpx import ASGITransport, AsyncClient
import pytest

from app.main import create_app


@pytest.mark.asyncio
async def test_poem_protected_fragments_are_persisted(tmp_path):
    app = create_app(database_url=f"sqlite+aiosqlite:///{tmp_path / 'protected.db'}", enable_background_tasks=False)

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post(
                "/api/poems",
                json={"title": "Стих", "text": "первая строка\nвторая строка"},
            )
            poem_id = created.json()["id"]

            marked = await client.post(
                f"/api/poems/{poem_id}/protected-fragments",
                json={
                    "text": "вторая строка",
                    "start_line": 2,
                    "end_line": 2,
                    "kind": "intended",
                },
            )
            assert marked.status_code == 200

            fragments = await client.get(f"/api/poems/{poem_id}/protected-fragments")
            assert fragments.status_code == 200
            assert fragments.json()[0]["text"] == "вторая строка"
            assert fragments.json()[0]["kind"] == "intended"
