from typing import Annotated

from fastapi import Depends

from src.shared.application.dtos import Page
from src.shared.dependencies import DBSession, PaginationDep

from ..application.repos import OrganizationRepository
from ..application.services import OrganizationService
from ..domain.entities import Organization
from ..infra.repos import SqlOrganizationRepository


def get_organization_repo(session: DBSession) -> SqlOrganizationRepository:
    return SqlOrganizationRepository(session)


OrganizationRepoDep = Annotated[OrganizationRepository, Depends(get_organization_repo)]


def get_organization_service(
    session: DBSession,
    repo: OrganizationRepoDep,
) -> OrganizationService:
    return OrganizationService(session, repo)


OrganizationServiceDep = Annotated[OrganizationService, Depends(get_organization_service)]


async def paginate_organizations(
    pagination: PaginationDep,
    organization_repo: OrganizationRepoDep,
) -> Page[Organization]:
    return await organization_repo.find(pagination=pagination)
