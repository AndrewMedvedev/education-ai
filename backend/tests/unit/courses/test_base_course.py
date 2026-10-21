from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.courses.application.services.base_course import BaseCourseService
from src.shared.domain.exceptions import NotFoundError


@pytest.fixture
def repository():
    """Создаёт MOCK репозитория с поддержкой базовой информации."""
    return AsyncMock()


@pytest.fixture
def service(repository):
    """Создаёт базовый сервис с изолированным репозиторием."""
    return BaseCourseService(repo=repository, session=AsyncMock())


@pytest.mark.asyncio
async def test_get_basic_info_returns_repository_result(service, repository) -> None:
    """Возвращает базовую информацию, полученную из репозитория."""
    uid = uuid4()
    basic_info = object()
    repository.get_by_id_basic_info.return_value = basic_info

    result = await service.get_basic_info(uid)

    assert result is basic_info
    repository.get_by_id_basic_info.assert_awaited_once_with(uid)


@pytest.mark.asyncio
async def test_get_basic_info_raises_when_repository_returns_none(service, repository) -> None:
    """Сообщает, что сущность не найдена, когда репозиторий вернул None."""
    repository.get_by_id_basic_info.return_value = None

    with pytest.raises(NotFoundError):
        await service.get_basic_info(uuid4())
