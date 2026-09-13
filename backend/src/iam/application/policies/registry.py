from collections.abc import Callable

from src.iam.application.dtos import Identity
from src.iam.domain.entities import Permission
from src.iam.domain.vo import PermissionScope

type AuthorizationPolicy = Callable[[Identity, object], bool]

_policy_registry: dict[tuple[str, PermissionScope], AuthorizationPolicy] = {}


def register_policy(
    permission: Permission, scope: PermissionScope,
) -> Callable[[AuthorizationPolicy], AuthorizationPolicy]:

    if scope not in permission.scopes:
        raise ValueError(
            f"Scope '{scope.value}' is not supported by permission '{permission.code}'.",
        )

    key = (permission.code, scope)

    def decorator(policy: AuthorizationPolicy) -> AuthorizationPolicy:

        if key in _policy_registry:
            raise ValueError(
                f"Authorization policy already registered: {permission.code} [{scope.value}]",
            )

        _policy_registry[key] = policy
        return policy

    return decorator


def get_permission_policies(
        permission: Permission,
) -> tuple[tuple[PermissionScope, AuthorizationPolicy], ...]:
    """Возвращает все зарегистрированные политики авторизации для permission"""

    return tuple(
        (scope, policy)
        for (code, scope), policy in _policy_registry.items()
        if code == permission.code
    )
