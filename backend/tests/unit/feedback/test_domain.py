from uuid import UUID

import pytest

from src.feedback.domain.constants import MAX_COMMENT_LENGTH
from src.feedback.domain.entities import Feedback
from src.feedback.domain.events import FeedbackCreated
from src.feedback.domain.vo import FeedbackRating
from src.iam.domain.vo import Email


@pytest.mark.parametrize("rating", [1, 5])
def test_rating_accepts_bounds(rating: int) -> None:
    assert FeedbackRating(rating).value == rating


@pytest.mark.parametrize("rating", [0, 6])
def test_rating_rejects_values_outside_range(rating: int) -> None:
    with pytest.raises(ValueError, match="between 1 and 5"):
        FeedbackRating(rating)


def test_create_normalizes_comment_and_registers_event(user_id: UUID) -> None:
    feedback = Feedback.create(
        user_id=user_id,
        email=Email("user@example.com"),
        rating=4,
        comment="  Отлично  ",
    )

    assert feedback.comment == "Отлично"
    assert feedback.rating.value == 4
    events = list(feedback.collect_events())
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, FeedbackCreated)
    assert event.event_type == "feedback.created"
    assert event.feedback_id == feedback.id
    assert event.user_id == user_id
    assert event.email == "user@example.com"
    assert event.rating == 4
    assert event.comment == "Отлично"


@pytest.mark.parametrize("comment", ["", " \t\n"])
def test_create_rejects_empty_comment(user_id: UUID, comment: str) -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        Feedback.create(
            user_id=user_id,
            email=Email("user@example.com"),
            rating=5,
            comment=comment,
        )


def test_create_accepts_comment_at_length_limit(user_id: UUID) -> None:
    comment = "x" * MAX_COMMENT_LENGTH

    feedback = Feedback.create(
        user_id=user_id,
        email=Email("user@example.com"),
        rating=5,
        comment=comment,
    )

    assert feedback.comment == comment


def test_create_rejects_comment_over_length_limit(user_id: UUID) -> None:
    with pytest.raises(ValueError, match="2000 characters"):
        Feedback.create(
            user_id=user_id,
            email=Email("user@example.com"),
            rating=5,
            comment="x" * (MAX_COMMENT_LENGTH + 1),
        )
