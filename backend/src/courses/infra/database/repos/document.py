import logging
from uuid import UUID

from sqlalchemy import select

from src.shared.infra.database.repos.sqlalchemy import SqlAlchemyRepository

from ....domain.entities import (
    Document,
)
from ....domain.vo import DocumentNodeType
from ...mappers import (
    DocumentMapper,
)
from ...models import DocumentOrm

logger = logging.getLogger(__name__)


class SqlDocumentRepository(SqlAlchemyRepository[Document, DocumentOrm]):
    model = DocumentOrm
    model_mapper = DocumentMapper  # type: ignore  # ruff:ignore[blanket-type-ignore]

    # ── 1. Все оглавления (TOC) владельца ─────────────────────────────────────────
    async def get_tocs(self, owner_id: UUID) -> list[Document]:
        """Возвращает все оглавления документов пользователя."""

        stmt = await self._session.execute(
            select(self.model).where(
                self.model.owner_id == owner_id,
                self.model.node_type == DocumentNodeType.TOC,
            )
        )

        return [self.model_mapper.from_model(model) for model in stmt.scalars().all()]

    # ── 2. Все заголовки (HEADING) конкретного TOC ────────────────────────────────
    async def get_headings(
        self,
        owner_id: UUID,
        toc_id: UUID,
    ) -> list[Document]:
        stmt = await self._session.execute(
            select(self.model).where(
                self.model.owner_id == owner_id,
                self.model.parent_node_id == toc_id,
                self.model.node_type == DocumentNodeType.HEADING,
            )
        )

        return [self.model_mapper.from_model(model) for model in stmt.scalars().all()]

    # ── 3. Текст (TEXT) конкретного заголовка ─────────────────────────────────────
    async def get_text(
        self,
        owner_id: UUID,
        heading_id: UUID,
    ) -> Document | None:
        stmt = await self._session.execute(
            select(self.model).where(
                self.model.owner_id == owner_id,
                self.model.parent_node_id == heading_id,
                self.model.node_type == DocumentNodeType.TEXT,
            )
        )

        model = stmt.scalar_one_or_none()

        if model is None:
            return None

        return self.model_mapper.from_model(model)
