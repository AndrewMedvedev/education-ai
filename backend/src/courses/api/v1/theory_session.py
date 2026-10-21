from typing import Annotated

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.courses.application.dtos import LessonTheorySessionEditSchema, LessonTheorySessionFilters
from src.courses.dependencies.base import DBSession, TheorySessionRepoDep
from src.courses.dependencies.services import CheckLessonAccessDep
from src.courses.domain.entities import LessonTheorySession
from src.courses.domain.permissions.courses import READ as READ_COURSE
from src.courses.domain.permissions.theory_session import READ
from src.iam.dependencies import require_permissions
from src.iam.dependencies.identity import CurrentIdentity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/theory-sessions", tags=["Theory Sessions"])


@router.post(
    "/{lesson_id}",
    summary="Создать сессию изучения теории",
    description="Создаёт сессию изучения теории для текущего пользователя и указанного урока.",
    status_code=status.HTTP_201_CREATED,
)
async def create(
    identity: CurrentIdentity,
    check_access: CheckLessonAccessDep,
    repo: TheorySessionRepoDep,
    session: DBSession,
    lesson_id: UUID,
) -> LessonTheorySession:
    await check_access(
        identity=identity,
        permission=READ_COURSE,
        uid=lesson_id,
    )
    result = await repo.create(LessonTheorySession(lesson_id=lesson_id, user_id=identity.id))
    await session.commit()
    return result


@router.put(
    "/{theory_session_id}",
    summary="Обновить сессию изучения теории",
    description="Сохраняет переданные метрики сессии: активное время, глубину прокрутки и время завершения.",
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
    "/{lesson_id}/users/{user_id}",
    summary="Получить сессии изучения теории пользователя",
    description="Возвращает историю сессий изучения указанного урока выбранным пользователем с учётом фильтров по дате.",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permissions(READ.code))],
)
async def get(
    user_id: UUID,
    repo: TheorySessionRepoDep,
    check_access: CheckLessonAccessDep,
    identity: CurrentIdentity,
    lesson_id: UUID,
    filters: Annotated[LessonTheorySessionFilters, Query()],
) -> list[LessonTheorySession]:
    await check_access(
        identity=identity,
        permission=READ,
        uid=lesson_id,
    )
    return await repo.find(lesson_id=lesson_id, user_id=user_id, filters=filters)
