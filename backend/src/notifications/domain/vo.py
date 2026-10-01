from enum import StrEnum, auto


class NotificationType(StrEnum):
    """Типы уведомлений в системе"""

    COURSE_INVITED = auto()
    ORGANIZATION_INVITED = auto()
    INVITED_IN_SYSTEM = auto()


class ChannelType(StrEnum):
    """Каналы куда пользователи получают уведомление"""

    EMAIL = "email"
    IN_APP = "in_app"  # всплывающее уведомление в Web-приложении
