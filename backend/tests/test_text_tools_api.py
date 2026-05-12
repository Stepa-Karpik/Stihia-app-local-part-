from httpx import ASGITransport, AsyncClient
import pytest

from app.main import create_app
from app.services.text_ai_service import TextAIService
from app.services.text_tools import analyze_lines


@pytest.mark.asyncio
async def test_text_tools_analyze_lines_and_rhyme_candidates(tmp_path, monkeypatch):
    monkeypatch.setenv("TEXT_FAST_MODEL_PATH", str(tmp_path / "missing.gguf"))
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
async def test_ai_draft_returns_no_fake_variants_when_model_unavailable(tmp_path, monkeypatch):
    monkeypatch.setenv("TEXT_FAST_MODEL_PATH", str(tmp_path / "missing.gguf"))
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
            assert draft.json()["variants"] == []


def test_ai_draft_filters_identity_and_preserves_line_count():
    generated = "1. первая строка\nвторая строка сильнее\n\n2. первая строка\nвторая строка"
    variants = TextAIService._line_locked_variants(generated, "первая строка\nвторая строка")

    assert variants == ["первая строка\nвторая строка сильнее"]


@pytest.mark.asyncio
async def test_autocomplete_returns_single_line_completion(tmp_path, monkeypatch):
    monkeypatch.setenv("TEXT_FAST_MODEL_PATH", str(tmp_path / "missing.gguf"))
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


def test_autocomplete_drops_instruction_echoes():
    completion = TextAIService._clean_single_line(
        "Ты должен продолжить строку, как если ты разговариваешь с человеком"
    )

    assert completion == ""


def test_autocomplete_drops_reasoning_tags():
    assert TextAIService._clean_single_line("<think>") == ""
    assert TextAIService._clean_single_line("<think>думаю</think>на краю") == "на краю"


def test_autocomplete_drops_overlong_prose():
    completion = TextAIService._clean_single_line(
        "это слишком длинная прозаическая фраза без точного поэтического хвоста и без нормальной формы"
    )

    assert completion == ""


def test_autocomplete_fallback_stays_silent():
    completion = TextAIService._fallback_completion("И как ясный день держит смысл на краю,")

    assert completion == ""


def test_analysis_accepts_alternating_stanza_rhythm():
    text = "\n".join(
        [
            "а а а а а а а а а а а а а край",
            "а а а а а а а а а а свет",
            "а а а а а а а а а а а а а рай",
            "а а а а а а а а а ответ",
        ]
    )

    lines = analyze_lines(text)

    assert [line.syllables for line in lines] == [14, 11, 14, 11]
    assert [line.rhythm_expected for line in lines] == [14, 11, 14, 11]
    assert all("rhythm" not in line.flags for line in lines)
    assert [line.rhyme_group for line in lines] == ["A", "B", "A", "B"]
    assert {line.rhyme_scheme for line in lines} == {"ABAB"}


def test_analysis_flags_real_break_in_alternating_stanza():
    text = "\n".join(
        [
            "а а а а а а а а а а а а а край",
            "а а а а а а а а а а свет",
            "а а а а а рай",
            "а а а а а а а а а ответ",
        ]
    )

    lines = analyze_lines(text)

    assert lines[2].rhythm_expected == 14
    assert "rhythm" in lines[2].flags


def test_analysis_marks_near_rhythm_as_soft_warning():
    text = "\n".join(
        [
            "а а а а а а а а край",
            "а а а а а а а а свет",
            "а а а а а а а а а а море",
        ]
    )

    lines = analyze_lines(text)

    assert lines[2].rhythm_expected == 10
    assert lines[2].flags == ["near_rhythm"]
