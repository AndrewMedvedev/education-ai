from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.iam.domain.entities import Invitation as IAMInvitation
from src.iam.domain.vo import Email as IAMEmail
from src.organization.application.services.invitation_management import (
    InvitationManagementService,
)
from src.organization.domain.entities import Invitation
from src.shared.application.dtos import Pagination
from src.shared.domain.exceptions import (
    AlreadyExistsError,
    ForbiddenError,
    NotFoundError,
)
from src.shared.domain.vo import Email
from src.shared.utils.time import current_datetime


def invitation(kind="organization"):
    cls, email = (Invitation, Email) if kind == "organization" else (IAMInvitation, IAMEmail)
    return cls(
        email=email("invited@example.com"),
        invited_by=uuid4(),
        organization_id=uuid4(),
        granted_roles={uuid4()},
        expires_at=current_datetime() + timedelta(days=1),
    )


def setup(item, source="organization"):
    org, iam, users, memberships, transaction = [AsyncMock() for _ in range(5)]
    service = InvitationManagementService(org, iam, users, memberships, transaction)
    org.get_by_token.return_value = item if source == "organization" else None
    iam.get_by_token.return_value = item if source == "iam" else None
    service.repos[source].read.return_value = item
    users.read.return_value = SimpleNamespace(email=IAMEmail("invited@example.com"))
    memberships.get_by_user_and_organization.return_value = None
    return service, service.repos[source], users, memberships, transaction


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["organization", "iam"])
async def test_accept_checks_recipient_and_consumes_both_kinds(source):
    item = invitation(source)
    service, repo, users, memberships, transaction = setup(item, source)
    user_id = uuid4()
    users.read.return_value.email = IAMEmail("other@example.com")
    with pytest.raises(ForbiddenError):
        await service.accept(item.token, user_id)
    memberships.create.assert_not_awaited()
    repo.update.assert_not_awaited()
    users.read.return_value.email = IAMEmail("invited@example.com")
    result = await service.accept(item.token, user_id)
    assert result.user_id == user_id
    assert result.organization_id == item.organization_id
    repo.update.assert_awaited_once_with(item.id, is_used=True, used_at=item.used_at)
    transaction.assert_awaited_once()
    with pytest.raises(NotFoundError):
        await service.accept(item.token, user_id)
    assert memberships.create.await_count == 1


@pytest.mark.asyncio
async def test_existing_membership_consumes_link_without_duplicate():
    item = invitation()
    service, repo, _, memberships, _ = setup(item)
    existing = SimpleNamespace(id=uuid4())
    memberships.get_by_user_and_organization.return_value = existing
    assert await service.accept(item.token, uuid4()) is existing
    memberships.create.assert_not_awaited()
    repo.update.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["revoke", "resend"])
async def test_cannot_manage_another_organization(action):
    item = invitation()
    service, repo, _, _, transaction = setup(item)
    with pytest.raises(NotFoundError):
        await getattr(service, action)(item.id, "organization", uuid4())
    repo.update.assert_not_awaited()
    transaction.assert_not_awaited()


@pytest.mark.asyncio
async def test_revoke_retains_history_and_invalidates_acceptance():
    item = invitation()
    service, repo, _, _, _ = setup(item)
    await service.revoke(item.id, "organization", item.organization_id)
    assert item.deleted_at is not None
    repo.update.assert_awaited_once_with(item.id, deleted_at=item.deleted_at)
    repo.delete.assert_not_awaited()
    with pytest.raises(NotFoundError):
        await service.accept(item.token, uuid4())
    with pytest.raises(AlreadyExistsError):
        await service.resend(item.id, "organization", item.organization_id)


@pytest.mark.asyncio
async def test_accepted_invitation_cannot_be_revoked_or_resent():
    item = invitation()
    item.mark_as_used()
    service, repo, _, _, _ = setup(item)
    for action in [service.revoke, service.resend]:
        with pytest.raises(AlreadyExistsError):
            await action(item.id, "organization", item.organization_id)
    repo.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_expired_invitation_can_be_resent_but_not_accepted():
    item = invitation()
    item.expires_at = current_datetime() - timedelta(seconds=1)
    service, _, _, _, _ = setup(item)
    assert await service.resend(item.id, "organization", item.organization_id) is item
    with pytest.raises(NotFoundError):
        await service.accept(item.token, uuid4())


@pytest.mark.asyncio
async def test_list_combines_sources_paginates_and_excludes_tokens():
    org_item, iam_item = invitation(), invitation("iam")
    iam_item.organization_id = org_item.organization_id
    service, _, _, _, _ = setup(org_item)
    service.repos["organization"].list_by_organization.return_value = [org_item]
    service.repos["iam"].list_by_organization.return_value = [iam_item]
    result = await service.list(org_item.organization_id, Pagination(page=1, size=1))
    assert result.total == 2
    assert len(result.items) == 1
    assert result.items[0].source == "iam"
    assert "token" not in result.model_dump_json()
    for repo in service.repos.values():
        repo.list_by_organization.assert_awaited_once_with(org_item.organization_id)


@pytest.mark.parametrize("state", ["pending", "accepted", "revoked", "expired"])
def test_summary_status(state):
    item = invitation()
    if state == "accepted":
        item.mark_as_used()
    elif state == "revoked":
        item.deleted_at = current_datetime()
    elif state == "expired":
        item.expires_at = current_datetime() - timedelta(seconds=1)
    assert InvitationManagementService.summarize(item, "organization").status == state


def test_http_list_and_revoke_use_current_organization():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from src.iam.dependencies import get_current_identity
    from src.organization.api.v1.invitations import router
    from src.organization.dependencies.services import get_invitation_management
    from src.organization.domain.permissions.invitations import (
        DELETE_INVITATION,
        INVITE,
    )
    from src.shared.application.dtos import Page

    item = invitation()
    identity = SimpleNamespace(
        id=uuid4(),
        organization_id=item.organization_id,
        permissions={INVITE.code, DELETE_INVITATION.code},
    )
    service = AsyncMock()
    summary = InvitationManagementService.summarize(item, "organization")
    service.list.return_value = Page.create([summary], 1, 1, 20)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_current_identity] = lambda: identity
    app.dependency_overrides[get_invitation_management] = lambda: service
    with TestClient(app) as client:
        response = client.get("/api/v1/organizations/invitations?page=1&size=20")
        assert response.status_code == 200
        assert response.json()["items"][0]["status"] == "pending"
        assert "token" not in response.text
        response = client.delete(f"/api/v1/organizations/invitations/revoke/{item.id}?source=iam")
        assert response.status_code == 204
        assert response.content == b""
        service.revoke.assert_awaited_once_with(item.id, "iam", item.organization_id)
        response = client.delete(
            f"/api/v1/organizations/invitations/revoke/{item.id}?source=invalid"
        )
        assert response.status_code == 422
