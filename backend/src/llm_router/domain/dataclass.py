from typing import Any

from dataclasses import dataclass
from uuid import UUID

from src.shared.domain.entities import Entity

from .enums import Complexity
from .vo import LLMInvocationStatus


@dataclass(kw_only=True)
class AIModel(Entity):
    name: str
    description: str
    complexity: Complexity
    context: int


@dataclass(kw_only=True)
class LLMInvocation(Entity):
    """Описывает один фактический вызов модели для мониторинга."""

    request_id: UUID
    model: str
    total_tokens: int = 0
    request: dict[str, Any]
    response: dict[str, Any]
    duration_ms: int = 0
    status: LLMInvocationStatus
    error: str | None = None
