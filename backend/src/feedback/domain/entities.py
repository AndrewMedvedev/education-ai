from typing import Self

from dataclasses import dataclass
from uuid import UUID

from src.iam.domain.vo import Email
from src.shared.domain.entities import AggregateRoot

from .constants import MAX_COMMENT_LENGTH
from .events import FeedbackCreated
from .vo import FeedbackRating


@dataclass(kw_only=True)
class Feedback(AggregateRoot):
    user_id: UUID
    email: Email
    rating: FeedbackRating
    comment: str

    def __post_init__(self) -> None:
        """Проверяет и нормализует обязательный комментарий."""

        self.comment = self._validate_comment(self.comment)

    @staticmethod
    def _validate_comment(comment: str) -> str:
        cleaned = comment.strip() if comment else ""
        if not cleaned:
            raise ValueError("Feedback comment cannot be empty")
        if len(cleaned) > MAX_COMMENT_LENGTH:
            raise ValueError(f"Feedback comment cannot exceed {MAX_COMMENT_LENGTH} characters")
        return cleaned

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        email: Email,
        rating: int,
        comment: str,
    ) -> Self:
        """
        Создаёт новый отзыв клиента.
        """

        feedback = cls(
            user_id=user_id,
            email=email,
            rating=FeedbackRating(rating),
            comment=comment,
        )

        feedback.register_event(
            FeedbackCreated(
                feedback_id=feedback.id,
                user_id=feedback.user_id,
                email=feedback.email.value,
                rating=feedback.rating.value,
                comment=feedback.comment,
            )
        )

        return feedback
