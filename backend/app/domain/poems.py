from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass(frozen=True)
class PoemVersion:
    id: str
    title: str
    text: str
    created_at: datetime
    source: str


@dataclass
class Poem:
    id: str
    title: str
    text: str
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False
    deleted_at: datetime | None = None
    is_locked: bool = False
    telegram_message_id: int | None = None
    versions: list[PoemVersion] = field(default_factory=list)

    @classmethod
    def create(cls, title: str, text: str, now: datetime) -> "Poem":
        poem = cls(
            id=str(uuid4()),
            title=title,
            text=text,
            created_at=now,
            updated_at=now,
        )
        poem._append_version(now=now, source="create")
        return poem

    def edit(self, title: str, text: str, now: datetime, source: str = "manual") -> None:
        self.title = title
        self.text = text
        self.updated_at = now
        self._append_version(now=now, source=source)

    def hide(self, now: datetime) -> None:
        self.is_deleted = True
        self.deleted_at = now
        self.updated_at = now

    def restore(self, now: datetime) -> None:
        self.is_deleted = False
        self.deleted_at = None
        self.updated_at = now

    def lock(self) -> None:
        self.is_locked = True

    def unlock(self) -> None:
        self.is_locked = False

    def visible_state(self, session_unlocked: bool) -> str:
        if not self.is_locked:
            return "open"
        if session_unlocked:
            return "unlocked"
        return "locked"

    def _append_version(self, now: datetime, source: str) -> None:
        self.versions.append(
            PoemVersion(
                id=str(uuid4()),
                title=self.title,
                text=self.text,
                created_at=now,
                source=source,
            )
        )
