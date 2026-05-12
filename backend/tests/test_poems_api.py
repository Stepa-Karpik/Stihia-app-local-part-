from httpx import ASGITransport, AsyncClient
import pytest

from app.main import create_app


@pytest.mark.asyncio
async def test_poems_api_creates_edits_and_soft_deletes(tmp_path):
    app = create_app(database_url=f"sqlite+aiosqlite:///{tmp_path / 'api.db'}", enable_background_tasks=False)

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post("/api/poems", json={"title": "Первый", "text": "строка"})
            assert created.status_code == 200
            poem = created.json()

            edited = await client.put(f"/api/poems/{poem['id']}", json={"title": "Первый", "text": "новая строка"})
            assert edited.status_code == 200
            assert edited.json()["text"] == "новая строка"

            deleted = await client.delete(f"/api/poems/{poem['id']}")
            assert deleted.status_code == 204

            active_list = await client.get("/api/poems")
            deleted_list = await client.get("/api/poems/deleted")

            assert active_list.json() == []
            assert len(deleted_list.json()) == 1


@pytest.mark.asyncio
async def test_autosave_updates_text_without_version_spam(tmp_path):
    app = create_app(database_url=f"sqlite+aiosqlite:///{tmp_path / 'autosave.db'}", enable_background_tasks=False)

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post("/api/poems", json={"title": "Черновик", "text": "первая"})
            poem_id = created.json()["id"]

            autosaved = await client.put(
                f"/api/poems/{poem_id}",
                json={"title": "Черновик", "text": "первая\nвторая", "source": "autosave"},
            )
            versions = await client.get(f"/api/poems/{poem_id}/versions")

            assert autosaved.status_code == 200
            assert autosaved.json()["text"] == "первая\nвторая"
            assert len(versions.json()) == 1
