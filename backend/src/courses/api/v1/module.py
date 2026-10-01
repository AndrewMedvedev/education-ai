import logging
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.courses.application.dtos import EditModuleSchema, ModuleSchema
from src.courses.dependencies.services import CheckAccessDep, ModuleServiceDep
from src.courses.domain.entities import Module
from src.courses.domain.permissions.courses import CREATE, DELETE, READ, UPDATE
from src.iam.dependencies import CurrentIdentity, require_permissions

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
)
async def assign(
    service: ModuleServiceDep,
    check_access: CheckAccessDep,
    identity: CurrentIdentity,
    module_id: UUID,
    course_id: UUID,
) -> None:
    await check_access.course(
        identity=identity,
        permission=UPDATE,
        course_id=course_id,
    )
    await service.assign_course(module_id=module_id, course_id=course_id)


@router.get(
    "/basic/info/{module_id}",
    status_code=status.HTTP_200_OK,
)
async def get_module_basic_info(
    service: ModuleServiceDep,
    check_access: CheckAccessDep,
    identity: CurrentIdentity,
    module_id: UUID,
):
    await check_access.module(
        identity=identity,
        permission=READ,
        module_id=module_id,
    )
    return await service.get_basic_info(module_id)


@router.put(
    "/edit/{module_id}",
    status_code=status.HTTP_200_OK,
)
async def edit_module(
    check_access: CheckAccessDep,
    identity: CurrentIdentity,
    service: ModuleServiceDep,
    module_id: UUID,
    schema: EditModuleSchema,
) -> Module:
    await check_access.module(
        identity=identity,
        permission=UPDATE,
        module_id=module_id,
    )
    return await service.edit(module_id=module_id, schema=schema)


@router.delete(
    "/{module_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions(DELETE.code))],
)
async def delete(
    check_access: CheckAccessDep,
    identity: CurrentIdentity,
    service: ModuleServiceDep,
    module_id: UUID,
) -> None:
    await check_access.module(
        identity=identity,
        permission=DELETE,
        module_id=module_id,
    )
    return await service.delete(module_id=module_id)
