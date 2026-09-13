from src.iam.domain.entities import Permission
from src.iam.domain.permissions.registry import register_permission
from src.iam.domain.vo import PermissionScope

READ = register_permission(
    Permission(
        resource="theory_session",
        action="read",
        scopes=frozenset({
            PermissionScope.COURSE,
            PermissionScope.ORGANIZATION,
            PermissionScope.OWN,
            PermissionScope.COURSE,
        }),
        title="Просмотр списка метрик теории",
    ),
)
