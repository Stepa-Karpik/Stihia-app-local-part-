from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

router = APIRouter(prefix="/api/speech", tags=["speech"])


@router.post("/transcribe")
async def transcribe_audio(
    request: Request,
    audio: UploadFile = File(...),
    recognizer: str | None = Form(default=None),
) -> dict[str, str | None]:
    payload = await audio.read()
    try:
        result = await request.app.state.speech_service.transcribe(
            audio=payload,
            filename=audio.filename or "voice.webm",
            content_type=audio.content_type,
            recognizer=recognizer,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"text": result.text, "engine": result.engine, "warning": result.warning}
