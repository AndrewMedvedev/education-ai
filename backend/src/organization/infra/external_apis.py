from uuid import UUID

from src.iam.application.dtos import InvitationCreate, UserResponse
from src.iam.application.dtos.membership import CreateMembershipDTO
from src.iam.domain.entities import Invitation, Membership

from .services.client import SrvOrganizationClient


async def get_user_by_email(email: str, client: SrvOrganizationClient) -> UserResponse | None:
    async with client._get_token_session() as session:  # noqa: SLF001
        try:
            result = await session.get(url=f"/api/v1/users/by-email/{email}")
            result.raise_for_status()
            response = await result.json()
            return UserResponse(**response)
        except:  # noqa: E722
            return None


async def invite_user_in_system(
    dto: InvitationCreate,
    client: SrvOrganizationClient,
) -> Invitation | None:
    async with client._get_token_session() as session:  # noqa: SLF001
        try:
            result = await session.post(
                url="/api/v1/invitations", json=dto.model_dump(mode="json")
            )
            result.raise_for_status()
            response = await result.json()
            response.pop("_events", None)
            return Invitation(**response)
        except:  # noqa: E722
            return None


class MembershipClient:
    def __init__(self, client: SrvOrganizationClient):
        self._client = client

    async def create_membership(self, dto: CreateMembershipDTO) -> Membership:
        async with self._client._get_token_session() as session:  # noqa: SLF001
            result = await session.post(
                url="/api/v1/memberships", json=dto.model_dump(mode="json")
            )
            result.raise_for_status()
            response = await result.json()
            response.pop("_events", None)
            return Membership(**response)

    async def get_user_membership(
        self,
        organization_id: UUID,
        user_id: UUID,
    ) -> Membership | None:
        async with self._client._get_token_session() as session:  # noqa: SLF001
            try:
                result = await session.get(url=f"/api/v1/memberships/{organization_id}/{user_id}")
                result.raise_for_status()
                response = await result.json()
                response.pop("_events", None)
                return Membership(**response)
            except:  # noqa: E722
                return None
