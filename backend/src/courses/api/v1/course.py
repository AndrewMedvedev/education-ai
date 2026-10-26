import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.courses.application.dtos import CourseBasicInfo, CourseSchema, EditCourseSchema
from src.courses.dependencies.base import CourseRepoDep
from src.courses.dependencies.services import CheckCourseAccessDep, CourseServiceDep
from src.courses.domain.entities import Course
from src.courses.domain.enums import CourseStatus
from src.courses.domain.permissions.courses import CREATE, DELETE, UPDATE
from src.iam.dependencies import require_permissions
from src.iam.dependencies.identity import CurrentIdentity
from src.shared.application.dtos import Page, Pagination

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.post(
    "",
    summary="Создать курс",
    description="Создаёт новый курс с указанными названием, описанием, уровнем сложности и тегами. Создатель курса становится его автором.",
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
    "/search",
    summary="Получить список курсов",
    description="Возвращает постраничный список курсов. Параметры пагинации передаются в теле запроса.",
    status_code=status.HTTP_200_OK,
)
async def get_course_with_pagination(
    repo: CourseRepoDep,
    pagination: Pagination,
) -> Page[Course]:
    return await repo.find(pagination)


@router.post(
    "/my-courses",
    summary="Получить мои курсы",
    description="Возвращает постраничный список курсов, в которых текущий пользователь является автором или участником.",
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
    summary="Получить статус курса",
    description="Возвращает текущий статус указанного курса для авторизованного пользователя.",
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
    "/{course_id:uuid}",
    summary="Получить информацию о курсе",
    description="Возвращает основную информацию о курсе, его модулях и уроках.",
    status_code=status.HTTP_200_OK,
)
async def get_course_basic_info(
    service: CourseServiceDep,
    course_id: UUID,
) -> CourseBasicInfo:
    return await service.get_basic_info(course_id)


@router.put(
    "/{course_id}",
    summary="Обновить курс",
    description="Обновляет переданные поля курса. Неуказанные поля остаются без изменений.",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permissions(UPDATE.code))],
)
async def edit_course(
    service: CourseServiceDep,
    course_id: UUID,
    schema: EditCourseSchema,
    check_access: CheckCourseAccessDep,
    identity: CurrentIdentity,
) -> Course:
    await check_access(
        identity=identity,
        permission=UPDATE,
        uid=course_id,
    )
    return await service.edit(course_id, schema)


@router.patch(
    "/{course_id}/status",
    summary="Опубликовать курс",
    description="Меняет статус курса на опубликованный, после чего курс становится доступен для прохождения.",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permissions(UPDATE.code))],
)
async def publish_course(
    service: CourseServiceDep,
    check_access: CheckCourseAccessDep,
    identity: CurrentIdentity,
    course_id: UUID,
) -> None:
    await check_access(
        identity=identity,
        permission=UPDATE,
        uid=course_id,
    )
    await service.change_status(course_id=course_id, status=CourseStatus.PUBLISHED)


@router.delete(
    "/{course_id}",
    summary="Архивировать курс",
    description="Переводит курс в архивный статус. Данные курса при этом сохраняются.",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions(DELETE.code))],
)
async def delete_course(
    check_access: CheckCourseAccessDep,
    identity: CurrentIdentity,
    service: CourseServiceDep,
    course_id: UUID,
) -> None:
    await check_access(
        identity=identity,
        permission=DELETE,
        uid=course_id,
    )
    await service.change_status(course_id=course_id, status=CourseStatus.ARCHIVED)


@router.post(
    "/{course_id}/invite-only",
    status_code=status.HTTP_200_OK,
)
async def invite_only_course(
    service: CourseServiceDep,
    course_id: UUID,
    check_access: CheckCourseAccessDep,
    identity: CurrentIdentity,
) -> None:
    await check_access(
        identity=identity,
        permission=UPDATE,
        uid=course_id,
    )
    await service.change_status(course_id=course_id, status=CourseStatus.INVITE_ONLY)
