import logging
from uuid import UUID

from fastapi import APIRouter, status

from src.courses.application.dtos import EditLessonSchema, LessonSchema
from src.courses.dependencies.services import (
    CheckLessonAccessDep,
    CheckModuleAccessDep,
    LessonServiceDep,
)
from src.courses.domain.entities import AnyContentBlock, Lesson
from src.courses.domain.permissions.courses import DELETE, READ, UPDATE
from src.iam.dependencies import CurrentIdentity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lessons", tags=["Lessons"])


@router.post(
    "",
    summary="Создать урок",
    description="Создаёт урок. При передаче идентификатора модуля сразу связывает урок с этим модулем.",
    status_code=status.HTTP_201_CREATED,
)
async def create(
    service: LessonServiceDep,
    schema: LessonSchema,
    module_id: UUID | None = None,
) -> Lesson:
    return await service.create(module_id=module_id, schema=schema)


@router.post(
    "/{lesson_id}/modules/{module_id}",
    summary="Привязать урок к модулю",
    description="Связывает существующий урок с указанным модулем.",
    status_code=status.HTTP_200_OK,
)
async def assign(
    service: LessonServiceDep,
    check_access: CheckModuleAccessDep,
    identity: CurrentIdentity,
    module_id: UUID,
    lesson_id: UUID,
) -> None:
    await check_access(
        identity=identity,
        permission=UPDATE,
        uid=module_id,
    )
    await service.assign_module(module_id=module_id, lesson_id=lesson_id)


@router.get(
    "/{lesson_id}",
    summary="Получить информацию об уроке",
    description="Возвращает основную информацию об уроке без содержимого теоретических блоков.",
    status_code=status.HTTP_200_OK,
)
async def get_lesson_basic_info(
    check_access: CheckLessonAccessDep,
    identity: CurrentIdentity,
    service: LessonServiceDep,
    lesson_id: UUID,
):
    await check_access(
        identity=identity,
        permission=READ,
        uid=lesson_id,
    )
    return await service.get_basic_info(lesson_id)


@router.get(
    "/{lesson_id}/theory",
    summary="Получить теоретический материал урока",
    description="Возвращает блоки теоретического содержимого указанного урока.",
    status_code=status.HTTP_200_OK,
)
async def get_theory(
    check_access: CheckLessonAccessDep,
    identity: CurrentIdentity,
    service: LessonServiceDep,
    lesson_id: UUID,
):
    await check_access(
        identity=identity,
        permission=READ,
        uid=lesson_id,
    )
    return await service.read_content_blocks(lesson_id)


@router.put(
    "/{lesson_id}",
    summary="Обновить урок",
    description="Обновляет переданные поля урока. Неуказанные поля остаются без изменений.",
    status_code=status.HTTP_200_OK,
)
async def edit_lesson(
    check_access: CheckLessonAccessDep,
    identity: CurrentIdentity,
    service: LessonServiceDep,
    lesson_id: UUID,
    schema: EditLessonSchema,
) -> Lesson:
    await check_access(
        identity=identity,
        permission=UPDATE,
        uid=lesson_id,
    )
    return await service.edit(lesson_id=lesson_id, schema=schema)


@router.put(
    "/{lesson_id}/content-blocks",
    summary="Обновить блоки содержимого урока",
    description="Полностью заменяет набор блоков теоретического содержимого урока.",
    status_code=status.HTTP_200_OK,
)
async def update_lesson_content_blocks(
    check_access: CheckLessonAccessDep,
    identity: CurrentIdentity,
    service: LessonServiceDep,
    lesson_id: UUID,
    content_blocks: list[AnyContentBlock],
) -> Lesson:
    await check_access(
        identity=identity,
        permission=UPDATE,
        uid=lesson_id,
    )
    return await service.update_content_blocks(lesson_id=lesson_id, content_blocks=content_blocks)


@router.delete(
    "/{lesson_id}",
    summary="Удалить урок",
    description="Удаляет урок и связанные с ним данные.",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete(
    check_access: CheckLessonAccessDep,
    identity: CurrentIdentity,
    service: LessonServiceDep,
    lesson_id: UUID,
) -> None:
    await check_access(
        identity=identity,
        permission=DELETE,
        uid=lesson_id,
    )
    return await service.delete(lesson_id=lesson_id)
