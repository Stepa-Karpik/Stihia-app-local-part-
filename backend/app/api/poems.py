from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, Response

from app.schemas import PoemCreateRequest, PoemResponse, PoemUpdateRequest
from app.services.poem_service import PoemService

router = APIRouter(prefix="/api/poems", tags=["poems"])


def poem_service(request: Request) -> PoemService:
    return request.app.state.poem_service


@router.get("", response_model=list[PoemResponse])
async def list_poems(request: Request) -> list[PoemResponse]:
    records = await poem_service(request).list_poems(include_deleted=False)
    return [PoemResponse.from_record(record) for record in records]


@router.get("/deleted", response_model=list[PoemResponse])
async def list_deleted_poems(request: Request) -> list[PoemResponse]:
    records = [record for record in await poem_service(request).list_poems(include_deleted=True) if record.is_deleted]
    return [PoemResponse.from_record(record) for record in records]


@router.post("", response_model=PoemResponse)
async def create_poem(payload: PoemCreateRequest, request: Request) -> PoemResponse:
    record = await poem_service(request).create_poem(payload.title, payload.text, now=datetime.now(UTC))
    return PoemResponse.from_record(record)


@router.put("/{poem_id}", response_model=PoemResponse)
async def edit_poem(poem_id: str, payload: PoemUpdateRequest, request: Request) -> PoemResponse:
    try:
        record = await poem_service(request).edit_poem(poem_id, payload.title, payload.text, now=datetime.now(UTC))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Poem not found") from exc
    return PoemResponse.from_record(record)


@router.delete("/{poem_id}", status_code=204)
async def delete_poem(poem_id: str, request: Request) -> Response:
    try:
        await poem_service(request).hide_poem(poem_id, now=datetime.now(UTC))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Poem not found") from exc
    return Response(status_code=204)
