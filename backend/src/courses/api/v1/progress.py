from typing import Annotated

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from faststream.rabbit import RabbitQueue

from src.core.rabbit import events_exchange
from src.core.rabbit import router as rabbit_router
from src.iam.dependencies import require_permissions
from src.iam.dependencies.identity import CurrentIdentity
from src.shared.application.dtos import Page, Pagination
from src.shared.dependencies.database import DBSession
from src.shared.utils.time import current_datetime

from ...dependencies.base import (
    CourseProgressRepoDep,
    LessonProgressRepoDep,
    ModuleProgressRepoDep,
)
from ...dependencies.services import (
    CheckCourseAccessDep,
    CheckLessonAccessDep,
    CheckModuleAccessDep,
    LearningProgressServiceDep,
    get_progress,
)
from ...domain.entities import CourseProgress, LessonProgress, ModuleProgress
from ...domain.events import LessonProgressUpdated
from ...domain.permissions.courses import READ, UPDATE

# HTTP-ручки — обычный APIRouter; подписчик событий висит на общем брокере приложения,
# иначе у роутера был бы свой брокер с настройками по умолчанию (guest@localhost).
router = APIRouter(prefix="/progress", tags=["Learning Progress"])
progress_queue = RabbitQueue(
    "learning_progress_updated",
    durable=True,
    routing_key=LessonProgressUpdated.event_type,
)


@router.post(
    "/courses/{course_id}",
    summary="Создать прогресс курса",
    description="Создаёт запись прогресса текущего ученика по указанному курсу. Повторный вызов возвращает существующую запись.",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(READ.code))],
)
async def create_course_progress(
    course_id: UUID,
    identity: CurrentIdentity,
    service: LearningProgressServiceDep,
    check_access: CheckCourseAccessDep,
) -> CourseProgress:
    await check_access(identity=identity, permission=READ, uid=course_id)
    return await service.create_course_progress(identity.id, course_id)


@router.get(
    "/courses/{course_id}",
    summary="Получить прогресс курса",
    description="Возвращает сохранённую запись прогресса текущего ученика по указанному курсу.",
    dependencies=[Depends(require_permissions(READ.code))],
)
async def read_course_progress(
    course_id: UUID,
    identity: CurrentIdentity,
    repo: CourseProgressRepoDep,
) -> CourseProgress:
    return await get_progress(identity.id, course_id, repo)


@router.patch(
    "/courses/{course_id}",
    summary="Обновить прогресс курса",
    status_code=status.HTTP_200_OK,
)
async def update_course_progress(
    course_id: UUID,
    total_lessons: int,
    identity: CurrentIdentity,
    repo: CourseProgressRepoDep,
    service: LearningProgressServiceDep,
    check_access: CheckCourseAccessDep,
) -> CourseProgress:
    await check_access(identity=identity, permission=READ, uid=course_id)
    progress = await get_progress(identity.id, course_id, repo)
    return await service.update_course_progress(progress, total_lessons)


@router.get(
    "/courses/{course_id}/students",
    summary="Получить прогресс учеников курса",
    description="Возвращает сохранённые записи прогресса всех учеников курса. Доступно автору и преподавателям этого курса.",
)
async def get_course_students_progress(
    course_id: UUID,
    identity: CurrentIdentity,
    check_access: CheckCourseAccessDep,
    repo: CourseProgressRepoDep,
    pagination: Annotated[Pagination, Query()],
) -> Page[CourseProgress]:
    # Право course.update есть у любого преподавателя, поэтому проверяем доступ
    # именно к этому курсу: автор или преподаватель курса (политика UPDATE).
    await check_access(identity=identity, permission=UPDATE, uid=course_id)
    return await repo.find_by_course(course_id, pagination)


@router.post(
    "/courses/{course_id}/modules/{module_id}",
    summary="Создать прогресс модуля",
    description="Создаёт запись прогресса текущего ученика по модулю. Прогресс курса создаётся автоматически, если его ещё нет.",
    status_code=status.HTTP_201_CREATED,
)
async def create_module_progress(
    module_id: UUID,
    course_id: UUID,
    identity: CurrentIdentity,
    service: LearningProgressServiceDep,
    check_access: CheckCourseAccessDep,
) -> ModuleProgress:
    await check_access(identity=identity, permission=READ, uid=course_id)
    return await service.create_module_progress(identity.id, course_id, module_id)


@router.get(
    "/modules/{module_id}",
    summary="Получить прогресс модуля",
    description="Возвращает сохранённую запись прогресса текущего ученика по указанному модулю.",
    dependencies=[Depends(require_permissions(READ.code))],
)
async def read_module_progress(
    module_id: UUID,
    identity: CurrentIdentity,
    repo: ModuleProgressRepoDep,
    check_access: CheckModuleAccessDep,
) -> ModuleProgress:
    await check_access(identity=identity, permission=READ, uid=module_id)
    return await get_progress(identity.id, module_id, repo)


@router.post(
    "/module/{module_id}/lessons/{lesson_id}",
    summary="Создать прогресс урока",
    description="Создаёт запись прогресса текущего ученика по уроку. Прогресс модуля и курса создаётся автоматически, если его ещё нет.",
    status_code=status.HTTP_201_CREATED,
)
async def create_lesson_progress(
    lesson_id: UUID,
    module_id: UUID,
    identity: CurrentIdentity,
    service: LearningProgressServiceDep,
    check_access: CheckModuleAccessDep,
) -> LessonProgress:
    await check_access(identity=identity, permission=READ, uid=module_id)
    return await service.create_lesson_progress(identity.id, module_id, lesson_id)


@router.get(
    "/lessons/{lesson_id}",
    summary="Получить прогресс урока",
    description="Возвращает сохранённую запись прогресса текущего ученика по указанному уроку.",
)
async def read_lesson_progress(
    lesson_id: UUID,
    identity: CurrentIdentity,
    repo: LessonProgressRepoDep,
    check_access: CheckLessonAccessDep,
) -> LessonProgress:
    await check_access(identity=identity, permission=READ, uid=lesson_id)
    return await get_progress(identity.id, lesson_id, repo)


@router.patch(
    "/lessons/{lesson_id}",
    summary="Отметить теорию урока пройденной",
    description="Сохраняет время завершения теории. Практика и тест обновляются только после серверной проверки через событие.",
)
async def mark_lesson_theory_completed(
    lesson_id: UUID,
    identity: CurrentIdentity,
    repo: LessonProgressRepoDep,
    service: LearningProgressServiceDep,
    check_access: CheckLessonAccessDep,
) -> LessonProgress:
    await check_access(identity=identity, permission=READ, uid=lesson_id)
    progress = await get_progress(identity.id, lesson_id, repo)
    return await service.update(
        progress,
        theory_completed_at=current_datetime(),
    )


@rabbit_router.subscriber(progress_queue, events_exchange)
async def on_lesson_progress_updated(
    event: LessonProgressUpdated,
    repo: LessonProgressRepoDep,
    session: DBSession,
) -> None:
    await repo.update_from_event(event)
    await session.commit()
