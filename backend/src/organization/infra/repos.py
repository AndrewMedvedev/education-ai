from sqlalchemy import select

from src.shared.infra.database.repos.sqlalchemy import ModelMapper, SqlAlchemyRepository

from ..domain.entities import Organization
from .models import OrganizationOrm


class OrganizationMapper(ModelMapper[Organization, OrganizationOrm]):
    @staticmethod
    def from_model(model: OrganizationOrm) -> Organization:
        return Organization(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            name=model.name,
            email=model.email,
            description=model.description,
            is_active=model.is_active,
        )

    @staticmethod
    def to_model(entity: Organization) -> OrganizationOrm:
        return OrganizationOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            name=entity.name,
            email=entity.email,
            description=entity.description,
            is_active=entity.is_active,
        )


class SqlOrganizationRepository(SqlAlchemyRepository[Organization, OrganizationOrm]):
    model = OrganizationOrm
    model_mapper = OrganizationMapper  # pyright: ignore[reportAssignmentType]

    async def get_by_email(self, email: str) -> Organization | None:
        stmt = select(self.model).where(self.model.email == email)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.from_model(model)
