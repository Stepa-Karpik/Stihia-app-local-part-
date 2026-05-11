from datetime import UTC, datetime
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request, Response

from app.schemas import PoemCreateRequest, PoemResponse, PoemUpdateRequest, PoemVersionResponse
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


@router.get("/{poem_id}/versions", response_model=list[PoemVersionResponse])
async def list_versions(poem_id: str, request: Request) -> list[PoemVersionResponse]:
    records = await poem_service(request).list_versions(poem_id)
    return [PoemVersionResponse.from_record(record) for record in records]


@router.get("/{poem_id}/export.md", response_class=Response)
async def export_markdown(poem_id: str, request: Request) -> Response:
    try:
        record = await poem_service(request).get_poem(poem_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Poem not found") from exc
    markdown = f"# {record.title}\n\n{record.text}\n"
    encoded_filename = quote(f"{record.title}.md")
    return Response(
        content=markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=stihia.md; filename*=UTF-8''{encoded_filename}"},
    )


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


@router.post("/{poem_id}/restore", response_model=PoemResponse)
async def restore_poem(poem_id: str, request: Request) -> PoemResponse:
    try:
        record = await poem_service(request).restore_poem(poem_id, now=datetime.now(UTC))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Poem not found") from exc
    return PoemResponse.from_record(record)


@router.post("/{poem_id}/lock", response_model=PoemResponse)
async def lock_poem(poem_id: str, request: Request) -> PoemResponse:
    try:
        record = await poem_service(request).lock_poem(poem_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Poem not found") from exc
    return PoemResponse.from_record(record)
