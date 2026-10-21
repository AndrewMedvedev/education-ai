from uuid import UUID

from src.iam.application.dtos import InvitationCreate as IAMInvitationCreate
from src.iam.application.dtos import UserResponse
from src.iam.domain.entities import Invitation as IAMInvitation
from src.iam.domain.entities import Membership
from src.organization.application.dtos import InvitationCreate as OrganizationInvitationCreate
from src.organization.domain.entities import Invitation as OrganizationInvitation

from .services.client import SrvCourseClient


class IAMClient:
    def __init__(self, client: SrvCourseClient) -> None:
        self.client = client

    async def get_user_by_email(
        self,
        email: str,
    ) -> UserResponse | None:
        async with self.client._get_token_session() as session:  # noqa: SLF001
            try:
                result = await session.get(url=f"/api/v1/users/by-email/{email}")
                result.raise_for_status()
                response = await result.json()
                response.pop("_events", None)
                return UserResponse(**response)
            except:
                return None

    async def invite_user_in_system(
        self,
        dto: IAMInvitationCreate,
    ) -> IAMInvitation | None:
        async with self.client._get_token_session() as session:  # noqa: SLF001
            try:
                result = await session.post(
                    url="/api/v1/invitations", json=dto.model_dump(mode="json")
                )
                result.raise_for_status()
                response = await result.json()
                response.pop("_events", None)
                return IAMInvitation(**response)
            except:
                return None

    async def get_user_membership(
        self,
        organization_id: UUID,
        user_id: UUID,
    ) -> Membership | None:
        async with self.client._get_token_session() as session:  # noqa: SLF001
            try:
                result = await session.get(url=f"/api/v1/memberships/{organization_id}/{user_id}")
                result.raise_for_status()
                response = await result.json()
                response.pop("_events", None)
                return Membership(**response)
            except:  # noqa: E722
                return None


async def invite_user_in_organization(
    client: SrvCourseClient, dto: OrganizationInvitationCreate
) -> OrganizationInvitation | None:
    async with client._get_token_session() as session:  # noqa: SLF001
        try:
            result = await session.post(
                url="/api/v1/organizations/invitations", json=dto.model_dump(mode="json")
            )
            result.raise_for_status()
            response = await result.json()
            response.pop("_events", None)
            return OrganizationInvitation(**response)
        except:
            return None
