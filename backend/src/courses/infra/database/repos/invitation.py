from uuid import UUID

from sqlalchemy import select

from src.shared.application.dtos import Page, Pagination
from src.shared.domain.vo import Email
from src.shared.infra.repos import SqlAlchemyRepository
from src.shared.utils.time import current_datetime

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

    async def find_by_course(
        self,
        course_id: UUID,
        pagination: Pagination,
    ) -> Page[Invitation]:
        """Приглашения курса, которые ещё ждут ответа (не приняты и не истекли), новые сверху."""

        stmt = select(self.model).where(
            self.model.course_id == course_id,
            self.model.is_used.is_(False),
            self.model.expires_at > current_datetime(),
        )
        return await self._paginate(stmt, pagination)

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
