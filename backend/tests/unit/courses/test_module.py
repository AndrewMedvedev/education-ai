# ruff: noqa: PLR6301

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.courses.application.dtos import EditModuleSchema, ModuleSchema
from src.courses.application.services.module import ModuleService
from src.courses.domain.entities import Module
from src.shared.domain.exceptions import NotFoundError


@pytest.fixture
def repository():
    """Создаёт мок репозитория модулей."""
    return AsyncMock()


@pytest.fixture
def course_repository():
    """Создаёт мок репозитория курсов."""
    return AsyncMock()


@pytest.fixture
def session():
    """Создаёт мок сессии базы данных."""
    return AsyncMock()


@pytest.fixture
def service(repository, course_repository, session):
    """Создаёт сервис модулей с изолированными зависимостями."""
    return ModuleService(
        repo=repository,
        course_repo=course_repository,
        session=session,
    )


def build_module(course_id):
    """Создаёт модуль для сценариев сервиса."""
    return Module(
        course_id=course_id,
        title="Module",
        description="Module description",
        order=1,
        learning_objectives=["Understand basics"],
    )


class TestModuleService:
    @pytest.mark.asyncio
    async def test_create_module(self, service, repository, session):
        """Создаёт модуль в переданном курсе."""
        course_id = uuid4()
        schema = ModuleSchema(
            title="Module",
            description="Module description",
            order=1,
            learning_objectives=["Understand basics"],
        )
        module = build_module(course_id)
        repository.create.return_value = module

        result = await service.create(course_id, schema)

        assert result == module
        created_module = repository.create.await_args.args[0]
        assert created_module.course_id == course_id
        assert created_module.title == schema.title
        assert created_module.learning_objectives == schema.learning_objectives
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_assign_course(self, service, repository, course_repository, session):
        """Привязывает существующий модуль к существующему курсу."""
        module_id = uuid4()
        course_id = uuid4()
        course_repository.exists.return_value = True
        repository.exists.return_value = True

        await service.assign_course(module_id, course_id)

        repository.assign_course.assert_awaited_once_with(module_id, course_id)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_assign_course_raises_when_course_not_found(
        self, service, repository, course_repository, session
    ):
        """Не привязывает модуль к отсутствующему курсу."""
        course_repository.exists.return_value = False

        with pytest.raises(NotFoundError, match="Module with id .* not found"):
            await service.assign_course(uuid4(), uuid4())

        repository.exists.assert_not_awaited()
        repository.assign_course.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_assign_course_raises_when_module_not_found(
        self, service, repository, course_repository, session
    ):
        """Не привязывает к курсу отсутствующий модуль."""
        course_repository.exists.return_value = True
        repository.exists.return_value = False

        with pytest.raises(NotFoundError, match="Lesson with id .* not found"):
            await service.assign_course(uuid4(), uuid4())

        repository.assign_course.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_edit_module(self, service, repository, session):
        """Обновляет поля существующего модуля."""
        module_id = uuid4()
        schema = EditModuleSchema(title="Updated module")
        module = build_module(uuid4())
        repository.exists.return_value = True
        repository.update.return_value = module

        result = await service.edit(module_id, schema)

        assert result == module
        repository.update.assert_awaited_once_with(uid=module_id, title="Updated module")
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_edit_module_raises_when_not_found(self, service, repository, session):
        """Не обновляет модуль, если его нет в репозитории."""
        repository.exists.return_value = False

        with pytest.raises(NotFoundError, match="Module with id .* not found"):
            await service.edit(uuid4(), EditModuleSchema(title="Updated module"))

        repository.update.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_module(self, service, repository, session):
        """Удаляет существующий модуль и фиксирует транзакцию."""
        module_id = uuid4()
        repository.exists.return_value = True

        await service.delete(module_id)

        repository.delete.assert_awaited_once_with(module_id)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_module_raises_when_not_found(self, service, repository, session):
        """Не удаляет модуль, если его нет в репозитории."""
        repository.exists.return_value = False

        with pytest.raises(NotFoundError, match="Module with id .* not found"):
            await service.delete(uuid4())

        repository.delete.assert_not_awaited()
        session.commit.assert_not_awaited()
