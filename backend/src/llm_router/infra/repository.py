from uuid import UUID

from sqlalchemy import func, select

from src.shared.application.dtos import Page, Pagination
from src.shared.infra.database.mappers import ModelMapper
from src.shared.infra.database.repos import SqlAlchemyRepository

from ..domain.dataclass import AIModel, LLMInvocation
from .models import AIModelOrm, LLMInvocationOrm


class AIModelMapper(ModelMapper[AIModel, AIModelOrm]):
    @staticmethod
    def from_model(model: AIModelOrm) -> AIModel:
        """Преобразует данные в доменную сущность, чтобы передать их в нужный слой приложения."""
        return AIModel(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            name=model.name,
            complexity=model.complexity,
            description=model.description,
            context=model.context,
        )

    @staticmethod
    def to_model(entity: AIModel) -> AIModelOrm:
        return AIModelOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            name=entity.name,
            complexity=entity.complexity,
            description=entity.description,
            context=entity.context,
        )


class SqlAIModelRepository(SqlAlchemyRepository[AIModel, AIModelOrm]):
    model = AIModelOrm
    model_mapper = AIModelMapper  # type: ignore  # ruff: ignore[blanket-type-ignore]

    async def read_fields(self, params: Pagination) -> Page:
        # 1. Основной запрос — выбираем только нужные поля, без служебных
        stmt = select(
            self.model.name,
            self.model.complexity,
            self.model.description,
            self.model.context,
        ).order_by(self.model.created_at.desc())

        # 2. Запрос для подсчёта общего количества записей
        count_stmt = select(func.count()).select_from(stmt.subquery())

        # 3. Запрос для пагинации записей
        paginate_stmt = stmt.offset(params.offset).limit(params.size)

        # 4. Выполнение запросов
        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one()
        if total == 0:
            return Page.create([], total, params.page, params.size)

        results = await self._session.execute(paginate_stmt)
        rows = results.mappings().all()

        # 5. Формирование результата — уже словари только с name/description/context
        return Page.create(
            items=[dict(row) for row in rows],
            total=total,
            page=params.page,
            size=params.size,
        )

    async def get_by_id(self, model_id: UUID) -> AIModel | None:
        """Получает by id, чтобы вызывающий код работал через единый интерфейс."""
        stmt = select(self.model).where(self.model.id == model_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.from_model(model)  # type: ignore  # ruff: ignore[blanket-type-ignore]


class LLMInvocationMapper(ModelMapper[LLMInvocation, LLMInvocationOrm]):
    @staticmethod
    def from_model(model: LLMInvocationOrm) -> LLMInvocation:
        """Преобразует запись мониторинга в доменную сущность."""
        return LLMInvocation(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            request_id=model.request_id,
            model=model.model,
            total_tokens=model.total_tokens,
            request=model.request,
            response=model.response,
            duration_ms=model.duration_ms,
            status=model.status,
            error=model.error,
        )

    @staticmethod
    def to_model(entity: LLMInvocation) -> LLMInvocationOrm:
        """Преобразует доменную сущность мониторинга в ORM-модель."""
        return LLMInvocationOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
            request_id=entity.request_id,
            model=entity.model,
            total_tokens=entity.total_tokens,
            request=entity.request,
            response=entity.response,
            duration_ms=entity.duration_ms,
            status=entity.status,
            error=entity.error,
        )


class SqlLLMInvocationRepository(SqlAlchemyRepository[LLMInvocation, LLMInvocationOrm]):
    model = LLMInvocationOrm
    model_mapper = LLMInvocationMapper  # type: ignore  # ruff: ignore[blanket-type-ignore]
