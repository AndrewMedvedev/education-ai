from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.iam.application.dtos.membership import CreateMembershipDTO
from src.iam.dependencies import require_permissions
from src.iam.dependencies.repos import MembershipRepositoryDep
from src.iam.dependencies.services import MembershipServiceDep
from src.iam.domain.entities import Membership
from src.iam.domain.permissions.membership import CREATE, READ

router = APIRouter(prefix="/memberships", tags=["Членство | Membership"])


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    summary="Проверить, является ли пользователь членом организации",
    dependencies=[Depends(require_permissions(CREATE.code))],
)
async def create_membership(
    dto: CreateMembershipDTO,
    service: MembershipServiceDep,
) -> Membership:
    return await service.create(dto)


@router.get(
    path="/{organization_id}/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Проверить, является ли пользователь членом организации",
    dependencies=[Depends(require_permissions(READ.code))],
)
async def is_user_member(
    organization_id: UUID,
    user_id: UUID,
    repo: MembershipRepositoryDep,
) -> Membership:
    result = await repo.get_by_user_and_organization(user_id, organization_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this organization.",
        )
    return result
