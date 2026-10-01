from src.shared.domain.vo import Email
from src.shared.infra.repos import ModelMapper

from ...domain.entities import Notification, UserPreference
from .models import NotificationOrm, UserPreferenceOrm


class NotificationMapper(ModelMapper[Notification, NotificationOrm]):
    @staticmethod
    def to_entity(model: NotificationOrm) -> Notification:
        return Notification(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            user_id=model.user_id,
            email=Email(model.email),
            title=model.title,
            message=model.message,
            type=model.notification_type,
            read=model.read,
            data=model.data,
        )

    @staticmethod
    def from_entity(entity: Notification) -> NotificationOrm:
        return NotificationOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
            user_id=entity.user_id,
            email=entity.email.value,
            title=entity.title,
            message=entity.message,
            notification_type=entity.type,
            read=entity.read,
            data=entity.data,
        )


class UserPreferenceMapper(ModelMapper[UserPreference, UserPreferenceOrm]):
    @staticmethod
    def to_entity(model: UserPreferenceOrm) -> UserPreference:
        return UserPreference(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            user_id=model.user_id,
            notification_type=model.notification_type,
            enabled_channels=set(model.enabled_channels),
            muted_until=model.muted_until,
        )

    @staticmethod
    def from_entity(entity: UserPreference) -> UserPreferenceOrm:
        return UserPreferenceOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
            user_id=entity.user_id,
            notification_type=entity.notification_type,
            enabled_channels=list(entity.enabled_channels),
            muted_until=entity.muted_until,
        )
