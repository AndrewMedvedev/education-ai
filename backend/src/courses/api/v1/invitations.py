from typing import Annotated

from fastapi import APIRouter, Path, status

from src.courses.application.dtos import InvitationCreate
from src.courses.dependencies.services import InvitationServiceDep
from src.courses.domain.entities import Invitation, Member
from src.iam.dependencies.identity import CurrentIdentity

router = APIRouter(
    prefix="/courses/invitations", tags=["Приглашения в курсы | Invitations in courses"]
)


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    summary="Пригласить пользователя",
)
async def create_invitations(
    identity: CurrentIdentity,
    service: InvitationServiceDep,
    dto: InvitationCreate,
) -> Invitation:
    return await service.create(dto=dto, identity=identity)


@router.post(
    path="/accept/{token}",
    status_code=status.HTTP_201_CREATED,
    summary="Принять приглашение",
    description="Один из способов регистрации.",
)
async def accept_invitation(
    identity: CurrentIdentity,
    token: Annotated[str, Path(description="Токен из пригласительного письма")],
    service: InvitationServiceDep,
) -> Member:
    return await service.accept(token=token, user_id=identity.id)
