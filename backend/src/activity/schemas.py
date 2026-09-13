from typing import Any

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ActivityLogResponse(BaseModel):
    aggregate_type: str = Field(description="Тип агрегата для которого записан лог")
    aggregate_id: UUID = Field(description="Идентификатор агрегата")
    action: str = Field(description="Бизнес действие которое было над агрегатом")
    actor_id: UUID = Field(description="Субъект, который выполнил действие")
    occurred_on: datetime = Field(description="Время когда произошло действие")

    changes: dict[str, Any] = Field(description="Изменённые данные")
    meta: dict[str, Any] = Field(description="Метаданные")

    event_id: UUID | None = Field(None, description="Уникальный идентификатор ивента")
    correlation_id: UUID | None = Field(None, description="Для трассировки лога")
