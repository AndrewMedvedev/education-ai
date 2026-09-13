from typing import Annotated, Any

from fastapi import Depends

from src.iam.application.dtos import CreateRoleDTO, Identity, RoleResponse, UpdateRoleDTO
from src.iam.dependencies.repos import RoleRepositoryDep
from src.iam.domain.entities import Role
from src.shared.application.crud import Crud
from src.shared.dependencies import TransactionDep

RoleCrud = Crud[
    Role,
    RoleResponse,
    CreateRoleDTO,
    UpdateRoleDTO,
    Identity, None, None, None,
]


async def create_handler(dto: CreateRoleDTO, identity: Identity) -> Role:
    return Role(
        name=dto.name,
        code=dto.code,
        description=dto.description,
        permissions=dto.permissions,
        author_id=identity.id,
        organization_id=identity.organization_id,
    )


async def update_handler(role: Role, dto: UpdateRoleDTO, options: Any | None = None) -> Role:
    return role.update(name=dto.name, code=dto.code, description=dto.description)


async def delete_handler(role: Role, options: Any | None = None) -> Role:
    return role.remove()


def get_role_crud(transaction: TransactionDep, role_repository: RoleRepositoryDep) -> RoleCrud:
    return RoleCrud(
        role_repository,
        transaction,
        RoleResponse.model_validate,
        create_handler=create_handler,
        update_handler=update_handler,
        delete_handler=delete_handler,
    )


RoleCrudDep = Annotated[RoleCrud, Depends(get_role_crud)]
