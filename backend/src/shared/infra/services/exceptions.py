from fastapi import status

from src.shared.domain.exceptions import DomainError


class SrvBaseError(DomainError):
    """Переопределить `error_code` в дочерних классах."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "SERVICE_ERROR"
