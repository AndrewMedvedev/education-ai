from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.courses.application.services.progress import LearningProgressService
from src.courses.domain.events import LessonProgressUpdated, LessonProgressUpdate
from src.courses.infra.mappers import CourseProgressMapper, LessonProgressMapper
from src.courses.infra.database.repos.course_progress import SqlCourseProgressRepository
from src.courses.infra.database.repos.lesson_progress import SqlLessonProgressRepository
from src.courses.infra.database.repos.module_progress import SqlModuleProgressRepository
from src.courses.infra.models import CourseProgressOrm, LessonProgressOrm, ModuleProgressOrm
from src.shared.application.dtos import Pagination


@pytest.mark.asyncio
async def test_read_by_returns_saved_user_course_progress(session):
    """Возвращает сохранённый прогресс конкретного пользователя по курсу."""
    user_id = uuid4()
    course_id = uuid4()
    course_progress = CourseProgressOrm(
        user_id=user_id,
        course_id=course_id,
        progress_percent=25,
    )
    session.add(course_progress)
    await session.flush()
    repository = SqlCourseProgressRepository(session)

    progress = await repository.get_by_user(user_id, course_id)

    assert progress is not None
    assert progress.id == course_progress.id
    assert progress.progress_percent == 25


@pytest.mark.asyncio
async def test_read_by_does_not_return_other_user_course_progress(session):
    """Не возвращает progress курса пользователю, которому он не принадлежит."""
    course_progress = CourseProgressOrm(
        id=uuid4(),
        user_id=uuid4(),
        course_id=uuid4(),
    )
    session.add(course_progress)
    await session.flush()
    repository = SqlCourseProgressRepository(session)

    progress = await repository.get_by_user(uuid4(), course_progress.course_id)

    assert progress is None


@pytest.mark.asyncio
async def test_read_by_does_not_return_other_user_module_progress(session):
    """Не возвращает progress модуля пользователю, которому он не принадлежит."""
    module_id = uuid4()
    course_progress = CourseProgressOrm(
        id=uuid4(),
        user_id=uuid4(),
        course_id=uuid4(),
    )
    module_progress = ModuleProgressOrm(
        id=uuid4(),
        course_progress_id=course_progress.id,
        module_id=module_id,
    )
    session.add_all([course_progress, module_progress])
    await session.flush()
    repository = SqlModuleProgressRepository(session)

    progress = await repository.get_by_user(uuid4(), module_id)

    assert progress is None


@pytest.mark.asyncio
async def test_count_completed_lessons_ignores_incomplete_lessons(session):
    """Считает только уроки с завершённой теорией, практикой и тестом."""
    course_progress_id = uuid4()
    module_progress_id = uuid4()
    course_progress = CourseProgressOrm(
        id=course_progress_id,
        user_id=uuid4(),
        course_id=uuid4(),
    )
    module_progress = ModuleProgressOrm(
        id=module_progress_id,
        course_progress_id=course_progress_id,
        module_id=uuid4(),
    )
    completed_at = datetime.now(timezone.utc)
    completed_lesson = LessonProgressOrm(
        module_progress_id=module_progress_id,
        lesson_id=uuid4(),
        theory_completed_at=completed_at,
        practice_completed_at=completed_at,
        test_completed_at=completed_at,
    )
    incomplete_lesson = LessonProgressOrm(
        module_progress_id=module_progress_id,
        lesson_id=uuid4(),
        theory_completed_at=completed_at,
    )
    session.add_all([course_progress, module_progress, completed_lesson, incomplete_lesson])
    await session.flush()
    repository = SqlCourseProgressRepository(session)

    completed_lessons = await repository.count_completed_lessons(course_progress_id)

    assert completed_lessons == 1


@pytest.mark.asyncio
async def test_count_completed_lessons_returns_zero_without_lessons(session):
    """Возвращает ноль, когда для курса нет завершённых уроков."""
    course_progress = CourseProgressOrm(
        id=uuid4(),
        user_id=uuid4(),
        course_id=uuid4(),
    )
    session.add(course_progress)
    await session.flush()
    repository = SqlCourseProgressRepository(session)

    completed_lessons = await repository.count_completed_lessons(course_progress.id)

    assert completed_lessons == 0


@pytest.mark.asyncio
async def test_update_course_progress_rounds_completed_lesson_fraction(session):
    """Округляет процент, когда полностью завершен один из трех уроков."""
    course_progress = CourseProgressOrm(id=uuid4(), user_id=uuid4(), course_id=uuid4())
    module_progress = ModuleProgressOrm(
        id=uuid4(),
        course_progress_id=course_progress.id,
        module_id=uuid4(),
    )
    completed_at = datetime.now(timezone.utc)
    completed_lesson = LessonProgressOrm(
        module_progress_id=module_progress.id,
        lesson_id=uuid4(),
        theory_completed_at=completed_at,
        practice_completed_at=completed_at,
        test_completed_at=completed_at,
    )
    incomplete_lessons = [
        LessonProgressOrm(module_progress_id=module_progress.id, lesson_id=uuid4())
        for _ in range(2)
    ]
    session.add_all([course_progress, module_progress, completed_lesson, *incomplete_lessons])
    await session.flush()
    service = LearningProgressService(
        progress_repo=SqlLessonProgressRepository(session),
        course_progress_repo=SqlCourseProgressRepository(session),
        module_progress_repo=SqlModuleProgressRepository(session),
        session=session,
    )

    progress = await service.update_course_progress(
        CourseProgressMapper.from_model(course_progress), total_lessons=3
    )

    assert progress.progress_percent == 33.33


@pytest.mark.asyncio
async def test_update_from_event_updates_only_target_user_progress(session):
    """Обновляет прогресс урока только пользователя из события."""
    user_id = uuid4()
    lesson_id = uuid4()
    target_course_progress = CourseProgressOrm(
        id=uuid4(),
        user_id=user_id,
        course_id=uuid4(),
    )
    other_course_progress = CourseProgressOrm(
        id=uuid4(),
        user_id=uuid4(),
        course_id=uuid4(),
    )
    target_module_progress = ModuleProgressOrm(
        id=uuid4(),
        course_progress_id=target_course_progress.id,
        module_id=uuid4(),
    )
    other_module_progress = ModuleProgressOrm(
        id=uuid4(),
        course_progress_id=other_course_progress.id,
        module_id=uuid4(),
    )
    target_lesson_progress = LessonProgressOrm(
        id=uuid4(),
        module_progress_id=target_module_progress.id,
        lesson_id=lesson_id,
    )
    other_lesson_progress = LessonProgressOrm(
        id=uuid4(),
        module_progress_id=other_module_progress.id,
        lesson_id=lesson_id,
    )
    session.add_all(
        [
            target_course_progress,
            other_course_progress,
            target_module_progress,
            other_module_progress,
            target_lesson_progress,
            other_lesson_progress,
        ]
    )
    await session.flush()
    completed_at = datetime.now(timezone.utc)
    event = LessonProgressUpdated(
        user_id=user_id,
        lesson_id=lesson_id,
        progress=LessonProgressUpdate(practice_completed_at=completed_at),
    )
    repository = SqlLessonProgressRepository(session)

    await repository.update_from_event(event)
    await session.refresh(target_lesson_progress)
    await session.refresh(other_lesson_progress)

    assert target_lesson_progress.practice_completed_at == completed_at
    assert other_lesson_progress.practice_completed_at is None


@pytest.mark.asyncio
async def test_update_from_event_preserves_completed_progress_parts(session):
    """Не затирает уже сохранённую часть прогресса при обновлении из события."""
    course_progress = CourseProgressOrm(
        id=uuid4(),
        user_id=uuid4(),
        course_id=uuid4(),
    )
    module_progress = ModuleProgressOrm(
        id=uuid4(),
        course_progress_id=course_progress.id,
        module_id=uuid4(),
    )
    practice_completed_at = datetime.now(timezone.utc)
    lesson_progress = LessonProgressOrm(
        module_progress_id=module_progress.id,
        lesson_id=uuid4(),
        practice_completed_at=practice_completed_at,
    )
    session.add_all([course_progress, module_progress, lesson_progress])
    await session.flush()
    test_completed_at = datetime.now(timezone.utc)
    event = LessonProgressUpdated(
        user_id=course_progress.user_id,
        lesson_id=lesson_progress.lesson_id,
        progress=LessonProgressUpdate(test_completed_at=test_completed_at),
    )
    repository = SqlLessonProgressRepository(session)

    await repository.update_from_event(event)
    await session.refresh(lesson_progress)

    assert lesson_progress.practice_completed_at == practice_completed_at
    assert lesson_progress.test_completed_at == test_completed_at


@pytest.mark.asyncio
async def test_update_from_event_does_not_create_unknown_lesson_progress(session):
    """Не создает progress, если событие пришло для отсутствующего урока пользователя."""
    event = LessonProgressUpdated(
        user_id=uuid4(),
        lesson_id=uuid4(),
        progress=LessonProgressUpdate(theory_completed_at=datetime.now(timezone.utc)),
    )
    repository = SqlLessonProgressRepository(session)

    await repository.update_from_event(event)

    assert await repository.get_by_user(event.user_id, event.lesson_id) is None


@pytest.mark.asyncio
async def test_update_course_progress_saves_calculated_percent(session):
    """Сохраняет процент курса, рассчитанный по завершённым урокам."""
    user_id = uuid4()
    course_id = uuid4()
    course_progress = CourseProgressOrm(id=uuid4(), user_id=user_id, course_id=course_id)
    module_progress = ModuleProgressOrm(
        id=uuid4(),
        course_progress_id=course_progress.id,
        module_id=uuid4(),
    )
    completed_at = datetime.now(timezone.utc)
    completed_lesson = LessonProgressOrm(
        module_progress_id=module_progress.id,
        lesson_id=uuid4(),
        theory_completed_at=completed_at,
        practice_completed_at=completed_at,
        test_completed_at=completed_at,
    )
    incomplete_lesson = LessonProgressOrm(
        module_progress_id=module_progress.id,
        lesson_id=uuid4(),
    )
    session.add_all([course_progress, module_progress, completed_lesson, incomplete_lesson])
    await session.flush()
    service = LearningProgressService(
        progress_repo=SqlLessonProgressRepository(session),
        course_progress_repo=SqlCourseProgressRepository(session),
        module_progress_repo=SqlModuleProgressRepository(session),
        session=session,
    )

    progress = await service.update_course_progress(CourseProgressMapper.from_model(course_progress), total_lessons=2)

    assert progress is not None
    assert progress.progress_percent == 50


@pytest.mark.asyncio
async def test_create_progress_tree_links_course_module_and_lesson(session):
    """Создаёт связанные записи прогресса курса, модуля и урока."""
    user_id = uuid4()
    course_id = uuid4()
    module_id = uuid4()
    lesson_id = uuid4()
    course_progress_repository = SqlCourseProgressRepository(session)
    module_progress_repository = SqlModuleProgressRepository(session)
    lesson_progress_repository = SqlLessonProgressRepository(session)
    service = LearningProgressService(
        progress_repo=lesson_progress_repository,
        course_progress_repo=course_progress_repository,
        module_progress_repo=module_progress_repository,
        session=session,
    )

    course_progress = await service.create_course_progress(user_id, course_id)
    module_progress = await service.create_module_progress(user_id, course_id, module_id)
    lesson_progress = await service.create_lesson_progress(user_id, module_id, lesson_id)

    assert module_progress.course_progress_id == course_progress.id
    assert lesson_progress.module_progress_id == module_progress.id


@pytest.mark.asyncio
async def test_update_marks_theory_completed_only_for_target_user(session):
    """Сохраняет завершение теории только в прогрессе текущего пользователя."""
    user_id = uuid4()
    lesson_id = uuid4()
    target_course_progress = CourseProgressOrm(
        id=uuid4(),
        user_id=user_id,
        course_id=uuid4(),
    )
    other_course_progress = CourseProgressOrm(
        id=uuid4(),
        user_id=uuid4(),
        course_id=uuid4(),
    )
    target_module_progress = ModuleProgressOrm(
        id=uuid4(),
        course_progress_id=target_course_progress.id,
        module_id=uuid4(),
    )
    other_module_progress = ModuleProgressOrm(
        id=uuid4(),
        course_progress_id=other_course_progress.id,
        module_id=uuid4(),
    )
    target_lesson_progress = LessonProgressOrm(
        id=uuid4(),
        module_progress_id=target_module_progress.id,
        lesson_id=lesson_id,
    )
    other_lesson_progress = LessonProgressOrm(
        id=uuid4(),
        module_progress_id=other_module_progress.id,
        lesson_id=lesson_id,
    )
    session.add_all(
        [
            target_course_progress,
            other_course_progress,
            target_module_progress,
            other_module_progress,
            target_lesson_progress,
            other_lesson_progress,
        ]
    )
    await session.flush()
    service = LearningProgressService(
        progress_repo=SqlLessonProgressRepository(session),
        course_progress_repo=SqlCourseProgressRepository(session),
        module_progress_repo=SqlModuleProgressRepository(session),
        session=session,
    )
    completed_at = datetime.now(timezone.utc)

    progress = await service.update(LessonProgressMapper.from_model(target_lesson_progress), completed_at)
    await session.refresh(target_lesson_progress)
    await session.refresh(other_lesson_progress)

    assert progress.theory_completed_at == completed_at
    assert target_lesson_progress.theory_completed_at == completed_at
    assert other_lesson_progress.theory_completed_at is None


@pytest.mark.asyncio
async def test_find_by_course_returns_paginated_student_progress(session):
    """Возвращает преподавателю страницу progress учеников указанного курса."""
    course_id = uuid4()
    first_progress = CourseProgressOrm(
        id=uuid4(),
        user_id=uuid4(),
        course_id=course_id,
        progress_percent=25,
    )
    second_progress = CourseProgressOrm(
        id=uuid4(),
        user_id=uuid4(),
        course_id=course_id,
        progress_percent=50,
    )
    other_course_progress = CourseProgressOrm(
        id=uuid4(),
        user_id=uuid4(),
        course_id=uuid4(),
        progress_percent=100,
    )
    session.add_all([first_progress, second_progress, other_course_progress])
    await session.flush()
    repository = SqlCourseProgressRepository(session)

    page = await repository.find_by_course(course_id, Pagination(page=1, size=1))

    assert page.total == 2
    assert len(page.items) == 1
    assert page.items[0].id in {first_progress.id, second_progress.id}
