from typing import ClassVar

from dataclasses import dataclass
from uuid import UUID

from src.shared.domain.events import Event


@dataclass(frozen=True, kw_only=True)
class FeedbackCreated(Event):
    event_type: ClassVar[str] = "feedback.created"
    """Пользователь оставил отзыв."""

    feedback_id: UUID
    user_id: UUID
    email: str
    rating: int
    comment: str | None = None
