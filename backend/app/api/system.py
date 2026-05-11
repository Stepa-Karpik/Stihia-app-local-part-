from pathlib import Path

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/models")
async def model_status(request: Request) -> dict[str, dict[str, str | bool]]:
    settings = request.app.state.settings
    paths = {
        "text_main": settings.text_main_model_path,
        "text_fast": settings.text_fast_model_path,
        "text_embed": settings.text_embed_model_path,
        "voice_live": settings.voice_live_model_path,
        "voice_final": settings.voice_final_model_path,
        "voice_vad": settings.voice_vad_model_path,
        "qwen_asr": settings.qwen_asr_model_path,
    }
    return {
        name: {
            "path": path,
            "exists": Path(path).expanduser().exists(),
        }
        for name, path in paths.items()
    }


@router.post("/telegram-outbox/flush")
async def flush_telegram_outbox(request: Request) -> dict[str, int]:
    result = await request.app.state.telegram_outbox_service.flush_once()
    return {"sent": result.sent, "failed": result.failed}
