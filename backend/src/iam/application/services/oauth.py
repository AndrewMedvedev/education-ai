from collections.abc import Sequence
from datetime import timedelta

from src.core.settings import jwt_config
from src.iam.application.dtos import IdentityType, OAuthCredentials, OAuthTokenResponse
from src.iam.application.repos import RoleRepository, ServiceAccountRepository
from src.iam.domain.entities import Role, ServiceAccount
from src.iam.domain.exceptions import UnauthorizedError
from src.iam.security import create_access_token, verify_password_async
from src.shared.utils.time import get_expiration_timestamp


def _create_token_for_service_account(
    service_account: ServiceAccount,
    roles: Sequence[Role],
) -> OAuthTokenResponse:

    permissions = {grant.permission for role in roles for grant in role.permissions}
    access_token = create_access_token(
        identity_id=service_account.id,
        identity_type=IdentityType.SERVICE_ACCOUNT,
        organization_id=service_account.organization_id,
        roles={role.code for role in roles},
        permissions=permissions,
    )

    access_token_expires_at = get_expiration_timestamp(
        expires_in=timedelta(minutes=jwt_config.access_token_expires_in_minutes),
    )

    return OAuthTokenResponse(access_token=access_token, expires_at=access_token_expires_at)


class OAuthService:
    def __init__(
        self,
        service_account_repo: ServiceAccountRepository,
        role_repo: RoleRepository,
    ) -> None:
        self._service_account_repo = service_account_repo
        self._role_repo = role_repo

    async def issue_token(self, credentials: OAuthCredentials) -> OAuthTokenResponse:

        service_account = await self._service_account_repo.get_by_client_id(credentials.client_id)

        if service_account is None or not service_account.is_active:
            raise UnauthorizedError("Invalid client credentials.")

        if not await verify_password_async(
            credentials.client_secret,
            service_account.client_secret_hash.get_hashed_value(),
        ):
            raise UnauthorizedError("Invalid client credentials.")

        roles = await self._role_repo.get_by_ids(service_account.roles)

        return _create_token_for_service_account(service_account, roles)
