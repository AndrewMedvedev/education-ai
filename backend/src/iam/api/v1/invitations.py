from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Response, status
from pydantic import BaseModel

from src.iam.application.dtos import CreateUserDTO, InvitationCreate, TokensResponse
from src.iam.dependencies import CurrentIdentity, require_permissions
from src.iam.dependencies.repos import (
    InvitationRepositoryDep,
    OrganizationRepositoryDep,
    UserRepositoryDep,
)
from src.iam.dependencies.services import InvitationServiceDep, RegistrationServiceDep
from src.iam.domain.entities import Invitation
from src.iam.domain.permissions.invitations import DELETE_INVITATION, INVITE
from src.organization.dependencies.base import (
    InvitationRepoDep as OrganizationInvitationRepoDep,
)
from src.shared.domain.exceptions import NotFoundError

router = APIRouter(prefix="/invitations", tags=["Приглашения | Invitations"])


class InvitationPreview(BaseModel):
    email: str
    registration_required: bool
    organization_id: UUID | None = None
    organization_name: str | None = None


@router.get("/preview/{token}", response_model=InvitationPreview)
async def preview_invitation(
    token: str,
    response: Response,
    invitation_repo: InvitationRepositoryDep,
    organization_invitation_repo: OrganizationInvitationRepoDep,
    user_repo: UserRepositoryDep,
    organization_repo: OrganizationRepositoryDep,
) -> InvitationPreview:
    """Resolve a bearer invitation without requiring an existing user session."""
    response.headers["Cache-Control"] = "no-store"
    invitation = await invitation_repo.get_by_token(token)
    is_registration = invitation is not None
    if invitation is None:
        invitation = await organization_invitation_repo.get_by_token(token)
    if invitation is None or not invitation.is_valid:
        raise NotFoundError("Invitation not found or invalid.")
    user = await user_repo.get_by_email(invitation.email)
    organization = (
        await organization_repo.read(invitation.organization_id)
        if invitation.organization_id
        else None
    )
    return InvitationPreview(
        email=invitation.email.value,
        registration_required=is_registration and user is None,
        organization_id=invitation.organization_id,
        organization_name=organization.name if organization else None,
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
    description="Регистрирует пользователя по токену из приглашения и возвращает токены авторизации.",
)
async def accept_invitation(
    token: Annotated[str, Path(description="Токен из пригласительного письма")],
    dto: CreateUserDTO,
    service: RegistrationServiceDep,
) -> TokensResponse:
    return await service.accept_invitation(token=token, dto=dto)


@router.delete(
    path="/revoke/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отозвать приглашение",
    dependencies=[Depends(require_permissions(DELETE_INVITATION.code))],
)
async def revoke_invitation(
    invitation_id: UUID,
    service: InvitationServiceDep,
    identity: CurrentIdentity,
) -> None:
    await service.revoke_invitation(
        invitation_id=invitation_id, organization_id=identity.organization_id
    )
