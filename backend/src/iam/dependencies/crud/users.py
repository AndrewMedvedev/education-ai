from typing import Annotated, Any

from fastapi import Depends

from src.iam.application.builders import build_user_response
from src.iam.application.dtos import (
    CreateUserDTO,
    UpdateUserDTO,
    UserQueryParamFilters,
    UserResponse,
)
from src.iam.dependencies.identity import CurrentIdentity
from src.iam.dependencies.repos import UserRepositoryDep
from src.iam.domain.entities import User
from src.iam.domain.vo import FullName, Username
from src.shared.application.crud import Crud
from src.shared.application.dtos import Page
from src.shared.application.repos import get_or_raise_404
from src.shared.dependencies import PaginationDep, TransactionDep
from src.shared.domain.helpers import apply_changes

UserCrud = Crud[
    User,
    UserResponse,
    CreateUserDTO,
    UpdateUserDTO,
    None,
    None,
    None,
    None,
]


async def update_handler(user: User, dto: UpdateUserDTO, options: Any | None = None) -> User:
    full_name = FullName(dto.full_name) if dto.full_name else None
    username = Username(dto.username) if dto.username else None
    return apply_changes(user, full_name=full_name, username=username, avatar_url=dto.avatar_url)


def get_user_crud(transaction: TransactionDep, user_repository: UserRepositoryDep) -> UserCrud:
    return UserCrud(
        user_repository,  # repository
        transaction,  # transaction
        build_user_response,
        update_handler=update_handler,
    )


async def get_current_user(
    identity: CurrentIdentity,
    user_repo: UserRepositoryDep,
) -> UserResponse:
    """Зависимость для получения текущего пользователя (делает запрос в БД)."""

    user = await get_or_raise_404(user_repo.read, identity.id, User)
    return build_user_response(user)


async def get_users_list(
    pagination: PaginationDep,
    filters: Annotated[UserQueryParamFilters, Depends()],
    user_repo: UserRepositoryDep,
) -> Page[UserResponse]:
    page = await user_repo.find(pagination, filters=filters)
    return page.to_response(build_user_response)


UserCrudDep = Annotated[UserCrud, Depends(get_user_crud)]
current_user_depends = Depends(get_current_user)
users_list_depends = Depends(get_users_list)
