import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.courses.dependencies.base import MemberRepoDep
from src.courses.dependencies.services import MemberServiceDep
from src.courses.domain.entities import Course, Member
from src.courses.domain.permissions.courses import UPDATE
from src.iam.dependencies import require_permissions
from src.iam.dependencies.identity import CurrentIdentity
from src.shared.application.dtos import Page, Pagination

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/members", tags=["Members"])


@router.post(
    "/{course_id}/enroll",
    summary="Записаться на курс",
    description="Записывает текущего пользователя на указанный курс.",
    status_code=status.HTTP_201_CREATED,
)
async def sign_up(
    service: MemberServiceDep,
    identity: CurrentIdentity,
    course_id: UUID,
) -> Member:
    return await service.sign_course(user_id=identity.id, course_id=course_id)


@router.get(
    "",
    summary="Получить мои курсы",
    description="Возвращает постраничный список курсов, на которые записан текущий пользователь.",
    status_code=status.HTTP_200_OK,
)
async def get_courses(
    service: MemberServiceDep,
    identity: CurrentIdentity,
    pagination: Annotated[Pagination, Query()],
) -> Page[Course]:
    return await service.get_my_courses(identity.id, pagination)


@router.get(
    "/{course_id}",
    summary="Получить список студентов курса",
    description="Возвращает постраничный список пользователей, записанных на указанный курс.",
    dependencies=[Depends(require_permissions(UPDATE.code))],
    status_code=status.HTTP_200_OK,
)
async def get_course_students(
    course_id: UUID,
    repo: MemberRepoDep,
    pagination: Annotated[Pagination, Query()],
) -> Page[Member]:
    return await repo.find_by_course(course_id, pagination)
