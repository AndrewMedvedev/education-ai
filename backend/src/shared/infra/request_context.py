from contextlib import suppress
from contextvars import ContextVar, Token
from uuid import UUID, uuid4

_request_id: ContextVar[UUID | None] = ContextVar("request_id", default=None)


def create_request_id(value: UUID | None = None) -> UUID:
    """Возвращает корректный UUID запроса или создаёт новый."""
    if value is not None:
        with suppress(ValueError):
            return UUID(value)
    return uuid4()


def get_request_id() -> UUID | None:
    """Возвращает ID текущего запроса из асинхронного контекста."""
    return _request_id.get()


def set_request_id(request_id: UUID) -> Token[UUID | None]:
    """Устанавливает ID текущего запроса и возвращает токен сброса."""
    return _request_id.set(request_id)


def reset_request_id(token: Token[UUID | None]) -> None:
    """Восстанавливает предыдущий контекст запроса."""
    _request_id.reset(token)
