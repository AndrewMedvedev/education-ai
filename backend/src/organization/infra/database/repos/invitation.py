from uuid import UUID

from sqlalchemy import select

from src.organization.domain.entities import Invitation
from src.organization.infra.database.mappers import InvitationMapper
from src.organization.infra.database.models import InvitationOrm
from src.shared.domain.vo import Email
from src.shared.infra.database import SqlAlchemyRepository


class SqlInvitationRepository(SqlAlchemyRepository[Invitation, InvitationOrm]):
    model = InvitationOrm
    model_mapper = InvitationMapper  # pyright: ignore[reportAssignmentType]

    async def get_by_token(self, token: str) -> Invitation | None:
        stmt = select(self.model).where(
            (self.model.token == token) & (self.model.deleted_at.is_(None)),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self.model_mapper.from_model(model) if model else None

    async def get_active_by_email(self, email: Email) -> tuple[Invitation, ...]:
        stmt = select(self.model).where(
            (self.model.email == email.value) & (self.model.deleted_at.is_(None)),
        )
        results = await self._session.execute(stmt)
        models = results.scalars().all()
        return tuple(self.model_mapper.from_model(model) for model in models)

    async def get_active_by_email_and_organization(
        self,
        email: Email,
        organization_id: UUID,
    ) -> Invitation | None:
        stmt = select(self.model).where(
            (self.model.email == email.value)
            & (self.model.organization_id == organization_id)
            & (self.model.deleted_at.is_(None)),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self.model_mapper.from_model(model) if model else None
