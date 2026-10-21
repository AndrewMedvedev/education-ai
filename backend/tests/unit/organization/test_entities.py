from datetime import datetime, timedelta, timezone

from src.organization.domain.entities import Organization


def test_edit_updates_only_provided_normalized_values(monkeypatch):
    """Обновляет переданные поля и убирает пробелы по краям."""
    updated_at = datetime.now(timezone.utc) - timedelta(days=1)
    edited_at = datetime.now(timezone.utc)
    organization = Organization(
        name="Old name",
        email="old@example.com",
        description="Old description",
        updated_at=updated_at,
    )
    monkeypatch.setattr(
        "src.organization.domain.entities.current_datetime",
        lambda: edited_at,
    )

    organization.edit(name="  New name  ", description="  New description  ")

    assert organization.name == "New name"
    assert organization.description == "New description"
    assert organization.email == "old@example.com"
    assert organization.updated_at == edited_at


def test_edit_ignores_empty_values():
    """Не затирает данные организации пустыми строками."""
    updated_at = datetime.now(timezone.utc)
    organization = Organization(
        name="Name",
        email="organization@example.com",
        description="Description",
        updated_at=updated_at,
    )

    organization.edit(name="  ", description="")

    assert organization.name == "Name"
    assert organization.description == "Description"
    assert organization.updated_at == updated_at
