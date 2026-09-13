from fastapi import status


class DomainError(Exception):
    """Базовая ошибка приложения - от него наследуются все доменные исключения"""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_SERVER_ERROR"
    public_message: str = "Внутренняя ошибка сервера"

    def __init__(
        self,
        message: str | None = None,
        status_code: int | None = None,
        error_code: str | None = None,
        details: dict | list | None = None,
    ):
        self.message = message or self.public_message
        self.status_code = status_code or self.status_code
        self.error_code = error_code or self.error_code
        self.details = details or {}
        super().__init__(self.message)


class InternalServerError(DomainError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "INTERNAL_SERVER_ERROR"
    public_message = "Внутренняя ошибка сервера"


class DatabaseError(DomainError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "DATABASE_ERROR"
    public_message = "Ошибка сервера базы данных"


class BadRequestError(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "BAD_REQUEST"
    public_message = "Некорректный запрос"


class UnauthorizedError(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "UNAUTHORIZED"
    public_message = "Неавторизованный доступ"


class ForbiddenError(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "FORBIDDEN"
    public_message = "Доступ запрещен"


class NotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "RESOURCE_NOT_FOUND"
    public_message = "Ресурс не найден"


class InvariantViolationError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "INVARIANT_VIOLATION"
    public_message = "Нарушены условия существования объекта"


class InvalidStateError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "INVALID_STATE"
    public_message = "Невалидное состояние объекта"


class AlreadyExistsError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "ALREADY_EXISTS"
    public_message = "Ресурс уже существует"


class EmailSendingFailedError(DomainError):
    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "EMAIL_SENDING_FAILED"
    public_message = "Не удалось отправить письмо. Попробуйте позже."


class RateLimitExceededError(DomainError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "RATE_LIMIT_EXCEEDED"
    public_message = "Превышен лимит запросов"


class UnsupportedOperationError(DomainError):
    status_code = status.HTTP_405_METHOD_NOT_ALLOWED
    error_code = "UNSUPPORTED_OPERATION"
    public_message = "Операция удалена или не поддерживается."
