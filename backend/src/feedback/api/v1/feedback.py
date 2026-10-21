from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.feedback.application.dtos import FeedbackCreate, FeedbackFilters
from src.feedback.dependencies.base import FeedbackRepoDep
from src.feedback.dependencies.services import FeedbackServiceDep
from src.feedback.domain.entities import Feedback
from src.feedback.domain.permissions.feedback import READ
from src.iam.dependencies import CurrentIdentity, require_permissions
from src.shared.application.dtos import Page
from src.shared.dependencies import PaginationDep

router = APIRouter(prefix="/feedbacks", tags=["Отзывы"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=Feedback,
)
async def create_feedback(
    data: FeedbackCreate,
    identity: CurrentIdentity,
    service: FeedbackServiceDep,
) -> Feedback:
    return await service.create_feedback(
        user_id=identity.id,
        email=identity.email,  # pyright: ignore[reportArgumentType]
        rating=data.rating,
        comment=data.comment,
    )


@router.get(
    "",
    response_model=Page[Feedback],
    dependencies=[Depends(require_permissions(READ.code))],
)
async def get_feedbacks(
    repo: FeedbackRepoDep,
    pagination: PaginationDep,
    filters: Annotated[FeedbackFilters, Query()],
) -> Page[Feedback]:
    """Возвращает администратору страницу отзывов."""
    return await repo.find(pagination, filters)
