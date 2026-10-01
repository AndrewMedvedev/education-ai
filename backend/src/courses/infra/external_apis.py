from src.iam.application.dtos import InvitationCreate, UserResponse
from src.iam.domain.entities import Invitation

from .services.client import SrvCourseClient


async def get_user_by_email(email: str, client: SrvCourseClient) -> UserResponse | None:
    async with client._get_token_session() as session:  # noqa: SLF001
        try:
            result = await session.get(url=f"/api/v1/users/by-email/{email}")
            result.raise_for_status()
            response = await result.json()
            response.pop("_events", None)
            return UserResponse(**response)
        except:
            return None


async def invite_user_in_system(
    dto: InvitationCreate,
    client: SrvCourseClient,
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
        except:
            return None
