from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request

from app.schemas import PhraseCreateRequest, PhraseResponse

router = APIRouter(prefix="/api/phrases", tags=["phrases"])


@router.get("", response_model=list[PhraseResponse])
async def list_phrases(request: Request) -> list[PhraseResponse]:
    records = await request.app.state.phrase_service.list_phrases()
    return [PhraseResponse.from_record(record) for record in records]


@router.post("", response_model=PhraseResponse)
async def create_phrase(payload: PhraseCreateRequest, request: Request) -> PhraseResponse:
    try:
        record = await request.app.state.phrase_service.create_phrase(
            text=payload.text,
            poem_id=payload.poem_id,
            start_line=payload.start_line,
            end_line=payload.end_line,
            note=payload.note,
            now=datetime.now(UTC),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Poem not found") from exc
    return PhraseResponse.from_record(record)
