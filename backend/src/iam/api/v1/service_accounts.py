from uuid import UUID

from fastapi import APIRouter, status

from src.iam.application.dtos import (
    ClientCredentials,
    CreateServiceAccountDTO,
    ServiceAccountResponse,
    UpdateServiceAccountDTO,
)
from src.iam.dependencies.crud import ServiceAccountCrudDep, service_accounts_list_depends
from src.iam.dependencies.services import ClientCredentialsServiceDep
from src.shared.application.dtos import Page

router = APIRouter(prefix="/service-accounts", tags=["Сервисные аккаунты | Service accounts"])


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    summary="Создать сервисный аккаунт",
    description="Создаёт сервисный аккаунт и возвращает учётные данные для машинного доступа к API.",
)
async def create_service_account(
    dto: CreateServiceAccountDTO,
    service: ClientCredentialsServiceDep,
) -> ClientCredentials:
    return await service.create(dto)


@router.post(
    path="/search",
    status_code=status.HTTP_200_OK,
    summary="Найти сервисные аккаунты",
    description="Возвращает постраничный список сервисных аккаунтов по заданным параметрам поиска.",
)
async def search_service_accounts(
    service_accounts: Page[ServiceAccountResponse] = service_accounts_list_depends,
) -> Page[ServiceAccountResponse]:
    return service_accounts


@router.get(
    path="/{service_account_id}",
    status_code=status.HTTP_200_OK,
    summary="Получить сервисный аккаунт",
    description="Возвращает данные сервисного аккаунта по его идентификатору.",
)
async def get_service_account(
    service_account_id: UUID,
    crud: ServiceAccountCrudDep,
) -> ServiceAccountResponse:
    return await crud.read(service_account_id)


@router.patch(
    path="/{service_account_id}",
    status_code=status.HTTP_200_OK,
    summary="Обновить сервисный аккаунт",
    description="Обновляет переданные данные сервисного аккаунта.",
)
async def update_service_account(
    service_account_id: UUID,
    dto: UpdateServiceAccountDTO,
    crud: ServiceAccountCrudDep,
) -> ServiceAccountResponse:
    return await crud.update(service_account_id, dto)


@router.delete(
    path="/{service_account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Деактивировать сервисный аккаунт",
    description="Деактивирует сервисный аккаунт, чтобы он больше не мог получать доступ к API.",
)
async def delete_service_account(
    service_account_id: UUID,
    crud: ServiceAccountCrudDep,
) -> None:
    await crud.delete(service_account_id)
