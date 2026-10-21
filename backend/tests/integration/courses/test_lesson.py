from uuid import uuid4

import pytest

from src.courses.domain.entities import TextBlock
from src.courses.infra.database.repos.lesson import SqlLessonRepository
from src.courses.infra.models import LessonOrm, ModuleOrm


@pytest.mark.asyncio
async def test_replace_content_block_updates_only_selected_block(session):
    """Заменяет указанный блок контента урока в PostgreSQL."""
    lesson_id = uuid4()
    lesson = LessonOrm(
        id=lesson_id,
        module_id=None,
        title="Variables",
        description="Python variables",
        order=1,
        content_blocks=[
            TextBlock(md_content="First block"),
            TextBlock(md_content="Old block"),
        ],
    )
    session.add(lesson)
    await session.flush()
    repository = SqlLessonRepository(session)

    await repository.replace_content_block(
        lesson_id,
        block_index=1,
        new_block={"content_type": "text", "md_content": "Updated block", "ai_generated": True},
    )
    await session.flush()

    content_blocks = await repository.get_content_blocks_by_id(lesson_id)

    assert content_blocks is not None
    assert content_blocks[0].md_content == "First block"
    assert content_blocks[1].md_content == "Updated block"


@pytest.mark.asyncio
async def test_get_by_id_basic_info_returns_lesson_data(session):
    """Возвращает краткие данные урока из PostgreSQL."""
    lesson = LessonOrm(
        id=uuid4(),
        module_id=None,
        title="Variables",
        description="Python variables",
        order=1,
        learning_objectives=["Use variables"],
        estimated_time_minutes=30,
        content_blocks=[],
    )
    session.add(lesson)
    await session.flush()
    repository = SqlLessonRepository(session)

    basic_info = await repository.get_by_id_basic_info(lesson.id)

    assert basic_info is not None
    assert basic_info.id == lesson.id
    assert basic_info.estimated_time_minutes == 30


@pytest.mark.asyncio
async def test_lesson_repository_returns_none_for_unknown_lesson(session):
    """Не возвращает описание или контент несуществующего урока."""
    repository = SqlLessonRepository(session)
    lesson_id = uuid4()

    assert await repository.get_by_id_basic_info(lesson_id) is None
    assert await repository.get_content_blocks_by_id(lesson_id) is None


@pytest.mark.asyncio
async def test_assign_module_updates_only_selected_lesson(session):
    """Не меняет привязку другого урока при переносе выбранного урока в модуль."""
    target_module = ModuleOrm(
        id=uuid4(),
        course_id=None,
        title="Target module",
        description="Target description",
        order=1,
    )
    other_module = ModuleOrm(
        id=uuid4(),
        course_id=None,
        title="Other module",
        description="Other description",
        order=2,
    )
    target_lesson = LessonOrm(
        id=uuid4(),
        module_id=None,
        title="Target lesson",
        description="Target description",
        order=1,
        content_blocks=[],
    )
    other_lesson = LessonOrm(
        id=uuid4(),
        module_id=other_module.id,
        title="Other lesson",
        description="Other description",
        order=1,
        content_blocks=[],
    )
    session.add_all([target_module, other_module, target_lesson, other_lesson])
    await session.flush()
    repository = SqlLessonRepository(session)

    await repository.assign_module(target_lesson.id, target_module.id)
    await session.refresh(target_lesson)
    await session.refresh(other_lesson)

    assert target_lesson.module_id == target_module.id
    assert other_lesson.module_id == other_module.id


@pytest.mark.asyncio
async def test_assign_module_links_lesson_to_module(session):
    """Привязывает урок к указанному модулю в базе данных."""
    module = ModuleOrm(
        id=uuid4(),
        course_id=None,
        title="Basics",
        description="Python basics",
        order=1,
    )
    lesson = LessonOrm(
        id=uuid4(),
        module_id=None,
        title="Variables",
        description="Python variables",
        order=1,
        content_blocks=[],
    )
    session.add_all([module, lesson])
    await session.flush()
    repository = SqlLessonRepository(session)

    await repository.assign_module(lesson.id, module.id)
    await session.refresh(lesson)

    assert lesson.module_id == module.id
