from typing import Annotated

from fastapi import Depends

from src.organization.domain.entities import Organization
from src.organization.infra.database.repos.invitation import SqlInvitationRepository
from src.organization.infra.database.repos.organization import SqlOrganizationRepository
from src.shared.application.dtos import Page
from src.shared.dependencies import DBSession, PaginationDep

from ..application.repos import InvitationRepository, OrganizationRepository


def get_organization_repo(session: DBSession) -> SqlOrganizationRepository:
    return SqlOrganizationRepository(session)


def get_invitation_repo(session: DBSession) -> SqlInvitationRepository:
    return SqlInvitationRepository(session)


OrganizationRepoDep = Annotated[OrganizationRepository, Depends(get_organization_repo)]
InvitationRepoDep = Annotated[InvitationRepository, Depends(get_invitation_repo)]


async def paginate_organizations(
    pagination: PaginationDep,
    organization_repo: OrganizationRepoDep,
) -> Page[Organization]:
    return await organization_repo.find(pagination=pagination)
