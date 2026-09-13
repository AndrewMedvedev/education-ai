from src.iam.domain.entities import Permission
from src.iam.domain.vo import PermissionScope

from .registry import register_permission

READ = register_permission(
    Permission(
        resource="permissions",
        action="read",
        scopes=frozenset({PermissionScope.GLOBAL}),
        title="Просмотр списка прав",
    ),
)
