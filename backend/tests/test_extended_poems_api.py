from httpx import ASGITransport, AsyncClient
import pytest

from app.main import create_app


@pytest.mark.asyncio
async def test_restore_versions_export_lock_and_password_flow(tmp_path):
    app = create_app(database_url=f"sqlite+aiosqlite:///{tmp_path / 'extended.db'}", enable_background_tasks=False)

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post("/api/poems", json={"title": "Стих", "text": "первая строка"})
            poem_id = created.json()["id"]
            await client.put(f"/api/poems/{poem_id}", json={"title": "Стих", "text": "первая строка\nвторая строка"})

            versions = await client.get(f"/api/poems/{poem_id}/versions")
            assert versions.status_code == 200
            assert len(versions.json()) == 2

            exported = await client.get(f"/api/poems/{poem_id}/export.md")
            assert exported.status_code == 200
            assert exported.text.startswith("# Стих")
            assert "вторая строка" in exported.text

            await client.post("/api/profile/password", json={"old_password": None, "new_password": "secret-1"})
            wrong_change = await client.post(
                "/api/profile/password",
                json={"old_password": "bad", "new_password": "secret-2"},
            )
            assert wrong_change.status_code == 403

            locked = await client.post(f"/api/poems/{poem_id}/lock")
            assert locked.status_code == 200
            assert locked.json()["is_locked"] is True

            unlock = await client.post("/api/profile/unlock-session", json={"password": "secret-1"})
            assert unlock.status_code == 200
            assert unlock.json() == {"session_unlocked": True}

            await client.delete(f"/api/poems/{poem_id}")
            assert (await client.get("/api/poems")).json() == []
            restored = await client.post(f"/api/poems/{poem_id}/restore")
            assert restored.status_code == 200
            assert restored.json()["is_deleted"] is False


@pytest.mark.asyncio
async def test_phrase_archive_keeps_source_pointer(tmp_path):
    app = create_app(database_url=f"sqlite+aiosqlite:///{tmp_path / 'phrases.db'}", enable_background_tasks=False)

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post(
                "/api/poems",
                json={"title": "Стих", "text": "Была агонией в смертника пистолете\nи его решением"},
            )
            poem_id = created.json()["id"]
            fetched = await client.get(f"/api/poems/{poem_id}")
            assert fetched.status_code == 200
            assert fetched.json()["id"] == poem_id

            phrase = await client.post(
                "/api/phrases",
                json={
                    "text": "агонией в смертника пистолете",
                    "poem_id": poem_id,
                    "start_line": 1,
                    "end_line": 1,
                    "note": "сложная метафора",
                },
            )

            assert phrase.status_code == 200
            archive = (await client.get("/api/phrases")).json()
            assert archive[0]["text"] == "агонией в смертника пистолете"
            assert archive[0]["source"]["poem_id"] == poem_id
            assert archive[0]["source"]["start_line"] == 1


@pytest.mark.asyncio
async def test_app_settings_persist_editor_preferences(tmp_path):
    app = create_app(database_url=f"sqlite+aiosqlite:///{tmp_path / 'settings.db'}", enable_background_tasks=False)

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            updated = await client.put(
                "/api/app-settings",
                json={
                    "studio_background": "#000000",
                    "studio_text": "#ffffff",
                    "studio_font_size": 24,
                    "speech_recognizer": "qwen_asr",
                },
            )
            assert updated.status_code == 200

            settings = (await client.get("/api/app-settings")).json()
            assert settings["studio_font_size"] == 24
            assert settings["speech_recognizer"] == "qwen_asr"
