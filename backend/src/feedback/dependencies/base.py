from typing import Annotated

from fastapi import Depends

from src.shared.dependencies.database import DBSession

from ..application.repos import FeedbackRepository
from ..infra.database.repos.feedback import SqlFeedbackRepository


def get_feedback_repo(session: DBSession) -> SqlFeedbackRepository:
    """Создаёт репозиторий на сессии текущего запроса."""
    return SqlFeedbackRepository(session)


FeedbackRepoDep = Annotated[FeedbackRepository, Depends(get_feedback_repo)]
