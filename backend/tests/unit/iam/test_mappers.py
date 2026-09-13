from uuid import uuid4

from pydantic import SecretStr

from src.iam.database.repository import InvitationMapper, InvitationOrm, UserMapper, UserOrm
from src.iam.domain.dataclasses import Invitation, User
from src.iam.domain.vo import Username, UserRole
from src.shared.utils.time import current_datetime


class TestUserMapper:
    """
    Тесты для маппинга доменной сущности User в ORM модель и обратно
    """

    def test_to_entity(self):  # noqa: PLR6301
        """Преобразует данные в `test_to_entity`, чтобы разделить доменную модель и модель хранения."""
        password_hash = "hashed_password"
        model = UserOrm(
            email="test@example.com",
            username="john_doe",
            password_hash=password_hash,
            is_verify=True,
            role=UserRole.USER,
        )

        entity = UserMapper.to_entity(model)

        assert entity.id == model.id
        assert entity.created_at == model.created_at
        assert entity.email == model.email
        assert entity.password_hash.get_secret_value() == model.password_hash
        assert entity.is_verify == model.is_verify

    def test_from_entity(self):  # noqa: PLR6301
        """Преобразует данные в `test_from_entity`, чтобы разделить доменную модель и модель хранения."""
        entity = User(
            email="test@example.com",
            username=Username("john_doe"),
            password_hash=SecretStr("hashed_password"),
            is_verify=True,
            role=UserRole.USER,
        )

        model = UserMapper.from_entity(entity)

        assert model.id == entity.id
        assert model.created_at == entity.created_at
        assert model.email == entity.email
        assert model.password_hash == entity.password_hash.get_secret_value()
        assert model.is_verify == entity.is_verify


class TestInvitationMapper:
    """
    Тесты для маппинга доменной модели приглашения в ORM и обратно
    """

    def test_to_entity(self):  # noqa: PLR6301
        """Преобразует данные в `test_to_entity`, чтобы разделить доменную модель и модель хранения."""
        token = "some-token"
        model = InvitationOrm(
            email="invitee@example.com",
            token=token,
            invited_by=uuid4(),
            expires_at=current_datetime(),
            is_used=False,
        )

        entity = InvitationMapper.to_entity(model)

        assert entity.id == model.id
        assert entity.created_at == model.created_at
        assert entity.updated_at == model.updated_at
        assert entity.email == model.email
        assert entity.token == model.token
        assert entity.invited_by == model.invited_by
        assert entity.expires_at == model.expires_at
        assert entity.used_at == model.used_at
        assert entity.is_used == model.is_used

    def test_from_entity(self):  # noqa: PLR6301
        """Преобразует данные в `test_from_entity`, чтобы разделить доменную модель и модель хранения."""
        token = "some-token"
        entity = Invitation(
            email="invitee@example.com",
            token=token,
            invited_by=uuid4(),
            expires_at=current_datetime(),
            used_at=None,
            is_used=False,
            assigned_role=UserRole.USER,
        )

        model = InvitationMapper.from_entity(entity)

        assert model.id == entity.id
        assert model.created_at == entity.created_at
        assert model.updated_at == entity.updated_at
        assert model.email == entity.email
        assert model.token == entity.token
        assert model.invited_by == entity.invited_by
        assert model.expires_at == entity.expires_at
        assert model.used_at == entity.used_at
        assert model.is_used == entity.is_used
