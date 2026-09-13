import logging
from uuid import UUID

from sqlalchemy import select, update

from src.shared.infra.database.repos.sqlalchemy import SqlAlchemyRepository

from ....domain.entities import (
    Chat,
)
from ...mappers import (
    ChatMapper,
)
from ...models import ChatOrm

logger = logging.getLogger(__name__)


class SqlChatRepository(SqlAlchemyRepository[Chat, ChatOrm]):
    model = ChatOrm
    model_mapper = ChatMapper  # type: ignore  # ruff:ignore[blanket-type-ignore]

    async def read(self, user_id: UUID, course_id: UUID, chat_id: UUID) -> Chat | None:
        """Получает существующую запись по идентификатору или заданным параметрам."""
        stmt = select(self.model).where(
            self.model.user_id == user_id,
            self.model.course_id == course_id,
            self.model.id == chat_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.from_model(model)

    async def update(self, chat_id: UUID, user_id: UUID, course_id: UUID, **kwargs) -> Chat | None:
        """Обновляет существующую запись, чтобы сохранить изменённое состояние."""
        stmt = (
            update(self.model)
            .values(**kwargs)
            .where(
                self.model.user_id == user_id,
                self.model.course_id == course_id,
                self.model.id == chat_id,
            )
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.from_model(model)
