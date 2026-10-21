# ruff: noqa: PLR6301

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.courses.application.dtos import EditLessonSchema, LessonSchema
from src.courses.application.services.lesson import LessonService
from src.courses.domain.entities import Lesson
from src.courses.domain.vo import TextBlock
from src.shared.domain.exceptions import NotFoundError


@pytest.fixture
def repository():
    """Создаёт мок репозитория уроков."""
    return AsyncMock()


@pytest.fixture
def module_repository():
    """Создаёт мок репозитория модулей."""
    return AsyncMock()


@pytest.fixture
def session():
    """Создаёт мок сессии базы данных."""
    return AsyncMock()


@pytest.fixture
def service(repository, module_repository, session):
    """Создаёт сервис уроков с изолированными зависимостями."""
    return LessonService(
        lesson_repo=repository,
        module_repo=module_repository,
        session=session,
    )


def build_lesson(module_id):
    """Создаёт урок для сценариев сервиса."""
    return Lesson(
        module_id=module_id,
        title="Lesson",
        description="Lesson description",
        order=1,
        learning_objectives=["Understand basics"],
    )


class TestLessonService:
    @pytest.mark.asyncio
    async def test_create_lesson(self, service, repository, session):
        """Создаёт урок в переданном модуле."""
        module_id = uuid4()
        schema = LessonSchema(
            title="Lesson",
            description="Lesson description",
            order=1,
            learning_objectives=["Understand basics"],
        )
        lesson = build_lesson(module_id)
        repository.create.return_value = lesson

        result = await service.create(module_id, schema)

        assert result == lesson
        created_lesson = repository.create.await_args.args[0]
        assert created_lesson.module_id == module_id
        assert created_lesson.title == schema.title
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_assign_module(self, service, repository, module_repository, session):
        """Привязывает существующий урок к существующему модулю."""
        lesson_id = uuid4()
        module_id = uuid4()
        module_repository.exists.return_value = True
        repository.exists.return_value = True

        await service.assign_module(lesson_id, module_id)

        repository.assign_module.assert_awaited_once_with(lesson_id, module_id)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_assign_module_raises_when_module_not_found(
        self, service, repository, module_repository, session
    ):
        """Не привязывает урок к отсутствующему модулю."""
        module_repository.exists.return_value = False

        with pytest.raises(NotFoundError, match="Module with id .* not found"):
            await service.assign_module(uuid4(), uuid4())

        repository.exists.assert_not_awaited()
        repository.assign_module.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_assign_module_raises_when_lesson_not_found(
        self, service, repository, module_repository, session
    ):
        """Не привязывает к модулю отсутствующий урок."""
        module_repository.exists.return_value = True
        repository.exists.return_value = False

        with pytest.raises(NotFoundError, match="Lesson with id .* not found"):
            await service.assign_module(uuid4(), uuid4())

        repository.assign_module.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_read_content_blocks(self, service, repository):
        """Возвращает content blocks существующего урока."""
        lesson_id = uuid4()
        content_blocks = [TextBlock(md_content="Lesson content")]
        repository.exists.return_value = True
        repository.get_content_blocks_by_id.return_value = content_blocks

        result = await service.read_content_blocks(lesson_id)

        assert result == content_blocks
        repository.get_content_blocks_by_id.assert_awaited_once_with(lesson_id)

    @pytest.mark.asyncio
    async def test_read_content_blocks_raises_when_lesson_not_found(self, service, repository):
        """Не ищет content blocks, если урока нет."""
        repository.exists.return_value = False

        with pytest.raises(NotFoundError, match="Lesson with id .* not found"):
            await service.read_content_blocks(uuid4())

        repository.get_content_blocks_by_id.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_read_content_blocks_raises_when_content_not_found(self, service, repository):
        """Сообщает об отсутствии content blocks у существующего урока."""
        repository.exists.return_value = True
        repository.get_content_blocks_by_id.return_value = []

        with pytest.raises(NotFoundError, match="Content blocks for lesson with id .* not found"):
            await service.read_content_blocks(uuid4())

    @pytest.mark.asyncio
    async def test_edit_lesson(self, service, repository, session):
        """Обновляет только поля, переданные в схеме редактирования урока."""
        lesson_id = uuid4()
        schema = EditLessonSchema(title="Updated lesson")
        lesson = build_lesson(uuid4())
        repository.exists.return_value = True
        repository.update.return_value = lesson

        result = await service.edit(lesson_id, schema)

        assert result == lesson
        repository.update.assert_awaited_once_with(uid=lesson_id, title="Updated lesson")
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_edit_lesson_raises_when_not_found(self, service, repository, session):
        """Не обновляет урок, если его нет в репозитории."""
        repository.exists.return_value = False

        with pytest.raises(NotFoundError, match="Lesson with id .* not found"):
            await service.edit(uuid4(), EditLessonSchema(title="Updated lesson"))

        repository.update.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_content_blocks(self, service, repository, session):
        """Заменяет content blocks существующего урока."""
        lesson_id = uuid4()
        content_blocks = [TextBlock(md_content="Updated content")]
        lesson = build_lesson(uuid4())
        repository.exists.return_value = True
        repository.update.return_value = lesson

        result = await service.update_content_blocks(lesson_id, content_blocks)

        assert result == lesson
        repository.update.assert_awaited_once_with(uid=lesson_id, content_blocks=content_blocks)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_content_blocks_raises_when_lesson_not_found(
        self, service, repository, session
    ):
        """Не заменяет content blocks, если урока нет."""
        repository.exists.return_value = False

        with pytest.raises(NotFoundError, match="Lesson with id .* not found"):
            await service.update_content_blocks(uuid4(), [TextBlock(md_content="Content")])

        repository.update.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_lesson(self, service, repository, session):
        """Удаляет существующий урок и фиксирует транзакцию."""
        lesson_id = uuid4()
        repository.exists.return_value = True

        await service.delete(lesson_id)

        repository.delete.assert_awaited_once_with(lesson_id)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_lesson_raises_when_not_found(self, service, repository, session):
        """Не удаляет урок, если его нет в репозитории."""
        repository.exists.return_value = False

        with pytest.raises(NotFoundError, match="Lesson with id .* not found"):
            await service.delete(uuid4())

        repository.delete.assert_not_awaited()
        session.commit.assert_not_awaited()
