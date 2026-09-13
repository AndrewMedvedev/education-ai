from typing import Any

from datetime import datetime
from enum import StrEnum, auto
from uuid import UUID

from sqlalchemy import TEXT, DateTime, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class MessageStatus(StrEnum):
    PENDING = auto()
    PROCESSED = auto()
    SENT = auto()
    FAILED = auto()
    DEAD = auto()


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    event_type: Mapped[str]
    aggregate_id: Mapped[UUID]
    aggregate_type: Mapped[str]
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    occurred_on: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    correlation_id: Mapped[UUID | None] = mapped_column(nullable=True)

    status: Mapped[MessageStatus] = mapped_column(Enum(MessageStatus))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[str | None] = mapped_column(TEXT, nullable=True)
