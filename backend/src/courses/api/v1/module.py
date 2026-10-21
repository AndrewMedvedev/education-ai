import logging
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.courses.application.dtos import EditModuleSchema, ModuleSchema
from src.courses.dependencies.services import (
    CheckCourseAccessDep,
    CheckModuleAccessDep,
    ModuleServiceDep,
)
from src.courses.domain.entities import Module
from src.courses.domain.permissions.courses import CREATE, DELETE, READ, UPDATE
from src.iam.dependencies import CurrentIdentity, require_permissions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/modules", tags=["Modules"])


@router.post(
    "",
    summary="Создать модуль",
    description="Создаёт модуль курса. При передаче идентификатора курса сразу связывает модуль с этим курсом.",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(CREATE.code))],
)
async def create(
    service: ModuleServiceDep,
    schema: ModuleSchema,
    course_id: UUID | None = None,
) -> Module:
    return await service.create(course_id=course_id, schema=schema)


@router.post(
    "/{module_id}/courses/{course_id}",
    summary="Привязать модуль к курсу",
    description="Связывает существующий модуль с указанным курсом.",
    status_code=status.HTTP_200_OK,
)
async def assign(
    service: ModuleServiceDep,
    check_access: CheckCourseAccessDep,
    identity: CurrentIdentity,
    module_id: UUID,
    course_id: UUID,
) -> None:
    await check_access(
        identity=identity,
        permission=UPDATE,
        uid=course_id,
    )
    await service.assign_course(module_id=module_id, course_id=course_id)


@router.get(
    "/{module_id}",
    summary="Получить информацию о модуле",
    description="Возвращает основную информацию о модуле и входящих в него уроках.",
    status_code=status.HTTP_200_OK,
)
async def get_module_basic_info(
    service: ModuleServiceDep,
    check_access: CheckModuleAccessDep,
    identity: CurrentIdentity,
    module_id: UUID,
):
    await check_access(
        identity=identity,
        permission=READ,
        uid=module_id,
    )
    return await service.get_basic_info(module_id)


@router.put(
    "/{module_id}",
    summary="Обновить модуль",
    description="Обновляет переданные поля модуля. Неуказанные поля остаются без изменений.",
    status_code=status.HTTP_200_OK,
)
async def edit_module(
    check_access: CheckModuleAccessDep,
    identity: CurrentIdentity,
    service: ModuleServiceDep,
    module_id: UUID,
    schema: EditModuleSchema,
) -> Module:
    await check_access(
        identity=identity,
        permission=UPDATE,
        uid=module_id,
    )
    return await service.edit(module_id=module_id, schema=schema)


@router.delete(
    "/{module_id}",
    summary="Удалить модуль",
    description="Удаляет модуль и его связь с курсом.",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions(DELETE.code))],
)
async def delete(
    check_access: CheckModuleAccessDep,
    identity: CurrentIdentity,
    service: ModuleServiceDep,
    module_id: UUID,
) -> None:
    await check_access(
        identity=identity,
        permission=DELETE,
        uid=module_id,
    )
    return await service.delete(module_id=module_id)
