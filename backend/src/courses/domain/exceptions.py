from fastapi import status

from ...shared.domain.exceptions import DomainError


class PayloadTooLargeError(DomainError):
    status_code = status.HTTP_413_CONTENT_TOO_LARGE
    error_code = "PAYLOAD_TOO_LARGE"
    public_message = "Размер запроса превышает допустимый лимит"
