from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ActivityLogFilters:
    actor_id: UUID | None = None
    actions: list[str] | None = None

    occurred_after: datetime | None = None
    occurred_before: datetime | None = None
