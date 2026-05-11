import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.mark.asyncio
async def test_speech_api_transcribes_uploaded_audio_with_selected_engine(tmp_path) -> None:
    app = create_app(database_url=f"sqlite+aiosqlite:///{tmp_path / 'speech.db'}", enable_background_tasks=False)

    class FakeSpeechService:
        async def transcribe(self, audio: bytes, filename: str, content_type: str | None, recognizer: str | None):
            assert audio == b"audio-bytes"
            assert filename == "voice.webm"
            assert content_type == "audio/webm"
            assert recognizer == "qwen_asr"
            return type(
                "Result",
                (),
                {"text": "строка из голоса", "engine": "qwen_asr", "warning": None},
            )()

    async with app.router.lifespan_context(app):
        app.state.speech_service = FakeSpeechService()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/speech/transcribe",
                data={"recognizer": "qwen_asr"},
                files={"audio": ("voice.webm", b"audio-bytes", "audio/webm")},
            )

    assert response.status_code == 200
    assert response.json() == {"text": "строка из голоса", "engine": "qwen_asr", "warning": None}
