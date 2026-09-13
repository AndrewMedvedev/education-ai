from src.iam.application.dtos import ClientCredentials, CreateServiceAccountDTO
from src.iam.application.repos import RoleRepository, ServiceAccountRepository
from src.iam.domain.entities import ServiceAccount
from src.iam.domain.services import validate_roles_assignment
from src.iam.domain.vo import SecretHash
from src.iam.security import generate_client_id, generate_client_secret, hash_password_async
from src.organization.application.repos import OrganizationRepository
from src.organization.domain.entities import Organization
from src.shared.application.repos import get_or_raise_404
from src.shared.application.uow import UnitOfWork
from src.shared.domain.exceptions import NotFoundError


class ClientCredentialsService:
    def __init__(
        self,
        uow: UnitOfWork,
        organization_repo: OrganizationRepository,
        service_account_repo: ServiceAccountRepository,
        role_repo: RoleRepository,
    ) -> None:
        self._uow = uow
        self._organization_repo = organization_repo
        self._service_account_repo = service_account_repo
        self._role_repo = role_repo

    async def create(self, dto: CreateServiceAccountDTO) -> ClientCredentials:
        """Создаёт сервисный аккаунт и возвращает client credentials."""

        organization = await get_or_raise_404(
            self._organization_repo.read,
            dto.organization_id,
            Organization,
        )

        roles = await self._role_repo.get_by_ids(dto.roles)

        if len(roles) != len(dto.roles):
            raise NotFoundError("One or more roles were not found.")

        validate_roles_assignment(roles, organization.id)

        client_id, client_secret = generate_client_id(), generate_client_secret()
        client_secret_hash = await hash_password_async(client_secret)

        service_account = ServiceAccount(
            name=dto.name,
            description=dto.description,
            client_id=client_id,
            client_secret_hash=SecretHash(client_secret_hash),
            organization_id=dto.organization_id,
            roles=dto.roles,
        )

        await self._service_account_repo.create(service_account)
        await self._uow.commit()

        return ClientCredentials(
            id=service_account.id,
            created_at=service_account.created_at,
            client_id=client_id,
            client_secret=client_secret,
            is_active=service_account.is_active,
        )
