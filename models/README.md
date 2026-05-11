# Models

Эта папка предназначена для локальных моделей и исключена из git.

Ожидаемые имена файлов:

```text
text-main.gguf   Qwen3-8B-GGUF Q4_K_M
text-fast.gguf   Qwen3-1.7B-GGUF Q8_0
text-embed.gguf  Qwen3-Embedding-0.6B-GGUF Q8_0, опционально
voice-live.bin   Whisper large-v3-turbo q8_0 для live-диктовки
voice-final.bin  Whisper large-v3 для финальной перепроверки, опционально
voice-vad.onnx   Silero VAD для определения речи/тишины
```

Qwen ASR можно хранить вне проекта, например в `~/Qwen3-ASR-1.7B`, и прокинуть в Docker как `/models/qwen-asr`.
