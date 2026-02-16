from uuid import UUID

from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models, schemas


async def add_submission(session: AsyncSession, submission: schemas.Submission) -> None:
    stmt = insert(models.Submission).values(**submission.model_dump())
    await session.execute(stmt)


async def get_submissions(session: AsyncSession, practice_id: UUID) -> list[schemas.Submission]:
    stmt = select(models.Submission).where(models.Submission.practice_id == practice_id)
    results = await session.execute(stmt)
    return [schemas.Submission.model_validate(model) for model in results.scalars().all()]


async def get_practice_progress(
    session: AsyncSession, practice_id: UUID
) -> schemas.PracticeProgress | None:
    stmt = (
        select(
            func.max(models.Submission.score).label("best_score"),
            func.count(models.Submission.id).label("attempts"),
            func.bool_or(models.Submission.is_passed).label("is_passed"),
            (
                func.max(models.Submission.id)
                .filter(models.Submission.score == func.max(models.Submission.score))
                .label("best_submission_id"),
            )
        )
        .where(models.Submission.practice_id == practice_id)
        .group_by(models.Submission.practice_id)
    )
    result = await session.execute(stmt)
    row = result.one_or_none()
    if row is None:
        practice = await session.get(models.StudentPractice, practice_id)
        if practice is None:
            return None
        return schemas.PracticeProgress(
            practice_id=practice_id,
            submission_id=None,
            user_id=practice.user_id,
            best_score=0.0,
            attempts=0,
        )
    practice = await session.get(models.StudentPractice, practice_id)
    return schemas.PracticeProgress(
        practice_id=practice_id,
        submission_id=row.best_submission_id,
        user_id=practice.user_id,
        best_score=row.best_score or 0.0,
        attempts=row.attempts or 0,
        is_passed=row.is_passed
    )
