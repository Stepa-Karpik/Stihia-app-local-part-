from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.poems import router as poems_router
from app.core.settings import AppSettings
from app.db.session import create_session_factory, init_models
from app.services.poem_service import PoemService


def create_app(database_url: str | None = None) -> FastAPI:
    settings = AppSettings()
    session_factory = create_session_factory(database_url or settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await init_models(session_factory)
        yield

    app = FastAPI(title=settings.site_name, lifespan=lifespan)
    app.state.poem_service = PoemService(session_factory)
    app.include_router(poems_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.site_name}

    @app.get("/api/settings/models")
    async def model_settings() -> dict[str, str | int]:
        return {
            "speech_recognizer": settings.speech_recognizer,
            "text_main_model_path": settings.text_main_model_path,
            "text_fast_model_path": settings.text_fast_model_path,
            "voice_live_model_path": settings.voice_live_model_path,
            "voice_final_model_path": settings.voice_final_model_path,
            "voice_vad_model_path": settings.voice_vad_model_path,
            "qwen_asr_model_path": settings.qwen_asr_model_path,
            "studio_default_background": settings.studio_default_background,
            "studio_default_text": settings.studio_default_text,
            "studio_default_font_size": settings.studio_default_font_size,
        }

    return app


app = create_app()
