from app.core.settings import AppSettings, SpeechRecognizer


def test_settings_default_to_local_whisper_pipeline():
    settings = AppSettings()

    assert settings.site_name == "Стихия"
    assert settings.speech_recognizer == SpeechRecognizer.LOCAL_WHISPER
    assert settings.voice_live_model_path.endswith("models/voice-live.bin")
    assert settings.voice_vad_model_path.endswith("models/voice-vad.onnx")


def test_settings_support_qwen_asr_path_override(monkeypatch):
    monkeypatch.setenv("SPEECH_RECOGNIZER", "qwen_asr")
    monkeypatch.setenv("QWEN_ASR_MODEL_PATH", "/home/stepka/Qwen3-ASR-1.7B")

    settings = AppSettings()

    assert settings.speech_recognizer == SpeechRecognizer.QWEN_ASR
    assert settings.qwen_asr_model_path == "/home/stepka/Qwen3-ASR-1.7B"
