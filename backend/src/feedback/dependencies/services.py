from typing import Annotated

from fastapi import Depends

from src.shared.dependencies.database import TransactionDep

from ..application.services import FeedbackService
from .base import FeedbackRepoDep


def get_feedback_service(repo: FeedbackRepoDep, transaction: TransactionDep) -> FeedbackService:
    """Подключает сервис к репозиторию и общей транзакции запроса."""
    return FeedbackService(feedback_repo=repo, transaction=transaction)


FeedbackServiceDep = Annotated[FeedbackService, Depends(get_feedback_service)]
