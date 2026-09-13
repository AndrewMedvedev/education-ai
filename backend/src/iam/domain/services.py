from collections.abc import Sequence
from uuid import UUID

from .entities import Invitation, Membership, Role, User
from .exceptions import PermissionDeniedError
from .vo import FullName, SecretHash, Username


def accept_for_new_user(
        invitation: Invitation,
        password_hash: str,
        *,
        full_name: str | None = None,
        username: str | None = None,
) -> tuple[User, Membership]:

    full_name = FullName(full_name) if full_name is not None else None
    username = Username(username) if username is not None else None

    user = User(
        email=invitation.email,
        password_hash=SecretHash(password_hash),
        username=username,
        full_name=full_name,
    )

    membership = Membership(
        user_id=user.id,
        organization_id=invitation.organization_id,
        roles=invitation.granted_roles,
    )

    invitation.mark_as_used()

    return user, membership


def validate_roles_assignment(roles: Sequence[Role], organization_id: UUID) -> None:
    """Проверяет допустимость назначения ролей для указанной организации."""

    invalid_roles = [
        role
        for role in roles
        if not role.is_default and role.organization_id != organization_id
    ]
    if invalid_roles:
        raise PermissionDeniedError("Cannot assign roles outside the target organization.")
