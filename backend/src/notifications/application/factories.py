from src.core.settings import app_config
from src.courses.domain.events import CourseInvited
from src.iam.domain.events import UserInvited
from src.notifications.domain.entities import Notification
from src.notifications.domain.vo import NotificationType
from src.organization.domain.events import OrganizationInvited


def from_course_invited(event: CourseInvited) -> Notification:
    return Notification(
        user_id=event.user_id,
        email=event.email,
        title="Приглашаем вас в курс",
        message=f"Вы были приглашены в курс «{event.title}».",
        type=NotificationType.COURSE_INVITED,
        data={
            "title": event.title,
            "course_id": f"{event.course_id}",
            "url": event.url,
            "app_name": app_config.name,
        },
    )


def from_organization_invited(event: OrganizationInvited) -> Notification:
    return Notification(
        user_id=event.user_id,
        email=event.email,
        title="Приглашаем вас в организацию",
        message="Вы были приглашены в организацию.",
        type=NotificationType.ORGANIZATION_INVITED,
        data={
            "title": "Приглашаем вас в организацию",
            "organization_id": f"{event.organization_id}",
            "invitation_id": f"{event.invitation_id}",
            "url": event.url,
            "app_name": app_config.name,
        },
    )


def from_user_invited(event: UserInvited) -> Notification:
    return Notification(
        email=event.email,  # pyright: ignore[reportArgumentType]
        title="Приглашаем вас в систему Генерации курсов",
        message="Вы были приглашены в систему Генерации курсов.",
        type=NotificationType.INVITED_IN_SYSTEM,
        data={
            "title": "Приглашаем вас в систему Генерации курсов",
            "url": event.url,
            "app_name": app_config.name,
        },
    )
