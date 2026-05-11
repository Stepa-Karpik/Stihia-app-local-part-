from enum import StrEnum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SpeechRecognizer(StrEnum):
    LOCAL_WHISPER = "local_whisper"
    QWEN_ASR = "qwen_asr"
    BROWSER = "browser"
    SILERO_VAD_ONLY = "silero_vad_only"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    site_name: str = "Стихия"
    database_url: str = "postgresql+asyncpg://stihia:stihia@postgres:5432/stihia"
    redis_url: str = "redis://redis:6379/0"
    app_secret_key: str = Field(default="change-me-local-secret", min_length=16)

    bot_server_url: str = "http://bot-server:8080"
    bot_server_token: str = "change-me-bot-token"
    telegram_queue_retry_seconds: int = 15

    speech_recognizer: SpeechRecognizer = SpeechRecognizer.LOCAL_WHISPER
    text_main_model_path: str = "models/text-main.gguf"
    text_fast_model_path: str = "models/text-fast.gguf"
    text_embed_model_path: str = "models/text-embed.gguf"
    voice_live_model_path: str = "models/voice-live.bin"
    voice_final_model_path: str = "models/voice-final.bin"
    voice_vad_model_path: str = "models/voice-vad.onnx"
    qwen_asr_model_path: str = "/models/qwen-asr"

    studio_default_background: str = "#050505"
    studio_default_text: str = "#f7f7f4"
    studio_default_font_size: int = 22

    def model_path_exists(self, value: str) -> bool:
        return Path(value).expanduser().exists()
