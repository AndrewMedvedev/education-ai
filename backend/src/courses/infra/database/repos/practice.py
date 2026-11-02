from typing import Any

import hashlib
import logging
from uuid import UUID

from sqlalchemy import or_, select, text

from src.courses.domain.entities import (
    Practice,
)
from src.shared.infra.database.repos.sqlalchemy import SqlAlchemyRepository

from ..mappers import (
    PracticeMapper,
)
from ..models import PracticeOrm

logger = logging.getLogger(__name__)


class SqlPracticeRepository(SqlAlchemyRepository[Practice, PracticeOrm]):
    model = PracticeOrm
    model_mapper = PracticeMapper  # pyright: ignore[reportAssignmentType]

    async def read(self, user_id: UUID, module_id: UUID, lesson_id: UUID) -> Practice | None:
        """Получает существующую запись по идентификатору или заданным параметрам."""
        stmt = select(self.model).where(
            self.model.user_id == user_id,
            self.model.module_id == module_id,
            self.model.lesson_id == lesson_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.from_model(model)

    async def lock_file_upload(self, user_id: UUID, module_id: UUID, lesson_id: UUID) -> None:
        await self._lock_assessment("file-upload", user_id, module_id, lesson_id)

    async def lock_knowledge_test(self, user_id: UUID, module_id: UUID, lesson_id: UUID) -> None:
        await self._lock_assessment("knowledge-test", user_id, module_id, lesson_id)

    async def _lock_assessment(self, kind: str, user_id: UUID, module_id: UUID, lesson_id: UUID) -> None:
        # Stable across API workers; transaction-scoped so failures release the lock too.
        key = f"{kind}:{user_id}:{module_id}:{lesson_id}".encode()
        lock_id = int.from_bytes(hashlib.sha256(key).digest()[:8], signed=True)
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_id)"),
            {"lock_id": lock_id},
        )

    async def read_latest_file_upload(
        self,
        user_id: UUID,
        module_id: UUID,
        lesson_id: UUID,
    ) -> Practice | None:
        stmt = (
            select(self.model)
            .where(
                self.model.user_id == user_id,
                self.model.module_id == module_id,
                self.model.lesson_id == lesson_id,
                or_(
                    self.model.practice[0]["assignment_type"].astext == "file_upload",
                    self.model.practice["practice"]["assignment_type"].astext == "file_upload",
                ),
            )
            .order_by(self.model.created_at.desc(), self.model.id.desc())
            .limit(1)
            .execution_options(populate_existing=True)
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return None if model is None else self.model_mapper.from_model(model)

    async def read_latest_knowledge_test(
        self, user_id: UUID, module_id: UUID, lesson_id: UUID
    ) -> Practice | None:
        stmt = (
            select(self.model)
            .where(
                self.model.user_id == user_id,
                self.model.module_id == module_id,
                self.model.lesson_id == lesson_id,
                or_(
                    self.model.practice[0]["test_type"].astext.in_(
                        ["multiple_choice", "detailed_answer"]
                    ),
                    self.model.practice["practice"]["test_type"].astext.in_(
                        ["multiple_choice", "detailed_answer"]
                    ),
                ),
            )
            .order_by(self.model.created_at.desc(), self.model.id.desc())
            .limit(1)
            .execution_options(populate_existing=True)
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return None if model is None else self.model_mapper.from_model(model)

    async def read_by_module(self, user_id: UUID, module_id: UUID) -> list[dict[str, Any]]:
        """Получает практики пользователя внутри модуля без служебных полей."""
        stmt = (
            select(
                self.model.practice,
                self.model.status,
            )
            .where(
                self.model.user_id == user_id,
                self.model.module_id == module_id,
            )
            .order_by(self.model.lesson_id)
        )

        result = await self._session.execute(stmt)

        return [
            {
                "practice": row.practice,
                "status": row.status,
            }
            for row in result.all()
        ]
