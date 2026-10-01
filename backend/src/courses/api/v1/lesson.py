import logging
from uuid import UUID

from fastapi import APIRouter, status

from src.courses.application.dtos import EditLessonSchema, LessonSchema
from src.courses.dependencies.services import CheckAccessDep, LessonServiceDep
from src.courses.domain.entities import AnyContentBlock, Lesson
from src.courses.domain.permissions.courses import DELETE, READ, UPDATE
from src.iam.dependencies import CurrentIdentity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lesson", tags=["Lesson"])


@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
)
async def create(
    service: LessonServiceDep,
    schema: LessonSchema,
    module_id: UUID | None = None,
) -> Lesson:
    return await service.create(module_id=module_id, schema=schema)


@router.post(
    "/assign/{lesson_id}/{module_id}",
    status_code=status.HTTP_200_OK,
)
async def assign(
    service: LessonServiceDep,
    check_access: CheckAccessDep,
    identity: CurrentIdentity,
    module_id: UUID,
    lesson_id: UUID,
) -> None:
    await check_access.module(
        identity=identity,
        permission=UPDATE,
        module_id=module_id,
    )
    await service.assign_module(module_id=module_id, lesson_id=lesson_id)


@router.get(
    "/basic/info/{lesson_id}",
    status_code=status.HTTP_200_OK,
)
async def get_lesson_basic_info(
    check_access: CheckAccessDep,
    identity: CurrentIdentity,
    service: LessonServiceDep,
    lesson_id: UUID,
):
    await check_access.lesson(
        identity=identity,
        permission=READ,
        lesson_id=lesson_id,
    )
    return await service.get_basic_info(lesson_id)


@router.get(
    "/theory/{lesson_id}",
    status_code=status.HTTP_200_OK,
)
async def get_theory(
    check_access: CheckAccessDep,
    identity: CurrentIdentity,
    service: LessonServiceDep,
    lesson_id: UUID,
):
    await check_access.lesson(
        identity=identity,
        permission=READ,
        lesson_id=lesson_id,
    )
    return await service.read_content_blocks(lesson_id)


@router.put(
    "/edit/{lesson_id}",
    status_code=status.HTTP_200_OK,
)
async def edit_lesson(
    check_access: CheckAccessDep,
    identity: CurrentIdentity,
    service: LessonServiceDep,
    lesson_id: UUID,
    schema: EditLessonSchema,
) -> Lesson:
    await check_access.lesson(
        identity=identity,
        permission=UPDATE,
        lesson_id=lesson_id,
    )
    return await service.edit(lesson_id=lesson_id, schema=schema)


@router.put(
    "/update/{lesson_id}",
    status_code=status.HTTP_200_OK,
)
async def update_lesson_content_blocks(
    check_access: CheckAccessDep,
    identity: CurrentIdentity,
    service: LessonServiceDep,
    lesson_id: UUID,
    content_blocks: list[AnyContentBlock],
) -> Lesson:
    await check_access.lesson(
        identity=identity,
        permission=UPDATE,
        lesson_id=lesson_id,
    )
    return await service.update_content_blocks(lesson_id=lesson_id, content_blocks=content_blocks)


@router.delete(
    "/{lesson_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete(
    check_access: CheckAccessDep,
    identity: CurrentIdentity,
    service: LessonServiceDep,
    lesson_id: UUID,
) -> None:
    await check_access.lesson(
        identity=identity,
        permission=DELETE,
        lesson_id=lesson_id,
    )
    return await service.delete(lesson_id=lesson_id)
