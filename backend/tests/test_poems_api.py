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


@pytest.mark.asyncio
async def test_manual_save_without_changes_does_not_create_version_or_touch_timestamp(tmp_path):
    app = create_app(database_url=f"sqlite+aiosqlite:///{tmp_path / 'unchanged.db'}", enable_background_tasks=False)

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post("/api/poems", json={"title": "Стих", "text": "строка"})
            poem = created.json()

            unchanged = await client.put(f"/api/poems/{poem['id']}", json={"title": "Стих", "text": "строка"})
            versions = await client.get(f"/api/poems/{poem['id']}/versions")

            assert unchanged.status_code == 200
            assert unchanged.json()["updated_at"] == poem["updated_at"]
            assert len(versions.json()) == 1


@pytest.mark.asyncio
async def test_empty_untouched_poems_are_hidden_from_active_list(tmp_path):
    app = create_app(database_url=f"sqlite+aiosqlite:///{tmp_path / 'empty.db'}", enable_background_tasks=False)

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            empty = await client.post("/api/poems", json={"title": "Новый стих", "text": ""})
            real = await client.post("/api/poems", json={"title": "Стих", "text": "строка"})

            active = await client.get("/api/poems")

            assert empty.status_code == 200
            assert real.status_code == 200
            assert [poem["id"] for poem in active.json()] == [real.json()["id"]]


@pytest.mark.asyncio
async def test_signature_phrase_archive_is_populated_from_poem_text(tmp_path):
    app = create_app(database_url=f"sqlite+aiosqlite:///{tmp_path / 'phrases-auto.db'}", enable_background_tasks=False)

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post(
                "/api/poems",
                json={
                    "title": "Стих",
                    "text": "Быть агонией в смертника пистолете,\nИ его решением одуматься в миг.",
                },
            )

            archive = await client.get("/api/phrases")

            assert created.status_code == 200
            assert archive.status_code == 200
            assert archive.json()[0]["text"] == "агонией в смертника пистолете"
            assert archive.json()[0]["source"]["start_line"] == 1
