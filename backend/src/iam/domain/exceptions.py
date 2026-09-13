from fastapi import status

from src.shared.domain.exceptions import DomainError


class WeakPasswordError(DomainError):
    def __init__(
            self, message: str, suggestions: list[str], warning: str | None = None,
    ) -> None:
        details = {"suggestions": suggestions}
        if warning is not None:
            details["warning"] = warning

        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code="WEAK_PASSWORD",
            details=details,
        )


class PermissionDeniedError(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "PERMISSION_DENIED"
    public_message = "Недостаточно прав"


class UnauthorizedError(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "UNAUTHORIZED"
    public_message = "Требуется авторизация"


class InvitationExpiredError(DomainError):
    status_code = status.HTTP_410_GONE
    error_code = "INVITATION_EXPIRED"
    public_message = "Приглашение было использовано или его срок действия истёк"
