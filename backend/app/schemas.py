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
