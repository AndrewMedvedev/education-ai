from src.iam.application.dtos import CreateUserDTO, TokensResponse
from src.iam.application.repos import (
    InvitationRepository,
    MembershipRepository,
    RoleRepository,
    UserRepository,
)
from src.iam.domain.services import accept_for_new_user
from src.iam.security import hash_password_async, validate_password_strength_async
from src.shared.application.transaction import Transaction
from src.shared.domain.exceptions import AlreadyExistsError, NotFoundError

from .auth import create_tokens_for_user


class RegistrationService:
    def __init__(
            self,
            transaction: Transaction,
            user_repo: UserRepository,
            membership_repo: MembershipRepository,
            role_repo: RoleRepository,
            invitation_repo: InvitationRepository
    ) -> None:
        self._transaction = transaction
        self._user_repo = user_repo
        self._membership_repo = membership_repo
        self._role_repo = role_repo
        self._invitation_repo = invitation_repo

    async def accept_invitation(self, token: str, dto: CreateUserDTO) -> TokensResponse:
        """Принять приглашение. Регистрирует пользователя в системе."""

        if (invitation := await self._invitation_repo.get_by_token(token)) is None \
                or not invitation.is_valid:
            raise NotFoundError(f"Invitation with token - '{token}' not found or invalid.")

        if (user := await self._user_repo.get_by_email(invitation.email)) is not None:
            raise AlreadyExistsError(f"User with email - '{user.email}' already registered.")

        await validate_password_strength_async(dto.password, email=invitation.email)

        password_hash = await hash_password_async(dto.password)
        user, membership = accept_for_new_user(
            invitation, password_hash, username=dto.username, full_name=dto.full_name,
        )

        await self._user_repo.create(user)
        await self._membership_repo.create(membership)

        await self._transaction(user, membership)

        roles = await self._role_repo.get_by_ids(list(membership.roles))

        return create_tokens_for_user(user=user, membership=membership, roles=roles)
