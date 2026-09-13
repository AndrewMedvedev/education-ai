from sqlalchemy import select

from src.iam.domain.entities import Role
from src.iam.infra.database.mappers import RoleMapper
from src.iam.infra.database.models import RoleOrm
from src.shared.infra.database import SqlAlchemyRepository


class SqlRoleRepository(SqlAlchemyRepository[Role, RoleOrm]):
    model = RoleOrm
    model_mapper = RoleMapper

    async def get_by_code(self, code: str) -> Role | None:
        stmt = select(self.model).where(
            (self.model.code == code) & (self.model.deleted_at.is_(None)),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self.model_mapper.from_model(model) if model else None
