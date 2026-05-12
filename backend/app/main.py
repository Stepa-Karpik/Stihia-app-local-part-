from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.app_settings import router as app_settings_router
from app.api.phrases import router as phrases_router
from app.api.poems import router as poems_router
from app.api.profile import router as profile_router
from app.api.speech import router as speech_router
from app.api.system import router as system_router
from app.api.text_tools import router as text_tools_router
from app.core.settings import AppSettings
from app.db.session import create_session_factory, init_models
from app.services.app_settings_service import AppSettingsService
from app.services.phrase_service import PhraseService
from app.services.poem_service import PoemService
from app.services.profile_service import ProfileService
from app.services.speech_service import SpeechService
from app.services.text_ai_service import TextAIService
from app.services.telegram_outbox_service import TelegramOutboxService
from app.services.telegram_outbox_worker import TelegramOutboxWorker


def create_app(database_url: str | None = None, enable_background_tasks: bool = True) -> FastAPI:
    settings = AppSettings()
    session_factory = create_session_factory(database_url or settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await init_models(session_factory)
        worker: TelegramOutboxWorker | None = None
        if enable_background_tasks:
            worker = TelegramOutboxWorker(
                app.state.telegram_outbox_service,
                interval_seconds=settings.telegram_queue_retry_seconds,
            )
            worker.start()
        try:
            yield
        finally:
            if worker is not None:
                await worker.stop()

    app = FastAPI(title=settings.site_name, lifespan=lifespan)
    app.state.settings = settings
    app.state.poem_service = PoemService(session_factory)
    app.state.profile_service = ProfileService(session_factory)
    app.state.phrase_service = PhraseService(session_factory)
    app.state.app_settings_service = AppSettingsService(session_factory)
    app.state.speech_service = SpeechService(settings)
    app.state.text_ai_service = TextAIService(settings)
    app.state.telegram_outbox_service = TelegramOutboxService(
        session_factory,
        bot_server_url=settings.bot_server_url,
        bot_server_token=settings.bot_server_token,
    )
    app.include_router(poems_router)
    app.include_router(profile_router)
    app.include_router(phrases_router)
    app.include_router(app_settings_router)
    app.include_router(speech_router)
    app.include_router(text_tools_router)
    app.include_router(system_router)

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
