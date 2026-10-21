from enum import StrEnum


class LLMInvocationStatus(StrEnum):
    """Статус выполнения вызова модели."""

    COMPLETED = "completed"
    FAILED = "failed"
