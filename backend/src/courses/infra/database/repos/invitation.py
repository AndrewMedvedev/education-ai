from uuid import UUID

from sqlalchemy import select

from src.shared.domain.vo import Email
from src.shared.infra.repos import SqlAlchemyRepository

from ....domain.entities import Invitation
from ..mappers import InvitationMapper
from ..models import InvitationOrm


class SqlInvitationRepository(SqlAlchemyRepository[Invitation, InvitationOrm]):
    model = InvitationOrm
    model_mapper = InvitationMapper  # pyright: ignore[reportAssignmentType]

    async def get_by_token(self, token: str) -> Invitation | None:
        stmt = select(self.model).where(self.model.token == token)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)

    async def get_active(
        self,
        email: Email,
        course_id: UUID,
    ) -> Invitation | None:
        stmt = (
            select(self.model)
            .where(
                (self.model.email == email.value)
                & (self.model.course_id == course_id)
                & (self.model.is_used.is_(False))
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)
