from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models, schemas


def _map_schema_to_model(course: schemas.Course) -> models.Course:
    """Маппинг pydantic схемы к sqlalchemy модели"""

    return models.Course(
        id=course.id,
        created_at=course.created_at,
        creator_id=course.creator_id,
        status=course.status,
        image_url=course.image_url,
        title=course.title,
        description=course.description,
        learning_objectives=course.learning_objectives,
        modules=[
            models.Module(
                id=module.id,
                course_id=course.id,
                order=module.order,
                title=module.title,
                description=module.description,
                content_blocks=[
                    content_block.model_dump() for content_block in module.content_blocks
                ],
                assignment=(
                    module.assignment.model_dump() if module.assignment is not None else None
                ),
            )
            for module in course.modules
        ],
        final_assessment=(
            None if course.final_assessment is None else
            course.final_assessment.model_dump()
        )
    )


def add(session: AsyncSession, course: schemas.Course) -> None:
    """Добавление курса в текущую сессию"""

    model = _map_schema_to_model(course)
    session.add(model)


async def get(session: AsyncSession, course_id: UUID) -> schemas.Course | None:
    """Получение курса по его ID"""

    stmt = select(models.Course).where(models.Course.id == course_id)
    result = await session.execute(stmt)
    model = result.scalar_one_or_none()
    return None if model is None else schemas.Course.model_validate(model)


async def refresh(session: AsyncSession, course: schemas.Course) -> schemas.Course:
    """Обновление состояния курса, принимает отредактированный курс и обновляет изменённые поля
    (включая связи  реляции)
    """

    model = _map_schema_to_model(course)
    merged_model = await session.merge(model)
    return schemas.Course.model_validate(merged_model)


async def get_by_creator(session: AsyncSession, creator_id: int) -> list[schemas.Course]:
    """Получение списка курсов по ID их создателя"""

    stmt = select(models.Course).where(models.Course.creator_id == creator_id)
    results = await session.execute(stmt)
    return [schemas.Course.model_validate(model) for model in results.scalars().all()]


async def get_module(session: AsyncSession, module_id: UUID) -> schemas.Module | None:
    """Получение модуля курса по его уникальному ID"""

    stmt = select(models.Module).where(models.Module.id == module_id)
    result = await session.execute(stmt)
    model = result.scalar_one_or_none()
    return None if model is None else schemas.Module.model_validate(model)
