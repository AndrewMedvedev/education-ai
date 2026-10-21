from typing import Literal

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.shared.application.dtos import BaseQueryParamFilters

from ..domain.constants import MAX_RATING, MIN_RATING


class FeedbackCreate(BaseModel):
    """Данные отзыва, которые отправляет пользователь."""

    model_config = ConfigDict(extra="forbid")

    rating: int = Field(ge=MIN_RATING, le=MAX_RATING)
    comment: str


class FeedbackFilters(BaseQueryParamFilters):
    """Фильтры отзывов."""

    rating: int | None = Field(default=None, ge=MIN_RATING, le=MAX_RATING)
    created_after: datetime | None = None
    created_before: datetime | None = None
    sort: Literal["created_at:asc", "created_at:desc"] = "created_at:desc"
