from typing import Any

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ActivityLogOrm(Base):
    __tablename__ = "activity_logs"

    aggregate_type: Mapped[str]
    aggregate_id: Mapped[UUID]
    action: Mapped[str]
    actor_id: Mapped[UUID]
    occurred_on: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    changes: Mapped[dict[str, Any]] = mapped_column(JSONB)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB)

    event_id: Mapped[UUID | None] = mapped_column(nullable=True)
    correlation_id: Mapped[UUID | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index(
            "ix_activity_logs_aggregate_type_id_date",
            "aggregate_type",
            "aggregate_id",
            occurred_on.desc(),
        ),
        Index("ix_activity_logs_actor_action_date", "actor_id", "action", occurred_on.desc()),
        Index("ix_activity_logs_changes_gin", "changes", postgresql_using="gin"),
        Index("ix_activity_logs_meta_gin", "meta", postgresql_using="gin"),
    )
