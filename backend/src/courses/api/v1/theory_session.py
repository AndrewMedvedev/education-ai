from typing import Annotated

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.iam.dependencies import require_permissions
from src.iam.dependencies.identity import CurrentIdentity

from ...application.dtos import LessonTheorySessionEditSchema, LessonTheorySessionFilters
from ...dependencies.base import DBSession, TheorySessionRepoDep
from ...domain.entities import LessonTheorySession
from ...domain.permissions.theory_session import READ

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/theory/session", tags=["Theory Session"])


@router.post(
    "/{lesson_id}",
    status_code=status.HTTP_201_CREATED,
)
async def create(
    identity: CurrentIdentity,
    repo: TheorySessionRepoDep,
    session: DBSession,
    lesson_id: UUID,
) -> LessonTheorySession:
    result = await repo.create(LessonTheorySession(lesson_id=lesson_id, user_id=identity.id))
    await session.commit()
    return result


@router.put(
    "/{theory_session_id}",
    status_code=status.HTTP_200_OK,
)
async def update(
    _identity: CurrentIdentity,
    repo: TheorySessionRepoDep,
    session: DBSession,
    theory_session_id: UUID,
    schema: LessonTheorySessionEditSchema,
) -> LessonTheorySession:
    exsists = await repo.exists(uid=theory_session_id)
    if not exsists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metrics not found")
    result = await repo.update(uid=theory_session_id, **schema.model_dump(exclude_none=True))
    await session.commit()
    return result  # pyright: ignore[reportReturnType]


@router.get(
    "/{lesson_id}/{user_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permissions(READ.code))],
)
async def get(
    user_id: UUID,
    repo: TheorySessionRepoDep,
    lesson_id: UUID,
    filters: Annotated[LessonTheorySessionFilters, Query()],
) -> list[LessonTheorySession]:
    return await repo.find(lesson_id=lesson_id, user_id=user_id, filters=filters)
