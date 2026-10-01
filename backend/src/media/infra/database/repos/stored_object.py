from sqlalchemy import select

from src.media.domain.entities import StoredObject
from src.shared.infra.database.repos.sqlalchemy import SqlAlchemyRepository

from ..mappers import StoredObjectMapper
from ..models import StoredObjectOrm


class SqlStoredObjectRepository(SqlAlchemyRepository[StoredObject, StoredObjectOrm]):
    model = StoredObjectOrm
    model_mapper = StoredObjectMapper  # pyright: ignore[reportAssignmentType]

    async def get_by_storage_key(self, storage_key: str) -> StoredObject | None:
        """Получает by storage key, чтобы вызывающий код работал через единый интерфейс."""
        stmt = select(self.model).where(self.model.storage_key == storage_key)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.from_model(model)

    async def get_by_hash(self, sha256: str) -> StoredObject | None:
        """Получает by checksum, чтобы вызывающий код работал через единый интерфейс."""
        stmt = select(self.model).where(self.model.sha256 == sha256)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.from_model(model)
