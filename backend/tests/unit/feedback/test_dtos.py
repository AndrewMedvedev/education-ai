import pytest
from pydantic import ValidationError

from src.feedback.application.dtos import FeedbackCreate, FeedbackFilters


def test_create_schema_accepts_only_rating_and_comment() -> None:
    request = FeedbackCreate(rating=5, comment="Спасибо")

    assert request.model_dump() == {"rating": 5, "comment": "Спасибо"}


@pytest.mark.parametrize("extra_field", ["user_id", "email"])
def test_create_schema_rejects_identity_fields(extra_field: str) -> None:
    with pytest.raises(ValidationError):
        FeedbackCreate.model_validate(
            {"rating": 5, "comment": "Спасибо", extra_field: "client-value"}
        )


@pytest.mark.parametrize("rating", [0, 6])
def test_create_schema_rejects_rating_outside_range(rating: int) -> None:
    with pytest.raises(ValidationError):
        FeedbackCreate(rating=rating, comment="Спасибо")


def test_create_schema_requires_comment() -> None:
    with pytest.raises(ValidationError):
        FeedbackCreate.model_validate({"rating": 5})


def test_feedback_filters_default_to_newest_first() -> None:
    filters = FeedbackFilters()

    assert "user_id" not in FeedbackFilters.model_fields
    assert filters.rating is None
    assert filters.sort == "created_at:desc"


@pytest.mark.parametrize("sort", ["created_at:asc", "created_at:desc"])
def test_feedback_filters_accept_date_order(sort: str) -> None:
    assert FeedbackFilters(rating=4, sort=sort).sort == sort


@pytest.mark.parametrize("sort", ["rating:asc", "created_at:random"])
def test_feedback_filters_reject_other_order(sort: str) -> None:
    with pytest.raises(ValidationError):
        FeedbackFilters(sort=sort)
