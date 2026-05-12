from httpx import ASGITransport, AsyncClient
import pytest

from app.main import create_app
from app.services.text_ai_service import TextAIService


@pytest.mark.asyncio
async def test_text_tools_analyze_lines_and_rhyme_candidates(tmp_path):
    app = create_app(database_url=f"sqlite+aiosqlite:///{tmp_path / 'tools.db'}", enable_background_tasks=False)

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            analysis = await client.post(
                "/api/text-tools/analyze",
                json={"text": "Была агонией в смертника пистолете\nи его решением одуматься в миг"},
            )
            assert analysis.status_code == 200
            assert analysis.json()["line_count"] == 2
            assert analysis.json()["lines"][0]["syllables"] >= 1
            assert analysis.json()["lines"][0]["rhyme_tail"] == "ете"
            assert "rhythm_delta" in analysis.json()["lines"][0]

            rhyme = await client.post("/api/text-tools/rhyme", json={"word": "миг", "context": "одуматься в миг"})
            assert rhyme.status_code == 200
            assert "стих" in rhyme.json()["candidates"]


@pytest.mark.asyncio
async def test_ai_draft_preserves_selected_line_count(tmp_path):
    app = create_app(database_url=f"sqlite+aiosqlite:///{tmp_path / 'tools.db'}", enable_background_tasks=False)

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


@pytest.mark.asyncio
async def test_autocomplete_returns_single_line_completion(tmp_path):
    app = create_app(database_url=f"sqlite+aiosqlite:///{tmp_path / 'tools.db'}", enable_background_tasks=False)

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            completion = await client.post(
                "/api/text-tools/complete",
                json={
                    "poem_text": "Была агонией в смертника пистолете",
                    "current_line": "и его решением",
                    "scope": "general",
                },
            )

    assert completion.status_code == 200
    assert completion.json()["line_count"] == 1
    assert "\n" not in completion.json()["completion"]


def test_autocomplete_drops_repetitive_model_loops():
    completion = TextAIService._clean_single_line(", и жду, и жду, и жду, и жду")

    assert completion == ""
