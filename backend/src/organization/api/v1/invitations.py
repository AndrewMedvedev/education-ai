from typing import Annotated

from uuid import UUID

from fastapi import APIRouter, Depends, Path, status

from src.iam.dependencies import CurrentIdentity, require_permissions
from src.iam.domain.entities import Membership
from src.organization.application.dtos import InvitationCreate
from src.organization.dependencies.services import InvitationServiceDep
from src.organization.domain.entities import Invitation
from src.organization.domain.permissions.invitations import DELETE_INVITATION, INVITE

router = APIRouter(
    prefix="/organizations/invitations",
    tags=["Приглашения в организации | Invitations"],
)


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    summary="Пригласить пользователя",
    dependencies=[Depends(require_permissions(INVITE.code))],
)
async def create_invitations(
    dto: InvitationCreate,
    service: InvitationServiceDep,
    identity: CurrentIdentity,
) -> Invitation:
    return await service.create(dto=dto, invited_by=identity.id)


@router.post(
    path="/accept/{token}",
    status_code=status.HTTP_201_CREATED,
    summary="Принять приглашение",
)
async def accept_invitation(
    token: Annotated[str, Path(description="Токен из пригласительного письма")],
    service: InvitationServiceDep,
    identity: CurrentIdentity,
) -> Membership:
    return await service.accept(token=token, user_id=identity.id)


@router.delete(
    path="/revoke/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отозвать приглашение",
    dependencies=[Depends(require_permissions(DELETE_INVITATION.code))],
)
async def revoke_invitation(
    invitation_id: UUID,
    service: InvitationServiceDep,
) -> None:
    await service.revoke_invitation(invitation_id=invitation_id)
