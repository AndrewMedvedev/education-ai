from typing import Any, ClassVar

from dataclasses import dataclass
from uuid import UUID

from src.shared.domain.events import Event

from .vo import LLMInvocationStatus


@dataclass(frozen=True, kw_only=True)
class LLMInvocationCreated(Event):
    """Содержит данные вызова модели для асинхронного сохранения."""

    event_type: ClassVar[str] = "llm_router.invocation.created"

    request_id: UUID
    model: str
    total_tokens: int
    request: dict[str, Any]
    response: dict[str, Any]
    duration_ms: int
    status: LLMInvocationStatus
    error: str | None = None
