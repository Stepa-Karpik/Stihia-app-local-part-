from fastapi import APIRouter

from app.schemas import (
    AnalyzeTextRequest,
    AnalyzeTextResponse,
    DraftRequest,
    DraftResponse,
    RhymeRequest,
    RhymeResponse,
)
from app.services.text_tools import analyze_lines, draft_variants, rhyme_candidates

router = APIRouter(prefix="/api/text-tools", tags=["text-tools"])


@router.post("/analyze", response_model=AnalyzeTextResponse)
async def analyze_text(payload: AnalyzeTextRequest) -> AnalyzeTextResponse:
    lines = analyze_lines(payload.text)
    return AnalyzeTextResponse(line_count=len(lines), lines=lines)


@router.post("/rhyme", response_model=RhymeResponse)
async def rhyme(payload: RhymeRequest) -> RhymeResponse:
    return RhymeResponse(word=payload.word, candidates=rhyme_candidates(payload.word))


@router.post("/draft", response_model=DraftResponse)
async def draft(payload: DraftRequest) -> DraftResponse:
    variants = draft_variants(payload.text, payload.mode)
    line_count = len(payload.text.splitlines() or [""])
    return DraftResponse(line_count=line_count, variants=variants)
