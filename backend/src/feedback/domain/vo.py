from dataclasses import dataclass

from src.shared.domain.vo import ValueObject

from .constants import MAX_RATING, MIN_RATING


@dataclass(frozen=True)
class FeedbackRating(ValueObject):
    """
    Оценка качества обслуживания по отзыву.
    """

    value: int

    def __post_init__(self) -> None:
        if not MIN_RATING <= self.value <= MAX_RATING:
            raise ValueError(f"Feedback rating must be between {MIN_RATING} and {MAX_RATING}")
