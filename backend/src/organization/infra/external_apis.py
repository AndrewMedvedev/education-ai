from uuid import UUID

from pydantic import TypeAdapter

from src.iam.application.dtos import InvitationCreate, UserResponse
from src.iam.application.dtos.membership import CreateMembershipDTO
from src.iam.domain.entities import Invitation, Membership

from .services.client import SrvOrganizationClient


class IAMClient:
    def __init__(self, client: SrvOrganizationClient) -> None:
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
            except:  # noqa: E722
                return None

    async def invite_user_in_system(
        self,
        dto: InvitationCreate,
    ) -> Invitation:
        async with self.client._get_token_session() as session:  # noqa: SLF001
            result = await session.post(
                url="/api/v1/invitations",
                json=dto.model_dump(mode="json", by_alias=True),
            )
            result.raise_for_status()

            response = await result.json()
            response.pop("_events", None)

            return TypeAdapter(Invitation).validate_python(response)


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
