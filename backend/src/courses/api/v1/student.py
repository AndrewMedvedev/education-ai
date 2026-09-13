import logging
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.iam.dependencies import require_permissions
from src.iam.dependencies.identity import CurrentIdentity
from src.shared.application.dtos import Page, Pagination

from ...dependencies.base import StudentRepoDep
from ...dependencies.services import StudentServiceDep
from ...domain.entities import Course, Student
from ...domain.permissions.courses import UPDATE

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/student", tags=["Student"])


@router.post(
    "/{course_id}/sign",
    status_code=status.HTTP_201_CREATED,
)
async def sign_up(
    service: StudentServiceDep,
    identity: CurrentIdentity,
    course_id: UUID,
) -> Student:
    return await service.sign_course(user_id=identity.id, course_id=course_id)


@router.post(
    "/",
    status_code=status.HTTP_200_OK,
)
async def get_courses(
    service: StudentServiceDep,
    identity: CurrentIdentity,
    pagination: Pagination,
) -> Page[Course]:
    return await service.get_my_courses(identity.id, pagination)


@router.post(
    "/{course_id}",
    dependencies=[Depends(require_permissions(UPDATE.code))],
    status_code=status.HTTP_200_OK,
)
async def get_course_students(
    course_id: UUID,
    repo: StudentRepoDep,
    pagination: Pagination,
) -> Page[Student]:
    return await repo.find_by_course(course_id, pagination)
