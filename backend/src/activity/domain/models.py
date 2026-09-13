from typing import Any

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.shared.utils.time import current_datetime


@dataclass(frozen=True)
class ActivityLog:
    """
    Запись завершённого бизнес действия (факт).
    """

    aggregate_type: str
    aggregate_id: UUID
    action: str
    actor_id: UUID
    occurred_on: datetime = field(default_factory=current_datetime)

    changes: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)

    event_id: UUID | None = None
    correlation_id: UUID | None = None
