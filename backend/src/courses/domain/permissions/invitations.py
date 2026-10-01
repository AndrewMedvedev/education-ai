from src.iam.domain.entities import Permission
from src.iam.domain.permissions.registry import register_permission
from src.iam.domain.vo import PermissionScope

INVITE = register_permission(
    Permission(
        resource="course-invitations",
        action="invite",
        scopes=frozenset(
            {
                PermissionScope.OWN,
                PermissionScope.COURSE,
            }
        ),
        title="Приглашение в курс",
    ),
)
