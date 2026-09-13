from src.iam.application.dtos import Identity
from src.iam.domain.entities import Permission
from src.iam.domain.exceptions import PermissionDeniedError

from .registry import get_permission_policies


def has_permission(identity: Identity, permission: Permission) -> bool:
    """Проверяет наличие конкретного права у субъекта авторизации."""

    return permission.code in identity.permissions


def can(identity: Identity, permission: Permission, resource: object | None = None) -> bool:
    """
    Проверяет доступ субъекта авторизации к ресурсу.

    Если ресурс не передан, проверяется только наличие права.
    При наличии ресурса дополнительно применяются зарегистрированные
    политики авторизации.
    """

    if not has_permission(identity, permission):
        return False

    if resource is None:
        return True

    if not (policies := get_permission_policies(permission)):
        return False

    return any(policy(identity, resource) for _, policy in policies)


def authorize(identity: Identity, permission: Permission, resource: object | None = None) -> None:
    """Проверяет доступ и выбрасывает исключение при отказе."""

    if can(identity, permission, resource):
        return

    if not has_permission(identity, permission):
        raise PermissionDeniedError(f"Missing required permission: {permission.code}.")

    raise PermissionDeniedError(f"Access denied for permission '{permission.code}'.")
