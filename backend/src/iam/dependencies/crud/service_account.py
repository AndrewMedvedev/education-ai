from typing import Annotated, Any

from fastapi import Depends

from src.iam.application.dtos import (
    CreateServiceAccountDTO,
    ServiceAccountResponse,
    UpdateServiceAccountDTO,
)
from src.iam.dependencies.repos import ServiceAccountRepositoryDep
from src.iam.domain.entities import ServiceAccount
from src.shared.application.crud import Crud
from src.shared.application.dtos import Page
from src.shared.dependencies import PaginationDep, TransactionDep
from src.shared.domain.helpers import apply_changes
from src.shared.utils.time import current_datetime

ServiceAccountCrud = Crud[
    ServiceAccount,
    ServiceAccountResponse,
    CreateServiceAccountDTO,
    UpdateServiceAccountDTO,
    None, None, None, None,
]


async def update_handler(
        service_account: ServiceAccount,
        dto: UpdateServiceAccountDTO,
        options: Any | None = None,
) -> ServiceAccount:
    return apply_changes(service_account, **dto.model_dump(exclude_none=True))


async def delete_handler(
        service_account: ServiceAccount,
        options: Any | None = None,
) -> ServiceAccount:
    service_account.is_active = False
    service_account.updated_at = current_datetime()
    return service_account


def map_to_response(service_account: ServiceAccount) -> ServiceAccountResponse:
    return ServiceAccountResponse.model_validate(service_account)


def get_service_account_crud(
        transaction: TransactionDep,
        service_account_repository: ServiceAccountRepositoryDep,
) -> ServiceAccountCrud:
    return ServiceAccountCrud(
        service_account_repository,
        transaction,
        map_to_response,
        update_handler=update_handler,
        delete_handler=delete_handler,
    )


async def get_service_accounts_list(
        pagination: PaginationDep,
        service_account_repo: ServiceAccountRepositoryDep,
) -> Page[ServiceAccountResponse]:
    service_accounts = await service_account_repo.find(pagination)
    return service_accounts.to_response(map_to_response)


ServiceAccountCrudDep = Annotated[ServiceAccountCrud, Depends(get_service_account_crud)]
service_accounts_list_depends = Depends(get_service_accounts_list)
