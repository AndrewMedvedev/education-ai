import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.courses.application.dtos import CourseSchema, EditCourseSchema
from src.courses.dependencies.base import CourseRepoDep
from src.courses.dependencies.services import CheckAccessDep, CourseServiceDep
from src.courses.domain.entities import Course, CourseBasicInfo
from src.courses.domain.permissions.courses import CREATE, DELETE, UPDATE
from src.courses.domain.vo import CourseStatus
from src.iam.dependencies import require_permissions
from src.iam.dependencies.identity import CurrentIdentity
from src.shared.application.dtos import Page, Pagination

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
)
async def edit_course(
    service: CourseServiceDep,
    course_id: UUID,
    schema: EditCourseSchema,
    check_access: CheckAccessDep,
    identity: CurrentIdentity,
) -> Course:
    await check_access.course(
        identity=identity,
        permission=UPDATE,
        course_id=course_id,
    )
    return await service.edit(course_id, schema)


@router.post(
    "/publish/{course_id}",
    status_code=status.HTTP_200_OK,
)
async def publish_course(
    service: CourseServiceDep,
    check_access: CheckAccessDep,
    identity: CurrentIdentity,
    course_id: UUID,
) -> None:
    await check_access.course(
        identity=identity,
        permission=UPDATE,
        course_id=course_id,
    )
    await service.change_status(course_id=course_id, status=CourseStatus.PUBLISHED)


@router.delete(
    "/delete/{course_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_course(
    check_access: CheckAccessDep,
    identity: CurrentIdentity,
    service: CourseServiceDep,
    course_id: UUID,
) -> None:
    await check_access.course(
        identity=identity,
        permission=DELETE,
        course_id=course_id,
    )
    await service.change_status(course_id=course_id, status=CourseStatus.ARCHIVED)


@router.post(
    "/{course_id}/invite-only",
    status_code=status.HTTP_200_OK,
)
async def invite_only_course(
    service: CourseServiceDep,
    course_id: UUID,
    check_access: CheckAccessDep,
    identity: CurrentIdentity,
) -> None:
    await check_access.course(
        identity=identity,
        permission=UPDATE,
        course_id=course_id,
    )
    await service.change_status(course_id=course_id, status=CourseStatus.INVITE_ONLY)
