from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models, schemas


def _to_orm(course: schemas.Course) -> models.Course:
    """Преобразует pydantic схему к sqlalchemy модели"""

    return models.Course(
        id=course.id,
        created_at=course.created_at,
        status=course.status,
        image_url=course.image_url,
        title=course.title,
        description=course.description,
        learning_objectives=course.learning_objectives,
        modules=[
            models.Module(
                course_id=course.id,
                title=module.title,
                description=module.description,
                content_blocks=[
                    content_block.model_dump() for content_block in module.content_blocks
                ],
                assignment=module.assignment.model_dump(),
            )
            for module in course.modules
        ],
        final_assessment=course.final_assessment.model_dump()
    )


def save(session: AsyncSession, course: schemas.Course) -> None:
    model = _to_orm(course)
    session.add(model)


async def get(session: AsyncSession, course_id: UUID) -> schemas.Course | None:
    stmt = select(models.Course).where(models.Course.id == course_id)
    result = await session.execute(stmt)
    model = result.scalar_one_or_none()
    return None if model is None else schemas.Course.model_validate(model)


async def get_by_creator(session: AsyncSession, creator_id: int) -> list[schemas.Course]:
    stmt = select(models.Course).where(models.Course.creator_id == creator_id)
    results = await session.execute(stmt)
    return [schemas.Course.model_validate(model) for model in results.scalars().all()]
