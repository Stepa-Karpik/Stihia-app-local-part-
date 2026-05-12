from fastapi import APIRouter, Request

from app.schemas import (
    AnalyzeTextRequest,
    AnalyzeTextResponse,
    CompleteRequest,
    CompleteResponse,
    DraftRequest,
    DraftResponse,
    RhymeRequest,
    RhymeResponse,
)
from app.services.text_tools import analyze_lines

router = APIRouter(prefix="/api/text-tools", tags=["text-tools"])


@router.post("/analyze", response_model=AnalyzeTextResponse)
async def analyze_text(payload: AnalyzeTextRequest) -> AnalyzeTextResponse:
    lines = analyze_lines(payload.text)
    return AnalyzeTextResponse(line_count=len(lines), lines=lines)


@router.post("/rhyme", response_model=RhymeResponse)
async def rhyme(payload: RhymeRequest, request: Request) -> RhymeResponse:
    candidates, _engine = request.app.state.text_ai_service.rhyme(payload.word, payload.context)
    return RhymeResponse(word=payload.word, candidates=candidates)


@router.post("/draft", response_model=DraftResponse)
async def draft(payload: DraftRequest, request: Request) -> DraftResponse:
    variants, _engine = request.app.state.text_ai_service.draft(payload.text, payload.mode)
    line_count = len(payload.text.splitlines() or [""])
    return DraftResponse(line_count=line_count, variants=variants)


@router.post("/complete", response_model=CompleteResponse)
async def complete(payload: CompleteRequest, request: Request) -> CompleteResponse:
    completion, engine = request.app.state.text_ai_service.complete_line(
        poem_text=payload.poem_text,
        current_line=payload.current_line,
        scope=payload.scope,
    )
    return CompleteResponse(completion=completion, line_count=1, engine=engine)
