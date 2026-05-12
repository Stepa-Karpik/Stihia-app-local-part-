from datetime import datetime

from pydantic import BaseModel, Field


class PoemCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    text: str = ""


class PoemUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    text: str


class PoemResponse(BaseModel):
    id: str
    title: str
    text: str
    created_at: datetime
    updated_at: datetime
    is_deleted: bool
    is_locked: bool
    telegram_message_id: int | None

    @classmethod
    def from_record(cls, record: object) -> "PoemResponse":
        return cls(
            id=record.id,
            title=record.title,
            text=record.text,
            created_at=record.created_at,
            updated_at=record.updated_at,
            is_deleted=record.is_deleted,
            is_locked=record.is_locked,
            telegram_message_id=record.telegram_message_id,
        )


class PoemVersionResponse(BaseModel):
    id: str
    poem_id: str
    title: str
    text: str
    created_at: datetime
    source: str

    @classmethod
    def from_record(cls, record: object) -> "PoemVersionResponse":
        return cls(
            id=record.id,
            poem_id=record.poem_id,
            title=record.title,
            text=record.text,
            created_at=record.created_at,
            source=record.source,
        )


class PasswordChangeRequest(BaseModel):
    old_password: str | None = None
    new_password: str = Field(min_length=6)


class UnlockSessionRequest(BaseModel):
    password: str


class PhraseCreateRequest(BaseModel):
    text: str = Field(min_length=1)
    poem_id: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    note: str | None = None


class PhraseSourceResponse(BaseModel):
    poem_id: str
    start_line: int
    end_line: int


class PhraseResponse(BaseModel):
    id: str
    text: str
    note: str | None
    created_at: datetime
    source: PhraseSourceResponse

    @classmethod
    def from_record(cls, record: object) -> "PhraseResponse":
        return cls(
            id=record.id,
            text=record.text,
            note=record.note,
            created_at=record.created_at,
            source=PhraseSourceResponse(
                poem_id=record.poem_id,
                start_line=record.start_line,
                end_line=record.end_line,
            ),
        )


class AppSettingsRequest(BaseModel):
    studio_background: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    studio_text: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    studio_font_size: int = Field(ge=16, le=34)
    speech_recognizer: str


class AppSettingsResponse(AppSettingsRequest):
    pass


class AnalyzeTextRequest(BaseModel):
    text: str


class LineAnalysisResponse(BaseModel):
    number: int
    text: str
    syllables: int
    last_word: str | None


class AnalyzeTextResponse(BaseModel):
    line_count: int
    lines: list[LineAnalysisResponse]


class RhymeRequest(BaseModel):
    word: str
    context: str | None = None


class RhymeResponse(BaseModel):
    word: str
    candidates: list[str]


class DraftRequest(BaseModel):
    text: str
    mode: str


class DraftResponse(BaseModel):
    line_count: int
    variants: list[str]


class CompleteRequest(BaseModel):
    poem_text: str
    current_line: str
    scope: str = "general"


class CompleteResponse(BaseModel):
    completion: str
    line_count: int
    engine: str
