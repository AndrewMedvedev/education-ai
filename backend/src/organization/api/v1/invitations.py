from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Path, status

from src.iam.dependencies import CurrentIdentity, require_permissions
from src.iam.domain.entities import Invitation as IAMInvitation
from src.iam.domain.entities import Membership
from src.organization.application.dtos import InvitationCreate
from src.organization.application.services.invitation_management import (
    InvitationSummary,
)
from src.organization.dependencies.services import (
    InvitationManagementDep,
    InvitationServiceDep,
)
from src.organization.domain.entities import Invitation as OrganizationInvitation
from src.organization.domain.permissions.invitations import DELETE_INVITATION, INVITE
from src.shared.application.dtos import Page
from src.shared.dependencies import PaginationDep

router = APIRouter(
    prefix="/organizations/invitations",
    tags=["Приглашения в организации | Invitations"],
)


@router.get("", dependencies=[Depends(require_permissions(INVITE.code))])
async def list_invitations(
    service: InvitationManagementDep,
    identity: CurrentIdentity,
    pagination: PaginationDep,
) -> Page[InvitationSummary]:
    return await service.list(identity.organization_id, pagination)


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
) -> OrganizationInvitation | IAMInvitation:
    return await service.create(dto=dto, identity=identity)


@router.post(
    path="/accept/{token}",
    status_code=status.HTTP_201_CREATED,
    summary="Принять приглашение",
)
async def accept_invitation(
    token: Annotated[str, Path(description="Токен из пригласительного письма")],
    service: InvitationManagementDep,
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
    service: InvitationManagementDep,
    identity: CurrentIdentity,
    source: Literal["iam", "organization"] = "organization",
) -> None:
    await service.revoke(invitation_id, source, identity.organization_id)


@router.post(
    "/{invitation_id}/resend", dependencies=[Depends(require_permissions(INVITE.code))]
)
async def resend_invitation(
    invitation_id: UUID,
    management: InvitationManagementDep,
    service: InvitationServiceDep,
    identity: CurrentIdentity,
    source: Literal["iam", "organization"] = "organization",
) -> InvitationSummary:
    invitation = await management.resend(
        invitation_id, source, identity.organization_id
    )
    result = await service.create(
        InvitationCreate(
            email=invitation.email.value, granted_roles=invitation.granted_roles
        ),
        identity,
    )
    result_source = "iam" if isinstance(result, IAMInvitation) else "organization"
    return management.summarize(result, result_source)
