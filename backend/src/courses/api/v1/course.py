import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.iam.dependencies import require_permissions
from src.iam.dependencies.identity import CurrentIdentity
from src.shared.application.dtos import Page, Pagination

from ...application.dtos import CourseSchema, EditCourseSchema
from ...dependencies.base import CourseRepoDep
from ...dependencies.services import CourseServiceDep
from ...domain.entities import Course, CourseBasicInfo
from ...domain.permissions.courses import CREATE, DELETE, UPDATE
from ...domain.vo import CourseStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/course", tags=["Courses"])


@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(CREATE.code))],
)
async def create_course(
    service: CourseServiceDep,
    identity: CurrentIdentity,
    schema: CourseSchema,
) -> Course:
    return await service.create(user_id=identity.id, schema=schema)


@router.post(
    "/",
    status_code=status.HTTP_200_OK,
)
async def get_course_with_pagination(
    repo: CourseRepoDep,
    pagination: Pagination,
) -> Page[Course]:
    return await repo.find(pagination)


@router.post(
    "/my-courses",
    status_code=status.HTTP_200_OK,
)
async def get_user_courses(
    repo: CourseRepoDep,
    identity: CurrentIdentity,
    pagination: Pagination,
) -> Page[Course]:
    return await repo.find_user_courses(identity.id, pagination)


@router.get(
    "/{course_id}/status",
    status_code=status.HTTP_200_OK,
)
async def get_status(
    course_id: UUID,
    repo: CourseRepoDep,
    identity: CurrentIdentity,
) -> dict[str, CourseStatus]:
    result = await repo.get_course_status(course_id=course_id, user_id=identity.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return {"status": result}


@router.get(
    "/basic/info/{course_id}",
    status_code=status.HTTP_200_OK,
)
async def get_course_basic_info(
    service: CourseServiceDep,
    course_id: UUID,
) -> CourseBasicInfo:
    return await service.get_basic_info(course_id)


@router.put(
    "/edit/{course_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permissions(UPDATE.code))],
)
async def edit_course(
    service: CourseServiceDep,
    course_id: UUID,
    schema: EditCourseSchema,
) -> Course:
    return await service.edit(course_id, schema)


@router.post(
    "/publish/{course_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permissions(UPDATE.code))],
)
async def publish_course(
    service: CourseServiceDep,
    course_id: UUID,
) -> None:
    await service.change_status(course_id=course_id, status=CourseStatus.PUBLISHED)


@router.delete(
    "/delete/{course_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permissions(DELETE.code))],
)
async def delete_course(
    service: CourseServiceDep,
    course_id: UUID,
) -> None:
    await service.change_status(course_id=course_id, status=CourseStatus.ARCHIVED)


@router.post(
    "/{course_id}/invite-only",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permissions(UPDATE.code))],
)
async def invite_only_course(
    service: CourseServiceDep,
    course_id: UUID,
) -> None:
    await service.change_status(course_id=course_id, status=CourseStatus.INVITE_ONLY)
