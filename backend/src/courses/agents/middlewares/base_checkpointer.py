import logging

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.courses.application.repos import Repository
from src.llm_service import (
    BaseAgentMiddleware,
)

logger = logging.getLogger(__name__)


class BaseSqlCheckpointer[EntityT, SchemaT: BaseModel | None = None](BaseAgentMiddleware):
    def __init__(
        self,
        repo: Repository,
        session: AsyncSession,
    ) -> None:
        """Инициализирует объект и сохраняет зависимости, необходимые для дальнейшей работы."""
        self.repo = repo
        self.session = session

    async def _create(self, entity: EntityT) -> None:
        """Выполняет внутренний шаг `_create`, чтобы скрыть детали реализации от публичного API."""
        await self.repo.create(entity)
        await self.session.commit()

    async def _read(self, *args, **kwargs) -> EntityT | None:
        """Выполняет внутренний шаг `_read`, чтобы скрыть детали реализации от публичного API."""
        return await self.repo.read(*args, **kwargs)

    async def _update(self, *args, **kwargs) -> None:
        """Выполняет внутренний шаг `_update`, чтобы скрыть детали реализации от публичного API."""
        await self.repo.update(*args, **kwargs)
        await self.session.commit()
