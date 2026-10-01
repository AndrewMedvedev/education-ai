from http import HTTPStatus

from ...shared.domain.exceptions import DomainError


class S3NotFoundError(DomainError):
    status_code = HTTPStatus.NOT_FOUND
    error_code = "NOT_FOUND"
    public_message = "Объект не найден"
