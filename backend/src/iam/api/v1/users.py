from uuid import UUID

from fastapi import APIRouter, status

from src.iam.application.dtos import UpdateUserDTO, UserResponse
from src.iam.dependencies import CurrentIdentity, require_authentication
from src.iam.dependencies.crud import UserCrudDep, current_user_depends, users_list_depends
from src.shared.application.dtos import Page

router = APIRouter(prefix="/users", tags=["Пользователи | Users"])


@router.get(
    path="/me",
    status_code=status.HTTP_200_OK,
    summary="Получить текущего пользователя",
)
async def get_me(user: UserResponse = current_user_depends) -> UserResponse:
    return user


@router.patch(
    path="/me", status_code=status.HTTP_200_OK, summary="Обновить данные текущего пользователя."
)
async def update_me(
    identity: CurrentIdentity,
    dto: UpdateUserDTO,
    crud: UserCrudDep,
) -> UserResponse:
    return await crud.update(identity.id, dto)


@router.post(
    path="/search",
    status_code=status.HTTP_200_OK,
    dependencies=[require_authentication],
    summary="Найти пользователей",
)
async def search_users(users: Page[UserResponse] = users_list_depends) -> Page[UserResponse]:
    return users


@router.get(
    path="/{user_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[require_authentication],
    summary="Получить конкретного пользователя",
)
async def get_user(user_id: UUID, crud: UserCrudDep) -> UserResponse:
    return await crud.read(user_id)
