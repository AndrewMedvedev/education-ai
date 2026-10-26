from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.courses.application.dtos import CourseSchema, EditCourseSchema
from src.courses.application.services.course import CourseService
from src.courses.domain.entities import Course
from src.courses.domain.enums import CourseStatus, DifficultyLevel
from src.shared.domain.exceptions import NotFoundError


@pytest.fixture
def repository():
    """Создаёт мок репозитория курсов."""
    return AsyncMock()


@pytest.fixture
def session():
    """Создаёт мок сессии базы данных."""
    return AsyncMock()


@pytest.fixture
def service(repository, session):
    """Создаёт сервис курсов с изолированными зависимостями."""
    return CourseService(repo=repository, session=session)


def build_course(creator_id):
    """Создаёт курс для сценариев сервиса."""
    return Course(
        creator_id=creator_id,
        title="Python",
        description="Course description",
        difficulty=DifficultyLevel.BEGINNER,
        tags=["python"],
    )


class TestCourseService:
    @pytest.mark.asyncio
    async def test_create_course(self, service, repository, session):
        """Создаёт курс от имени переданного пользователя."""
        user_id = uuid4()
        schema = CourseSchema(
            title="Python",
            description="Course description",
            tags=["python"],
        )
        course = build_course(user_id)
        repository.create.return_value = course

        result = await service.create(user_id, schema)

        assert result == course
        created_course = repository.create.await_args.args[0]
        assert created_course.creator_id == user_id
        assert created_course.title == schema.title
        assert created_course.description == schema.description
        assert created_course.tags == schema.tags
        assert created_course.difficulty == schema.difficulty
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_edit_course(self, service, repository, session):
        """Обновляет только поля, которые переданы в схеме редактирования."""
        course_id = uuid4()
        schema = EditCourseSchema(title="Updated Python")
        course = build_course(uuid4())
        repository.exists.return_value = True
        repository.update.return_value = course

        result = await service.edit(course_id, schema)

        assert result == course
        repository.update.assert_awaited_once_with(uid=course_id, title="Updated Python")
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_edit_course_raises_when_not_found(self, service, repository, session):
        """Не обновляет курс, если его нет в репозитории."""
        repository.exists.return_value = False

        with pytest.raises(NotFoundError, match="Course with id .* not found"):
            await service.edit(uuid4(), EditCourseSchema(title="Updated Python"))

        repository.update.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_course(self, service, repository, session):
        """Удаляет существующий курс и фиксирует транзакцию."""
        course_id = uuid4()
        repository.exists.return_value = True

        await service.delete(course_id)

        repository.delete.assert_awaited_once_with(course_id)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_course_raises_when_not_found(self, service, repository, session):
        """Не удаляет курс, если его нет в репозитории."""
        repository.exists.return_value = False

        with pytest.raises(NotFoundError, match="Course with id .* not found"):
            await service.delete(uuid4())

        repository.delete.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_change_course_status(self, service, repository, session):
        """Меняет статус существующего курса."""
        course_id = uuid4()
        repository.exists.return_value = True

        await service.change_status(course_id, CourseStatus.PUBLISHED)

        repository.update.assert_awaited_once_with(uid=course_id, status=CourseStatus.PUBLISHED)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_change_course_status_raises_when_not_found(self, service, repository, session):
        """Не меняет статус курса, если его нет в репозитории."""
        repository.exists.return_value = False

        with pytest.raises(NotFoundError, match="Course with id .* not found"):
            await service.change_status(uuid4(), CourseStatus.ARCHIVED)

        repository.update.assert_not_awaited()
        session.commit.assert_not_awaited()
