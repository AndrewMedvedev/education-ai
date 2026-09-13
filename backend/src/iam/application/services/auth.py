from typing import Literal

from datetime import datetime, timedelta
from uuid import UUID

from src.core.settings import jwt_config
from src.iam.application.builders import build_login_response
from src.iam.application.dtos import (
    IdentityType,
    LoginResponse,
    LogoutRequest,
    TokenRequest,
    TokensResponse,
    UserCredentials,
)
from src.iam.application.repos import MembershipRepository, RoleRepository, UserRepository
from src.iam.domain.entities import Membership, Role, User
from src.iam.domain.exceptions import UnauthorizedError
from src.iam.domain.vo import Email
from src.iam.security import (
    create_access_token,
    create_authentication_token,
    create_refresh_token,
    decode_token,
    verify_password_async,
)
from src.organization.application.repos import OrganizationRepository
from src.shared.infra.cache import Cache
from src.shared.utils.time import from_timestamp, get_expiration_timestamp

from .blacklist import is_revoked, revoke_token


def _verify_token(
    token: str,
    expected_type: Literal["authentication", "access", "refresh"],
) -> tuple[UUID, UUID | None, UUID, datetime]:
    """Проверяет токен, возвращает user_id, membership_id, jti, expires_at."""

    payload = decode_token(token)

    if payload.get("typ") != expected_type:
        raise UnauthorizedError(f"Invalid token type. Expected - '{expected_type}'.")

    claims = ("sub", "mid", "jti", "exp")

    sub, mid, jti, exp = (payload.get(claim) for claim in claims)

    try:
        sub_uuid, mid_uuid, jti_uuid, exp_dt = (
            UUID(sub),
            UUID(mid) if mid else None,
            UUID(jti),
            from_timestamp(exp),
        )
    except (ValueError, TypeError):
        raise UnauthorizedError("Invalid claim format") from None

    return sub_uuid, mid_uuid, jti_uuid, exp_dt


def create_tokens_for_user(
    user: User,
    membership: Membership,
    roles: set[Role],
) -> TokensResponse:
    """Выпуск пары токенов для пользователя."""

    permissions = {grant.permission for role in roles for grant in role.permissions}
    access_token = create_access_token(
        identity_id=user.id,
        identity_type=IdentityType.USER,
        email=user.email,
        membership_id=membership.id,
        organization_id=membership.organization_id,
        roles={role.code for role in roles},
        permissions=permissions,
    )
    refresh_token = create_refresh_token(user_id=user.id, membership_id=membership.id)

    access_token_expires_at = get_expiration_timestamp(
        expires_in=timedelta(minutes=jwt_config.access_token_expires_in_minutes),
    )

    return TokensResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=access_token_expires_at,
    )


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        membership_repo: MembershipRepository,
        role_repo: RoleRepository,
        organization_repo: OrganizationRepository,
        cache: Cache[bool],
    ) -> None:
        self._user_repo = user_repo
        self._membership_repo = membership_repo
        self._role_repo = role_repo
        self._organization_repo = organization_repo
        self._cache = cache

    async def login(self, credentials: UserCredentials) -> LoginResponse:
        """Поверяет учётную запись и выдаёт токен для аутентификации."""

        email = Email(credentials.email)

        if (user := await self._user_repo.get_by_email(email)) is None:
            raise UnauthorizedError(f"User account - '{email}' not found.")

        if (
            not await verify_password_async(
                credentials.password,
                user.password_hash.get_hashed_value(),
            )
            or not user.is_active
        ):
            raise UnauthorizedError("Invalid credentials or user is not active.")

        memberships = await self._membership_repo.get_by_user(user.id)

        organization_ids = [membership.organization_id for membership in memberships]
        organizations = await self._organization_repo.get_by_ids(organization_ids)

        authentication_token = create_authentication_token(user.id)

        return build_login_response(
            authentication_token=authentication_token,
            memberships=memberships,
            organizations=organizations,
        )

    async def authenticate(self, request: TokenRequest) -> TokensResponse:
        """Получение пары токенов в выбранной организации."""

        user_id, _, _, _ = _verify_token(
            request.authentication_token,
            expected_type="authentication",
        )

        if (user := await self._user_repo.read(user_id)) is None:
            raise UnauthorizedError(f"User - '{user_id}' not found.")

        if (membership := await self._membership_repo.read(request.membership_id)) is None:
            raise UnauthorizedError(f"Membership - '{request.membership_id}' not found.")

        if membership.user_id != user_id:
            raise UnauthorizedError("")

        roles = await self._role_repo.get_by_ids(list(membership.roles))

        return create_tokens_for_user(user=user, membership=membership, roles=roles)

    async def refresh_tokens(self, refresh_token: str) -> TokensResponse:
        """Получить новую пару access + refresh."""

        user_id, membership_id, jti, expires_at = _verify_token(
            refresh_token,
            expected_type="refresh",
        )

        if await is_revoked(jti, self._cache):
            raise UnauthorizedError("Refresh token revoked.")

        if (user := await self._user_repo.read(user_id)) is None or not user.is_active:
            raise UnauthorizedError(f"User - '{user_id}' inactive.")

        if (
            membership := await self._membership_repo.read(membership_id)
        ) is None or not membership.is_active:
            raise UnauthorizedError(f"Membership - '{membership_id}' inactive.")

        roles = await self._role_repo.get_by_ids(list(membership.roles))

        await revoke_token(jti, expires_at, self._cache)

        return create_tokens_for_user(user=user, membership=membership, roles=roles)

    async def logout(self, request: LogoutRequest) -> None:
        """
        Выход их аккаунта, отзывает пару токенов (помещает в чёрный список).
        Идемпотентный метод.
        """

        pairs: tuple[tuple[Literal["access", "refresh"], str]] = (
            ("access", request.access_token),
            ("refresh", request.refresh_token),
        )
        for expected_type, token in pairs:
            try:
                _, _, jti, expires_at = _verify_token(token, expected_type)
            except UnauthorizedError:
                continue

            await revoke_token(jti, expires_at, self._cache)
