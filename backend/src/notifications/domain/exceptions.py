from fastapi import status

from ...shared.domain.exceptions import DomainError


class NotificationSendingFailedError(DomainError):
    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "NOTIFICATION_SEND_FAILED"
    public_message = "Произошла ошибка при отправке уведомления"
