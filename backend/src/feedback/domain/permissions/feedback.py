from src.iam.domain.entities import Permission
from src.iam.domain.permissions.registry import register_permission
from src.iam.domain.vo import PermissionScope

READ = register_permission(
    Permission(
        resource="feedback",
        action="read",
        scopes=frozenset({PermissionScope.GLOBAL}),
        title="Просмотр отзывов о платформе",
    ),
)
