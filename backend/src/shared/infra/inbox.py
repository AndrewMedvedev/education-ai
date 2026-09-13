from typing import Any

from datetime import datetime
from enum import StrEnum

from sqlalchemy import TEXT, DateTime, Enum, UniqueConstraint, select, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

from ..utils.time import current_datetime


class MessageStatus(StrEnum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class InboxMessage(Base):
    __tablename__ = "inbox_messages"

    message_id: Mapped[str]
    event_type: Mapped[str]
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[MessageStatus] = mapped_column(Enum(MessageStatus))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(TEXT, nullable=True)

    __table_args__ = (
        UniqueConstraint("message_id", "event_type", name="uq_inbox_message_id_event"),
    )


class InboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, message_id: str, event_type: str, payload: dict[str, Any]) -> bool:
        """
        Попытка вставить сообщение. Возвращает True, если вставка прошла успешно.
        """

        stmt = (
            pg_insert(InboxMessage)
            .values(
                message_id=message_id,
                event_type=event_type,
                payload=payload,
                status=MessageStatus.PENDING,
            )
            .on_conflict_do_nothing()
        )
        result = await self.session.execute(stmt)

        return result.rowcount > 0

    async def get_pending(self, limit: int = 100) -> list[InboxMessage]:
        """
        Получает порцию pending-сообщений с блокировкой
        """

        stmt = (
            select(InboxMessage)
            .where(InboxMessage.status == MessageStatus.PENDING)
            .order_by(InboxMessage.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(stmt)

        return list(result.scalars().all())

    async def mark_processed(self, message_id: str, event_type: str) -> None:
        """
        Пометить inbox-сообщение как успешно обработанное.
        """

        stmt = (
            update(InboxMessage)
            .where(
                InboxMessage.message_id == message_id,
                InboxMessage.event_type == event_type,
            )
            .values(
                status=MessageStatus.PROCESSED,
                processed_at=current_datetime(),
                error_message=None,
            )
        )

        await self.session.execute(stmt)

    async def mark_failed(self, message_id: str, event_type: str, error_message: str) -> None:
        """
        Пометить inbox-сообщение как обработанное с ошибкой
        """

        stmt = (
            update(InboxMessage)
            .where(
                InboxMessage.message_id == message_id,
                InboxMessage.event_type == event_type,
            )
            .values(
                status=MessageStatus.FAILED,
                processed_at=current_datetime(),
                error_message=error_message,
            )
        )

        await self.session.execute(stmt)
