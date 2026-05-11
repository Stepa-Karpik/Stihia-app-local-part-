from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.core.settings import AppSettings, SpeechRecognizer


@dataclass(frozen=True)
class SpeechResult:
    text: str
    engine: str
    warning: str | None = None


class SpeechService:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._qwen_model: object | None = None
        self._whisper_model: object | None = None

    async def transcribe(
        self,
        audio: bytes,
        filename: str,
        content_type: str | None,
        recognizer: str | None = None,
    ) -> SpeechResult:
        engine = SpeechRecognizer(recognizer or self._settings.speech_recognizer)
        if engine == SpeechRecognizer.BROWSER:
            return SpeechResult(text="", engine=engine.value, warning="Браузерный режим распознает речь на клиенте.")
        if engine == SpeechRecognizer.SILERO_VAD_ONLY:
            return SpeechResult(
                text="",
                engine=engine.value,
                warning="Silero VAD определяет наличие речи, но не превращает аудио в текст.",
            )

        suffix = Path(filename).suffix or ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_file.write(audio)
            temp_path = temp_file.name
        try:
            if engine == SpeechRecognizer.QWEN_ASR:
                return self._transcribe_qwen(temp_path)
            return self._transcribe_whisper(temp_path)
        finally:
            os.unlink(temp_path)

    def _transcribe_qwen(self, audio_path: str) -> SpeechResult:
        model_path = Path(self._settings.qwen_asr_model_path).expanduser()
        self._ensure_real_weights(model_path, "Qwen3-ASR")
        try:
            import torch
            from qwen_asr import Qwen3ASRModel
        except ImportError as exc:
            raise RuntimeError("Для Qwen ASR установи пакет: pip install -U qwen-asr torch") from exc

        if self._qwen_model is None:
            self._qwen_model = Qwen3ASRModel.from_pretrained(
                str(model_path),
                dtype=torch.float16,
                device_map="cuda:0" if torch.cuda.is_available() else "cpu",
                max_inference_batch_size=1,
                max_new_tokens=512,
            )
        results = self._qwen_model.transcribe(audio=audio_path, language="Russian")
        text = getattr(results[0], "text", "") if results else ""
        return SpeechResult(text=text.strip(), engine=SpeechRecognizer.QWEN_ASR.value)

    def _transcribe_whisper(self, audio_path: str) -> SpeechResult:
        model_path = Path(self._settings.voice_final_model_path).expanduser()
        self._ensure_real_weights(model_path, "Whisper")
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError("Для локального Whisper установи пакет: pip install -U faster-whisper") from exc

        if self._whisper_model is None:
            self._whisper_model = WhisperModel(
                str(model_path),
                device="cuda",
                compute_type="float16",
            )
        segments, _info = self._whisper_model.transcribe(
            audio_path,
            language="ru",
            beam_size=1,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        text = " ".join(segment.text.strip() for segment in segments)
        return SpeechResult(text=text.strip(), engine=SpeechRecognizer.LOCAL_WHISPER.value)

    @staticmethod
    def _ensure_real_weights(path: Path, label: str) -> None:
        if not path.exists():
            raise RuntimeError(f"{label}: путь к модели не найден: {path}")
        files = [path] if path.is_file() else list(path.glob("*.safetensors")) + list(path.glob("*.bin")) + list(path.glob("*.gguf"))
        if not files:
            raise RuntimeError(f"{label}: в папке нет файлов весов модели.")
        if all(file.stat().st_size < 1024 * 1024 for file in files):
            raise RuntimeError(f"{label}: похоже, скачались только Git LFS pointers, а не реальные веса модели.")
