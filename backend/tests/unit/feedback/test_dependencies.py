# ruff: file-ignore[private-member-access]

from unittest.mock import AsyncMock

from src.core.database.connection import engine
from src.feedback.dependencies.base import get_feedback_repo
from src.feedback.dependencies.services import get_feedback_service
from src.feedback.domain.permissions.feedback import READ
from src.feedback.infra.database.repos.feedback import SqlFeedbackRepository


def test_repo_dependency_uses_supplied_session(mock_session: AsyncMock) -> None:
    repository = get_feedback_repo(mock_session)

    assert isinstance(repository, SqlFeedbackRepository)
    assert repository._session is mock_session


def test_service_dependency_uses_supplied_repo_and_transaction() -> None:
    repository = AsyncMock()
    transaction = AsyncMock()

    service = get_feedback_service(repository, transaction)

    assert service._feedback_repo is repository
    assert service._transaction is transaction


def test_read_permission_is_registered() -> None:
    assert READ.code == "feedback.read"


def test_database_engine_does_not_log_bound_comment_values() -> None:
    assert not engine.echo
    assert engine.sync_engine.hide_parameters is True
