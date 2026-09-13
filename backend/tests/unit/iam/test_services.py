from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import SecretStr

from src.iam.domain.dataclasses import Invitation, User
from src.iam.domain.exceptions import (
    InvitationExpiredError,
    PermissionDeniedError,
    UnauthorizedError,
)
from src.iam.domain.vo import Username, UserRole
from src.iam.schemas import InvitationCreate, Tokens, UserCreateForm
from src.iam.security import hash_password
from src.iam.services import AuthService, InvitationService
from src.shared.domain.exceptions import NotFoundError
from src.shared.utils.time import current_datetime


@pytest.fixture
def mock_session():
    """Выполняет действие `mock_session`, чтобы поддержать основной сценарий модуля."""
    return AsyncMock()


@pytest.fixture
def mock_user_repo():
    """Выполняет действие `mock_user_repo`, чтобы поддержать основной сценарий модуля."""
    repo = AsyncMock()
    repo.create = AsyncMock()
    repo.get_by_email = AsyncMock()
    repo.read = AsyncMock()
    repo.upsert = AsyncMock()
    return repo


@pytest.fixture
def mock_invitation_repo():
    """Выполняет действие `mock_invitation_repo`, чтобы поддержать основной сценарий модуля."""
    repo = AsyncMock()
    repo.get_active_by_email = AsyncMock()
    repo.create = AsyncMock()
    repo.get_by_token = AsyncMock()
    repo.upsert = AsyncMock()
    return repo


@pytest.fixture
def mock_mail_sender():
    """Выполняет действие `mock_mail_sender`, чтобы поддержать основной сценарий модуля."""
    sender = AsyncMock()
    sender.send = AsyncMock()
    return sender


@pytest.fixture
def invitation_service(mock_invitation_repo, mock_user_repo, mock_mail_sender, mock_session):
    """Выполняет действие `invitation_service`, чтобы поддержать основной сценарий модуля."""
    return InvitationService(
        invitation_repo=mock_invitation_repo,
        user_repo=mock_user_repo,
        mail_sender=mock_mail_sender,
        session=mock_session,
    )


@pytest.fixture
def mock_invitation_service():
    """Выполняет действие `mock_invitation_service`, чтобы поддержать основной сценарий модуля."""
    service = AsyncMock()
    service.create_invitation = AsyncMock()
    service.send_invitation = AsyncMock()
    service.send_an_invitation_to_the_admin = AsyncMock()
    service.verify = AsyncMock()
    return service


@pytest.fixture
def auth_service(mock_invitation_repo, mock_session, mock_user_repo, mock_invitation_service):
    """Выполняет действие `auth_service`, чтобы поддержать основной сценарий модуля."""
    return AuthService(
        session=mock_session,
        user_repo=mock_user_repo,
        invitation_service=mock_invitation_service,
        invitation_repo=mock_invitation_repo,
    )


def build_user(email: str, password_hash: str, is_verify: bool = True) -> User:
    """Собирает user из входных данных для следующего шага сценария."""
    return User(
        username=Username("test-user"),
        email=email,
        password_hash=SecretStr(password_hash),
        is_verify=is_verify,
        role=UserRole.ADMIN,
    )


def build_invitation(
    email: str, expires_at=None, invited_by=None, is_used: bool = False
) -> Invitation:
    """Собирает invitation из входных данных для следующего шага сценария."""
    return Invitation(
        email=email,
        expires_at=expires_at or current_datetime() + timedelta(days=1),
        invited_by=invited_by,
        is_used=is_used,
        assigned_role=UserRole.USER,
    )


class TestInvitationService:
    @pytest.mark.asyncio
    async def test_send_invitation_creates_new_invitation(  # noqa: PLR6301
        self, invitation_service, mock_invitation_repo, mock_session, mock_mail_sender
    ):
        """Выполняет действие `test_send_invitation_creates_new_invitation`, чтобы поддержать основной сценарий модуля."""
        email = "new@example.com"
        invited_by = uuid4()
        mock_invitation_repo.get_active_by_email.return_value = None

        invitation = await invitation_service.create_invitation(email, invited_by)

        mock_invitation_repo.create.assert_awaited_once()
        mock_session.commit.assert_awaited_once()
        mock_mail_sender.send.assert_awaited_once()

        assert invitation.email == email
        assert invitation.invited_by == invited_by
        assert invitation.token
        assert invitation.token in mock_mail_sender.send.call_args.kwargs["context"]["invite_url"]
        assert mock_mail_sender.send.call_args.kwargs["to"] == email

    @pytest.mark.asyncio
    async def test_send_an_invitation_to_the_admin(  # noqa: PLR6301
        self, invitation_service, mock_invitation_repo, mock_user_repo, mock_session
    ):
        """Выполняет действие `test_send_an_invitation_to_the_admin`, чтобы поддержать основной сценарий модуля."""
        email = "verify@example.com"
        invited_by = uuid4()
        invitation = InvitationCreate(email=email, role=UserRole.MODERATOR)
        user = build_user(email=email, password_hash=hash_password("Password1!"), is_verify=False)

        mock_user_repo.read.return_value = user

        invitation = await invitation_service.send_an_invitation_to_the_admin(
            invitation, invited_by
        )

        assert isinstance(invitation, dict)

    @pytest.mark.asyncio
    async def test_raises_permission_send_an_invitation_to_the_admin(  # noqa: PLR6301
        self, invitation_service, mock_invitation_repo, mock_user_repo, mock_session
    ):
        """Выполняет действие `test_raises_permission_send_an_invitation_to_the_admin`, чтобы поддержать основной сценарий модуля."""
        email = "verify@example.com"
        invited_by = uuid4()
        invitation = InvitationCreate(email=email, role=UserRole.SUPER_ADMIN)
        user = build_user(email=email, password_hash=hash_password("Password1!"), is_verify=False)

        mock_user_repo.read.return_value = user

        with pytest.raises(PermissionDeniedError, match="Недостаточно прав"):
            await invitation_service.send_an_invitation_to_the_admin(invitation, invited_by)

    @pytest.mark.asyncio
    async def test_send_invitation_reuses_existing_invitation(  # noqa: PLR6301
        self, invitation_service, mock_invitation_repo, mock_session, mock_mail_sender
    ):
        """Выполняет действие `test_send_invitation_reuses_existing_invitation`, чтобы поддержать основной сценарий модуля."""
        email = "existing@example.com"
        invitation = build_invitation(email=email)

        # Передаём объект, а не email — именно такая сигнатура у send_invitation
        result = await invitation_service.send_invitation(invitation)

        mock_invitation_repo.create.assert_not_awaited()
        mock_session.commit.assert_not_awaited()
        mock_mail_sender.send.assert_awaited_once()

        assert result is invitation
        assert mock_mail_sender.send.call_args.kwargs["to"] == email
        assert invitation.token in mock_mail_sender.send.call_args.kwargs["context"]["invite_url"]

    @pytest.mark.asyncio
    async def test_verify_marks_invitation_as_used_and_verifies_user(  # noqa: PLR6301
        self, invitation_service, mock_invitation_repo, mock_user_repo, mock_session
    ):
        """Выполняет действие `test_verify_marks_invitation_as_used_and_verifies_user`, чтобы поддержать основной сценарий модуля."""
        email = "verify@example.com"
        invitation = build_invitation(email=email)
        user = build_user(email=email, password_hash=hash_password("Password1!"), is_verify=False)

        mock_invitation_repo.get_by_token.return_value = invitation
        mock_user_repo.get_by_email.return_value = user

        await invitation_service.verify(invitation.token)

        assert invitation.is_used is True
        assert user.is_verify is True
        mock_user_repo.upsert.assert_awaited_once_with(user)
        mock_invitation_repo.upsert.assert_awaited_once_with(invitation)
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_verify_raises_not_found_for_unknown_token(  # noqa: PLR6301
        self, invitation_service, mock_invitation_repo
    ):
        """Выполняет действие `test_verify_raises_not_found_for_unknown_token`, чтобы поддержать основной сценарий модуля."""
        mock_invitation_repo.get_by_token.return_value = None

        with pytest.raises(NotFoundError, match="Invitation not found"):
            await invitation_service.verify("bad-token")

    @pytest.mark.asyncio
    async def test_verify_raises_for_expired_invitation(  # noqa: PLR6301
        self, invitation_service, mock_invitation_repo
    ):
        """Выполняет действие `test_verify_raises_for_expired_invitation`, чтобы поддержать основной сценарий модуля."""
        invitation = build_invitation(
            email="expired@example.com", expires_at=current_datetime() - timedelta(days=1)
        )
        mock_invitation_repo.get_by_token.return_value = invitation

        with pytest.raises(InvitationExpiredError, match="Invitation expired or already used"):
            await invitation_service.verify(invitation.token)


class TestAuthService:
    @pytest.mark.asyncio
    async def test_registration_creates_user_and_sends_invitation(  # noqa: PLR6301
        self,
        auth_service,
        mock_user_repo,
        mock_invitation_service,
        mock_invitation_repo,
        mock_session,
    ):
        # Без этого AsyncMock truthy — код не доходит до create
        """Выполняет действие `test_registration_creates_user_and_sends_invitation`, чтобы поддержать основной сценарий модуля."""
        mock_user_repo.get_by_email.return_value = None
        mock_invitation_repo.get_active_by_email.return_value = None

        form = UserCreateForm(
            username="newuser",
            email="newuser@example.com",
            password="Password1!",  # noqa: S106
        )

        result = await auth_service.registration(form=form)

        mock_user_repo.create.assert_awaited_once()
        mock_invitation_service.create_invitation.assert_awaited_once_with(form.email)
        mock_session.commit.assert_awaited_once()
        assert "Письмо" in result["message"]

    @pytest.mark.asyncio
    async def test_authenticate_returns_tokens_for_verified_user(  # noqa: PLR6301
        self, auth_service, mock_user_repo
    ):
        """Выполняет действие `test_authenticate_returns_tokens_for_verified_user`, чтобы поддержать основной сценарий модуля."""
        email = "verified@example.com"
        password = "Password1!"
        user = build_user(email=email, password_hash=hash_password(password), is_verify=True)
        mock_user_repo.get_by_email.return_value = user

        result = await auth_service.authenticate(email, password)

        assert isinstance(result, Tokens)

    @pytest.mark.asyncio
    async def test_authenticate_sends_confirmation_for_unverified_user(  # noqa: PLR6301
        self, auth_service, mock_user_repo, mock_invitation_service, mock_invitation_repo
    ):
        """Выполняет действие `test_authenticate_sends_confirmation_for_unverified_user`, чтобы поддержать основной сценарий модуля."""
        email = "pending@example.com"
        password = "Password1!"
        user = build_user(email=email, password_hash=hash_password(password), is_verify=False)
        mock_user_repo.get_by_email.return_value = user
        # None → попадаем в ветку create_invitation(email)
        mock_invitation_repo.get_active_by_email.return_value = None

        result = await auth_service.authenticate(email, password)

        # Сервис вызывает create_invitation, а не send_invitation
        mock_invitation_service.create_invitation.assert_awaited_once_with(email)
        assert isinstance(result, dict)
        assert "Письмо" in result["message"]

    @pytest.mark.asyncio
    async def test_authenticate_raises_when_user_not_found(self, auth_service, mock_user_repo):  # noqa: PLR6301
        """Выполняет действие `test_authenticate_raises_when_user_not_found`, чтобы поддержать основной сценарий модуля."""
        mock_user_repo.get_by_email.return_value = None

        with pytest.raises(UnauthorizedError, match="User not found by email"):
            await auth_service.authenticate("missing@example.com", "Password1!")

    @pytest.mark.asyncio
    async def test_authenticate_raises_for_invalid_password(self, auth_service, mock_user_repo):  # noqa: PLR6301
        """Выполняет действие `test_authenticate_raises_for_invalid_password`, чтобы поддержать основной сценарий модуля."""
        email = "verified@example.com"
        password = "Password1!"
        user = build_user(email=email, password_hash=hash_password(password), is_verify=True)
        mock_user_repo.get_by_email.return_value = user

        with pytest.raises(UnauthorizedError, match="Invalid password or user is not active"):
            await auth_service.authenticate(email, "wrong-password")

    @pytest.mark.asyncio
    async def test_refresh_tokens_returns_new_tokens_for_verified_user(  # noqa: PLR6301
        self, auth_service, mock_user_repo, monkeypatch
    ):
        """Выполняет действие `test_refresh_tokens_returns_new_tokens_for_verified_user`, чтобы поддержать основной сценарий модуля."""
        user_id = str(uuid4())
        email = "refresh@example.com"
        user = build_user(email=email, password_hash=hash_password("Password1!"), is_verify=True)
        mock_user_repo.read.return_value = user

        monkeypatch.setattr(
            "src.iam.services.validate_token",
            lambda refresh_token: {"sub": user_id, "jti": "jti", "exp": 9999999999},  # noqa: ARG005
        )

        result = await auth_service.refresh_tokens("refresh-token")

        assert isinstance(result, Tokens)
        mock_user_repo.read.assert_awaited_once_with(user_id)

    @pytest.mark.asyncio
    async def test_refresh_tokens_raises_when_user_is_not_active(  # noqa: PLR6301
        self, auth_service, mock_user_repo, monkeypatch
    ):
        """Выполняет действие `test_refresh_tokens_raises_when_user_is_not_active`, чтобы поддержать основной сценарий модуля."""
        user_id = str(uuid4())
        user = build_user(
            email="refresh@example.com", password_hash=hash_password("Password1!"), is_verify=False
        )
        mock_user_repo.read.return_value = user

        monkeypatch.setattr(
            "src.iam.services.validate_token",
            lambda refresh_token: {"sub": user_id, "jti": "jti", "exp": 9999999999},  # noqa: ARG005
        )

        with pytest.raises(UnauthorizedError, match="User is not active"):
            await auth_service.refresh_tokens("refresh-token")
