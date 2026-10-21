from uuid import UUID

from sqlalchemy import CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

from ...domain.constants import MAX_RATING, MIN_RATING


class FeedbackOrm(Base):
    __tablename__ = "feedbacks"

    user_id: Mapped[UUID] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(nullable=False)
    rating: Mapped[int] = mapped_column(nullable=False)
    comment: Mapped[str] = mapped_column(nullable=False)

    __table_args__ = (
        CheckConstraint(
            f"rating >= {MIN_RATING} AND rating <= {MAX_RATING}",
            name="ck_feedbacks_rating_range",
        ),
        Index("ix_feedbacks_user_created_at", "user_id", "created_at"),
    )
