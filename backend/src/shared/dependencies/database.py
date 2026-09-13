from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.shared.application.transaction import Transaction

from .events import EventPublisherDep

DBSession = Annotated[AsyncSession, Depends(get_db)]


def get_transaction(db: DBSession, publisher: EventPublisherDep) -> Transaction:
    return Transaction(uow=db, publisher=publisher)


TransactionDep = Annotated[Transaction, Depends(get_transaction)]
