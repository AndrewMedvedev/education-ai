from uuid import uuid4

import pytest

from src.courses.domain.enums import CourseStatus, DifficultyLevel
from src.courses.infra.database.repos.module import SqlModuleRepository
from src.courses.infra.models import CourseOrm, LessonOrm, ModuleOrm


@pytest.mark.asyncio
async def test_get_by_id_basic_info_returns_module_with_lessons(session):
    """Возвращает краткие данные модуля вместе с его уроками из базы данных."""
    course = CourseOrm(
        id=uuid4(),
        creator_id=uuid4(),
        title="Python",
        description="Python course",
        difficulty=DifficultyLevel.BEGINNER,
        tags=["python"],
        status=CourseStatus.PUBLISHED,
    )
    module_id = uuid4()
    module = ModuleOrm(
        id=module_id,
        course_id=course.id,
        title="Basics",
        description="Python basics",
        order=1,
        learning_objectives=["Learn syntax"],
    )
    lesson = LessonOrm(
        id=uuid4(),
        module_id=module_id,
        title="Variables",
        description="Python variables",
        order=1,
        learning_objectives=["Use variables"],
        content_blocks=[],
    )
    session.add_all([course, module, lesson])
    await session.flush()
    repository = SqlModuleRepository(session)

    basic_info = await repository.get_by_id_basic_info(module_id)

    assert basic_info is not None
    assert basic_info.id == module_id
    assert basic_info.title == "Basics"
    assert basic_info.lessons[0].id == lesson.id
    assert basic_info.lessons[0].title == "Variables"


@pytest.mark.asyncio
async def test_get_by_id_basic_info_returns_lessons_in_module_order(session):
    """Возвращает уроки модуля в порядке их позиции в программе."""
    module = ModuleOrm(
        id=uuid4(),
        course_id=None,
        title="Basics",
        description="Python basics",
        order=1,
    )
    later_lesson = LessonOrm(
        id=uuid4(),
        module_id=module.id,
        title="Loops",
        description="Python loops",
        order=2,
        content_blocks=[],
    )
    first_lesson = LessonOrm(
        id=uuid4(),
        module_id=module.id,
        title="Variables",
        description="Python variables",
        order=1,
        content_blocks=[],
    )
    session.add_all([module, later_lesson, first_lesson])
    await session.flush()
    repository = SqlModuleRepository(session)

    basic_info = await repository.get_by_id_basic_info(module.id)

    assert basic_info is not None
    assert [lesson.id for lesson in basic_info.lessons] == [first_lesson.id, later_lesson.id]


@pytest.mark.asyncio
async def test_get_by_id_basic_info_returns_none_for_unknown_module(session):
    """Не возвращает базовые данные для отсутствующего модуля."""
    repository = SqlModuleRepository(session)

    assert await repository.get_by_id_basic_info(uuid4()) is None


@pytest.mark.asyncio
async def test_get_by_id_basic_info_returns_empty_lessons_for_new_module(session):
    """Возвращает пустой список уроков для модуля без наполнения."""
    module = ModuleOrm(
        id=uuid4(),
        course_id=None,
        title="Basics",
        description="Python basics",
        order=1,
    )
    session.add(module)
    await session.flush()
    repository = SqlModuleRepository(session)

    basic_info = await repository.get_by_id_basic_info(module.id)

    assert basic_info is not None
    assert basic_info.lessons == []


@pytest.mark.asyncio
async def test_assign_course_links_module_to_course(session):
    """Привязывает модуль к указанному курсу в базе данных."""
    course = CourseOrm(
        id=uuid4(),
        creator_id=uuid4(),
        title="Python",
        description="Python course",
        difficulty=DifficultyLevel.BEGINNER,
        tags=["python"],
        status=CourseStatus.DRAFT,
    )
    module = ModuleOrm(
        id=uuid4(),
        course_id=None,
        title="Basics",
        description="Python basics",
        order=1,
    )
    session.add_all([course, module])
    await session.flush()
    repository = SqlModuleRepository(session)

    await repository.assign_course(module.id, course.id)
    await session.refresh(module)

    assert module.course_id == course.id
