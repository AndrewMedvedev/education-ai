from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import EmailStr

from src.iam.application.builders import build_user_response
from src.iam.application.dtos import UpdateUserDTO, UserResponse
from src.iam.dependencies import CurrentIdentity, require_authentication
from src.iam.dependencies.crud import UserCrudDep, current_user_depends, users_list_depends
from src.iam.dependencies.repos import UserRepositoryDep
from src.iam.domain.vo import Email
from src.shared.application.dtos import Page

router = APIRouter(prefix="/users", tags=["Пользователи | Users"])


@router.get(
    path="/me",
    status_code=status.HTTP_200_OK,
    summary="Получить текущего пользователя",
    description="Возвращает профиль пользователя, от имени которого выполнен запрос.",
)
async def get_me(user: UserResponse = current_user_depends) -> UserResponse:
    return user


@router.patch(
    path="/me",
    status_code=status.HTTP_200_OK,
    summary="Обновить данные текущего пользователя.",
    description="Обновляет переданные поля профиля текущего пользователя.",
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
    description="Возвращает постраничный список пользователей по заданным параметрам поиска.",
)
async def search_users(users: Page[UserResponse] = users_list_depends) -> Page[UserResponse]:
    return users


@router.get(
    path="/{user_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[require_authentication],
    summary="Получить конкретного пользователя",
    description="Возвращает профиль пользователя по его идентификатору.",
)
async def get_user_by_id(user_id: UUID, crud: UserCrudDep) -> UserResponse:
    return await crud.read(user_id)


@router.get(
    path="/by-email/{email}",
    status_code=status.HTTP_200_OK,
    dependencies=[require_authentication],
    summary="Получить конкретного пользователя по email",
)
async def read_user_by_email(email: EmailStr, repo: UserRepositoryDep) -> UserResponse:
    user = await repo.get_by_email(Email(str(email)))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return build_user_response(user)
