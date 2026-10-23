from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import Response
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.iam.api.v1.invitations import preview_invitation
from src.iam.api.v1.invitations import router
from src.iam.dependencies.services import get_registration_service
from src.iam.application.dtos import CreateUserDTO
from src.iam.application.services.registration import RegistrationService
from src.iam.domain.entities import Invitation
from src.iam.domain.vo import Email
from src.shared.domain.exceptions import AlreadyExistsError, NotFoundError
from src.shared.utils.time import current_datetime


def make_invitation():
    return Invitation(
        email=Email("invitee@example.com"),
        invited_by=uuid4(),
        organization_id=uuid4(),
        granted_roles={uuid4()},
        expires_at=current_datetime() + timedelta(days=1),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("kind,exists,expected", [("iam", False, True), ("iam", True, False), ("organization", True, False)])
async def test_preview_selects_registration_or_login(kind, exists, expected):
    invitation = make_invitation()
    iam, org, users = AsyncMock(), AsyncMock(), AsyncMock()
    iam.get_by_token.return_value = invitation if kind == "iam" else None
    org.get_by_token.return_value = invitation if kind == "organization" else None
    users.get_by_email.return_value = object() if exists else None
    response = Response()
    result = await preview_invitation(invitation.token, response, iam, org, users)
    assert result.email == "invitee@example.com"
    assert result.registration_required is expected
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["missing", "used", "expired"])
async def test_preview_rejects_invalid_links(state):
    invitation = make_invitation()
    if state == "used":
        invitation.mark_as_used()
    if state == "expired":
        invitation.expires_at = current_datetime() - timedelta(seconds=1)
    iam, org, users = AsyncMock(), AsyncMock(), AsyncMock()
    iam.get_by_token.return_value = None if state == "missing" else invitation
    org.get_by_token.return_value = None
    with pytest.raises(NotFoundError):
        await preview_invitation("token", Response(), iam, org, users)
    users.get_by_email.assert_not_awaited()


@pytest.mark.asyncio
async def test_registration_uses_invited_email_and_persists_consumption(monkeypatch):
    invitation = make_invitation()
    transaction, users, memberships, roles, invitations = [AsyncMock() for _ in range(5)]
    users.get_by_email.return_value = None
    invitations.get_by_token.return_value = invitation
    roles.get_by_ids.return_value = []
    service = RegistrationService(transaction, users, memberships, roles, invitations)
    module = "src.iam.application.services.registration"
    monkeypatch.setattr(f"{module}.validate_password_strength_async", AsyncMock())
    monkeypatch.setattr(f"{module}.hash_password_async", AsyncMock(return_value="hashed"))
    monkeypatch.setattr(f"{module}.create_tokens_for_user", lambda **kwargs: kwargs)
    result = await service.accept_invitation(invitation.token, CreateUserDTO(password="strong-password"))
    assert result["user"].email == invitation.email
    assert result["membership"].organization_id == invitation.organization_id
    invitations.update.assert_awaited_once_with(invitation.id, is_used=True, used_at=invitation.used_at)
    transaction.assert_awaited_once()
    # A consumed token cannot create another account.
    with pytest.raises(NotFoundError):
        await service.accept_invitation(invitation.token, CreateUserDTO(password="another-password"))
    assert users.create.await_count == 1


@pytest.mark.asyncio
async def test_existing_account_is_not_overwritten():
    transaction, users, memberships, roles, invitations = [AsyncMock() for _ in range(5)]
    invitations.get_by_token.return_value = make_invitation()
    users.get_by_email.return_value = SimpleNamespace(email="invitee@example.com")
    service = RegistrationService(transaction, users, memberships, roles, invitations)
    with pytest.raises(AlreadyExistsError):
        await service.accept_invitation("token", CreateUserDTO(password="replacement"))
    users.create.assert_not_awaited()
    invitations.update.assert_not_awaited()


def test_registration_http_contract_accepts_password_without_email():
    service = AsyncMock()
    service.accept_invitation.return_value = {
        "access_token": "test-access",
        "refresh_token": "test-refresh",
        "expires_at": 2000000000,
    }
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_registration_service] = lambda: service
    with TestClient(app) as client:
        response = client.post("/api/v1/invitations/accept/test-token", json={"password": "test-password"})
    assert response.status_code == 201
    assert response.json()["access_token"] == "test-access"
    call = service.accept_invitation.await_args.kwargs
    assert call["token"] == "test-token"
    assert call["dto"].password == "test-password"
