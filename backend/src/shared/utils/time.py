from datetime import datetime, timedelta

from ...core.settings import timezone


def current_datetime() -> datetime:
    """Текущее время в указанном часовом поясе."""

    return datetime.now(timezone)


def from_timestamp(timestamp: float) -> datetime:
    """Преобразует UNIX timestamp в datetime с timezone."""

    return datetime.fromtimestamp(timestamp, timezone)


def get_expiration_time(expires_in: timedelta) -> datetime:
    """Получение времени истечения в формате datetime."""

    return current_datetime() + expires_in


def get_expiration_timestamp(expires_in: timedelta) -> int:
    """Получение и расчёт UNIX Timestamp для истечения времени."""

    return int((current_datetime() + expires_in).timestamp())
