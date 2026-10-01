# pyright: reportAssignmentType=false

from __future__ import annotations

from typing import Any, Self

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

from src.core.settings import settings
from src.shared.domain.vo import Email
from src.shared.utils.time import current_datetime, get_expiration_time

from ...shared.domain.entities import AggregateRoot, Entity
from .constants import INVITATION_EXPIRES_IN_DAYS
from .events import CourseInvited
from .vo import (
    AnyContentBlock,
    CourseStatus,
    DifficultyLevel,
    DocumentNodeType,
    MemberRole,
    PracticeStatus,
)


def _generate_invite_token(length: int = 32) -> str:
    """
    Генерирует токен для активации приглашения.
    """

    return secrets.token_urlsafe(length)


@dataclass(kw_only=True, slots=True)
class LessonBasicInfo:
    """Описывает доменную сущность `LessonBasicInfo` и её данные для бизнес-логики."""

    id: UUID
    title: str
    description: str
    order: int
    learning_objectives: list[str] = field(default_factory=list)
    estimated_time_minutes: int | None = None


@dataclass(kw_only=True, slots=True)
class BasicInfo:
    """Описывает доменную сущность `BasicInfo` и её данные для бизнес-логики."""

    id: UUID
    title: str
    order: int


@dataclass(kw_only=True, slots=True)
class ModuleBasicInfo:
    """Описывает доменную сущность `ModuleBasicInfo` и её данные для бизнес-логики."""

    id: UUID
    title: str
    description: str
    order: int
    learning_objectives: list[str] = field(default_factory=list)
    lessons: list[BasicInfo] = field(default_factory=list)  # [{"id": UUID, "order": int}, ...]


@dataclass(kw_only=True, slots=True)
class CourseBasicInfo:
    """Описывает доменную сущность `CourseBasicInfo` и её данные для бизнес-логики."""

    id: UUID
    title: str
    description: str
    difficulty: DifficultyLevel
    tags: list[str]
    learning_objectives: list[str] = field(default_factory=list)
    modules: list[BasicInfo] = field(default_factory=list)  # [{"id": UUID, "order": int}, ...]


@dataclass(kw_only=True, slots=True)
class Lesson(Entity):
    """Урок внутри модуля курса.

    Attributes:
        title: Название урока.
        description: Описание урока.
        order: Порядковый номер урока в модуле (начинается с 1).
        learning_objectives: Список целей урока.
        content_blocks: Дополнительные блоки контента (видео, код, тесты и т.п.).
        estimated_time_minutes: Предполагаемое время прохождения урока (в минутах).
        assignment: Практическое задание
    """

    module_id: UUID
    title: str
    description: str
    order: int
    learning_objectives: list[str] = field(default_factory=list)
    content_blocks: list[AnyContentBlock] = field(default_factory=list)
    estimated_time_minutes: int | None = None

    def append_content_block(self, content_block: AnyContentBlock) -> None:
        """Выполняет действие `append_content_block`, чтобы поддержать основной сценарий модуля."""
        self.content_blocks.append(content_block)


@dataclass(kw_only=True, slots=True)
class Module(Entity):
    """Модуль курса.

    Attributes:
        title: Название модуля.
        description: Описание модуля.
        order: Порядковый номер модуля в курсе.
        learning_objectives: Список целей модуля.
        content_blocks: Блоки контента модуля (общие для всех уроков).
        assignment: Задание модуля (может быть Assignment или сырой dict).
        lesson_basic_info: Список {"order": int, "title": str}.
        lessons: Список уроков модуля.


    """

    course_id: UUID
    title: str
    description: str
    order: int
    learning_objectives: list[str] = field(default_factory=list)
    lessons: list[Lesson] = field(default_factory=list)

    def append_lesson(self, module: Lesson) -> None:
        """Выполняет действие `append_lesson`, чтобы поддержать основной сценарий модуля."""
        self.lessons.append(module)


@dataclass(kw_only=True, slots=True)
class Course(AggregateRoot):
    """Курс.

    Attributes:
        title: Название курса.
        description: Полное описание курса.
        difficulty: Уровень сложности (beginner, intermediate, advanced).
        tags: Список тегов для поиска и категоризации.
        status: Статус курса (draft, published, archived).
        popularity: оценок популярности.
        creator_id: UUID создателя курса.
        image_url: Ссылка на обложку курса (опционально).
        learning_objectives: Список целей курса.
        final_assessment: Финальное задание (модель или dict).
        module_basic_info: Список {"order": int, "title": str}.
        modules: Список модулей курса.
    """

    title: str
    description: str
    difficulty: DifficultyLevel
    tags: list[str]
    status: CourseStatus = CourseStatus.IN_GENERATION
    popularity: int = 0
    creator_id: UUID
    image_url: str | None = None
    learning_objectives: list[str] = field(default_factory=list)
    modules: list[Module] = field(default_factory=list)
    members: list[Member] = field(default_factory=list)

    def append_module(self, module: Module) -> None:
        """Выполняет действие `append_module`, чтобы поддержать основной сценарий модуля."""
        self.modules.append(module)


@dataclass(kw_only=True, slots=True)
class LessonTheorySession(AggregateRoot):
    lesson_id: UUID
    user_id: UUID
    completed_at: datetime | None = None
    active_time_seconds: int = 0
    max_scroll_depth_percent: int = 0


@dataclass(kw_only=True, slots=True)
class Document(Entity):
    """Описывает доменную сущность `Document` и её данные для бизнес-логики."""

    owner_id: UUID
    parent_node_id: UUID | None = None
    node_type: DocumentNodeType
    title: str | None = None
    content: str | None = None


@dataclass(kw_only=True, slots=True)
class Chat(Entity):
    """Описывает доменную сущность `Chat` и её данные для бизнес-логики."""

    user_id: UUID
    course_id: UUID
    messages: list[dict] = field(default_factory=list)

    def replace_messages(self, messages: list[dict]) -> None:
        """Выполняет действие `replace_messages`, чтобы поддержать основной сценарий модуля."""
        self.messages = messages.copy()


@dataclass(kw_only=True, slots=True)
class Member(Entity):
    """Описывает доменную сущность `Member` и её данные для бизнес-логики."""

    role: MemberRole
    course_id: UUID
    user_id: UUID


@dataclass(kw_only=True, slots=True)
class StudentPractice(Entity):
    """Описывает доменную сущность `StudentPractice` и её данные для бизнес-логики."""

    user_id: UUID
    course_id: UUID
    messages: list[dict] = field(default_factory=list)

    def replace_messages(self, messages: list[dict]) -> None:
        """Выполняет действие `replace_messages`, чтобы поддержать основной сценарий модуля."""
        self.messages = messages.copy()


@dataclass(kw_only=True, slots=True)
class Practice(Entity):
    """Описывает доменную сущность `Practice` и её данные для бизнес-логики."""

    user_id: UUID
    module_id: UUID
    lesson_id: UUID
    status: PracticeStatus = PracticeStatus.NOT_STARTED

    practice: list[dict[str, Any]] = field(default_factory=list)


@dataclass(kw_only=True, slots=True)
class Invitation(Entity):
    """
    Приглашение пользователя в курс.
    """

    title: str
    course_id: UUID
    user_id: UUID | None = None
    email: Email
    token: str = field(default_factory=_generate_invite_token)
    invited_by: UUID
    role: MemberRole
    expires_at: datetime
    used_at: datetime | None = None
    is_used: bool = False

    @property
    def is_valid(self) -> bool:
        return not self.is_used and self.expires_at > current_datetime()

    @classmethod
    def create(
        cls,
        title: str,
        course_id: UUID,
        email: Email,
        invited_by: UUID,
        role: MemberRole,
        user_id: UUID | None = None,
        expires_at: datetime | None = None,
    ) -> Self:
        expires_at = get_expiration_time(expires_in=timedelta(days=INVITATION_EXPIRES_IN_DAYS))
        invitation = cls(
            title=title,
            course_id=course_id,
            user_id=user_id,
            email=email,
            invited_by=invited_by,
            role=role,
            expires_at=expires_at,
        )
        invitation.invite()
        return invitation

    def invite(self) -> None:
        self.register_event(
            CourseInvited(
                invitation_id=self.id,
                title=self.title,
                url=f"{settings.frontend_url}/courses/invitations/accept/{self.token}",
                course_id=self.course_id,
                user_id=self.user_id,
                email=self.email,
                invited_by=self.invited_by,
                role=self.role,
            )
        )

    def mark_as_used(self) -> None:
        self.used_at = current_datetime()
        self.is_used = True
