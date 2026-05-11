from httpx import ASGITransport, AsyncClient
import pytest

from app.main import create_app


@pytest.mark.asyncio
async def test_text_tools_analyze_lines_and_rhyme_candidates(tmp_path):
    app = create_app(database_url=f"sqlite+aiosqlite:///{tmp_path / 'tools.db'}")

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            analysis = await client.post(
                "/api/text-tools/analyze",
                json={"text": "Была агонией в смертника пистолете\nи его решением одуматься в миг"},
            )
            assert analysis.status_code == 200
            assert analysis.json()["line_count"] == 2
            assert analysis.json()["lines"][0]["syllables"] >= 1

            rhyme = await client.post("/api/text-tools/rhyme", json={"word": "миг", "context": "одуматься в миг"})
            assert rhyme.status_code == 200
            assert "стих" in rhyme.json()["candidates"]


@pytest.mark.asyncio
async def test_ai_draft_preserves_selected_line_count(tmp_path):
    app = create_app(database_url=f"sqlite+aiosqlite:///{tmp_path / 'tools.db'}")

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            draft = await client.post(
                "/api/text-tools/draft",
                json={
                    "text": "первая строка\nвторая строка\nтретья строка",
                    "mode": "recommendation",
                },
            )
            assert draft.status_code == 200
            assert draft.json()["line_count"] == 3
            assert len(draft.json()["variants"]) == 3
            assert all(len(variant.split("\n")) == 3 for variant in draft.json()["variants"])
