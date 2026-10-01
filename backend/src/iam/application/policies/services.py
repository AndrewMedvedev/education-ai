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
    При наличии ресурса сначала применяются зарегистрированные
    политики авторизации. Если политик нет, проверяется наличие права.
    """

    if resource is None:
        return has_permission(identity, permission)

    if policies := get_permission_policies(permission):
        return any(policy(identity, resource) for _, policy in policies)

    return has_permission(identity, permission)


def authorize(identity: Identity, permission: Permission, resource: object | None = None) -> None:
    """Проверяет доступ и выбрасывает исключение при отказе."""

    if can(identity, permission, resource):
        return

    if resource is not None and get_permission_policies(permission):
        raise PermissionDeniedError(f"Access denied for permission '{permission.code}'.")

    raise PermissionDeniedError(f"Missing required permission: {permission.code}.")
