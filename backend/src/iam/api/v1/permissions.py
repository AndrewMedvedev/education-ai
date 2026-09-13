from fastapi import APIRouter, Depends, status

from src.iam.application.dtos import PermissionResponse
from src.iam.dependencies.permissions import get_permission_list, require_permissions
from src.iam.domain.permissions import permissions as acl
from src.shared.application.dtos import Page

router = APIRouter(prefix="/permissions", tags=["Разрешения | Permissions"])


@router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=PermissionResponse,
    dependencies=[Depends(require_permissions(acl.READ.code))],
    summary="Получить список прав",
)
async def get_permissions(
        permissions: Page[PermissionResponse] = Depends(get_permission_list),
) -> PermissionResponse:
    return permissions
