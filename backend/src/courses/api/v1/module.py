import logging
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.iam.dependencies import require_permissions

from ...application.dtos import EditModuleSchema, ModuleSchema
from ...dependencies.services import ModuleServiceDep
from ...domain.entities import Module
from ...domain.permissions.courses import CREATE, DELETE, UPDATE

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/module", tags=["Module"])


@router.post(
    "/create",
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
    "/assign/{module_id}/{course_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permissions(UPDATE.code))],
)
async def assign(
    service: ModuleServiceDep,
    module_id: UUID,
    course_id: UUID,
) -> None:
    await service.assign_course(module_id=module_id, course_id=course_id)


@router.get(
    "/basic/info/{module_id}",
    status_code=status.HTTP_200_OK,
)
async def get_module_basic_info(service: ModuleServiceDep, module_id: UUID):
    return await service.get_basic_info(module_id)


@router.put(
    "/edit/{module_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permissions(UPDATE.code))],
)
async def edit_module(
    service: ModuleServiceDep,
    module_id: UUID,
    schema: EditModuleSchema,
) -> Module:
    return await service.edit(module_id=module_id, schema=schema)


@router.delete(
    "/{module_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions(DELETE.code))],
)
async def delete(
    service: ModuleServiceDep,
    module_id: UUID,
) -> None:
    return await service.delete(module_id=module_id)
