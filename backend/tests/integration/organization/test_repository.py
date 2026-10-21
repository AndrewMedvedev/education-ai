import pytest
from sqlalchemy.exc import IntegrityError

from src.organization.infra.models import OrganizationOrm
from src.organization.infra.repos import SqlOrganizationRepository


@pytest.mark.asyncio
async def test_get_by_email_returns_only_matching_organization(session):
    """Находит организацию по её уникальному email."""
    expected_organization = OrganizationOrm(
        name="Expected",
        email="expected@example.com",
        description="Description",
        is_active=True,
    )
    session.add_all(
        [
            expected_organization,
            OrganizationOrm(
                name="Other",
                email="other@example.com",
                description="Description",
                is_active=True,
            ),
        ]
    )
    await session.flush()
    repository = SqlOrganizationRepository(session)

    organization = await repository.get_by_email("expected@example.com")

    assert organization is not None
    assert organization.id == expected_organization.id
    assert organization.name == "Expected"


@pytest.mark.asyncio
async def test_organization_email_is_unique_in_database(session):
    """Не позволяет сохранить две организации с одинаковым email."""
    session.add(
        OrganizationOrm(
            name="First",
            email="organization@example.com",
            description="Description",
            is_active=True,
        )
    )
    await session.flush()
    session.add(
        OrganizationOrm(
            name="Second",
            email="organization@example.com",
            description="Description",
            is_active=True,
        )
    )

    with pytest.raises(IntegrityError):
        await session.flush()
