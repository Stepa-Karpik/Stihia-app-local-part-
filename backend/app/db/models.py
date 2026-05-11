from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.db.types import UTCDateTime


def new_id() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class PoemRecord(Base):
    __tablename__ = "poems"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(240))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    telegram_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    versions: Mapped[list["PoemVersionRecord"]] = relationship(back_populates="poem", cascade="all, delete-orphan")
    outbox_items: Mapped[list["TelegramOutboxRecord"]] = relationship(back_populates="poem", cascade="all, delete-orphan")


class PoemVersionRecord(Base):
    __tablename__ = "poem_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    poem_id: Mapped[str] = mapped_column(ForeignKey("poems.id"))
    title: Mapped[str] = mapped_column(String(240))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    source: Mapped[str] = mapped_column(String(40))

    poem: Mapped[PoemRecord] = relationship(back_populates="versions")


class TelegramOutboxRecord(Base):
    __tablename__ = "telegram_outbox"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    poem_id: Mapped[str] = mapped_column(ForeignKey("poems.id"), unique=True)
    title: Mapped[str] = mapped_column(String(240))
    text: Mapped[str] = mapped_column(Text)
    telegram_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    poem: Mapped[PoemRecord] = relationship(back_populates="outbox_items")
