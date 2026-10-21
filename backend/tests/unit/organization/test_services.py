from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.organization.application.dtos import OrganizationCreate, OrganizationEdit
from src.organization.application.services import OrganizationService
from src.organization.domain.entities import Organization
from src.shared.domain.exceptions import AlreadyExistsError, NotFoundError


@pytest.mark.asyncio
async def test_create_saves_organization_with_unique_email():
    """Создаёт организацию, если её email ещё не используется."""
    repository = AsyncMock()
    repository.get_by_email.return_value = None
    session = AsyncMock()
    service = OrganizationService(session, repository)
    data = OrganizationCreate(
        name="Organization",
        email="organization@example.com",
        description="Description",
    )

    organization = await service.create(data)

    assert organization.name == data.name
    assert organization.email == data.email
    assert organization.description == data.description
    repository.create.assert_awaited_once_with(organization)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_rejects_duplicate_email():
    """Не создаёт вторую организацию с тем же email."""
    repository = AsyncMock()
    repository.get_by_email.return_value = Organization(
        name="Existing",
        email="organization@example.com",
        description="Description",
    )
    session = AsyncMock()
    service = OrganizationService(session, repository)
    data = OrganizationCreate(
        name="Duplicate",
        email="organization@example.com",
        description="Description",
    )

    with pytest.raises(AlreadyExistsError, match="already exists"):
        await service.create(data)

    repository.create.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_edit_rejects_unknown_organization():
    """Не редактирует организацию, которой нет в репозитории."""
    repository = AsyncMock()
    repository.read.return_value = None
    session = AsyncMock()
    service = OrganizationService(session, repository)

    with pytest.raises(NotFoundError, match="not found"):
        await service.edit(uuid4(), OrganizationEdit(name="New name"))

    repository.upsert.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_edit_updates_and_saves_existing_organization():
    """Применяет изменения к существующей организации и сохраняет их."""
    organization = Organization(
        name="Old name",
        email="organization@example.com",
        description="Description",
    )
    repository = AsyncMock()
    repository.read.return_value = organization
    session = AsyncMock()
    service = OrganizationService(session, repository)

    result = await service.edit(organization.id, OrganizationEdit(name="New name"))

    assert result is organization
    assert organization.name == "New name"
    repository.upsert.assert_awaited_once_with(organization)
    session.commit.assert_awaited_once()
