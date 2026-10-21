# pyright: reportAssignmentType=false
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field

from src.courses.domain.enums import ContentType, DifficultyLevel
from src.courses.domain.vo import MemberRole
from src.shared.application.dtos import BaseQueryParamFilters


@dataclass(kw_only=True, slots=True)
class BasicInfo:
    id: UUID
    title: str
    order: int


@dataclass(kw_only=True, slots=True)
class LessonBasicInfo(BasicInfo):
    description: str
    learning_objectives: list[str] = field(default_factory=list)
    estimated_time_minutes: int | None = None


@dataclass(kw_only=True, slots=True)
class ModuleBasicInfo(BasicInfo):
    description: str
    learning_objectives: list[str] = field(default_factory=list)
    lessons: list[BasicInfo] = field(default_factory=list)  # [{"id": UUID, "order": int}, ...]


@dataclass(kw_only=True, slots=True)
class CourseBasicInfo:
    id: UUID
    title: str
    description: str
    difficulty: DifficultyLevel
    tags: list[str]
    learning_objectives: list[str] = field(default_factory=list)
    modules: list[BasicInfo] = field(default_factory=list)  # [{"id": UUID, "order": int}, ...]

if TYPE_CHECKING:
    from ..domain.entities import Invitation


class Chat(BaseModel):
    chat_id: UUID = Field(default_factory=uuid4)
    course_id: UUID
    role: Literal["assistant", "user"] = "user"
    content: str | dict[str, Any]


class ModuleGenerationChat(Chat):
    order: int


class LessonGenerationChat(ModuleGenerationChat):
    module_id: UUID


class EditorChat(Chat):
    content_type: ContentType
    content_block: str
    content_blocks: list
    images: list[str] = Field(default_factory=list, max_length=5)


class MentorChat(Chat):
    content_blocks: list = Field(default_factory=list)


class EditorInfo(BaseModel):
    title: str | None = None
    description: str | None = None
    difficulty: DifficultyLevel | None = None
    tags: list[str] | None = None
    image_url: str | None = None
    learning_objectives: list[str]
    estimated_time_minutes: int | None = None


class LessonTheorySessionEditSchema(BaseModel):
    completed_at: datetime | None = None
    active_time_seconds: int | None = None
    max_scroll_depth_percent: int | None = None


class CourseSchema(BaseModel):
    title: str
    description: str
    difficulty: DifficultyLevel = DifficultyLevel.BEGINNER
    tags: list[str]


class EditCourseSchema(BaseModel):
    title: str | None = None
    description: str | None = None
    difficulty: DifficultyLevel | None = None
    tags: list[str] | None = None


class ModuleSchema(BaseModel):
    title: str
    description: str
    order: int
    learning_objectives: list[str]


class EditModuleSchema(BaseModel):
    title: str | None = None
    description: str | None = None
    order: int | None = None
    learning_objectives: list[str] | None = None


class LessonSchema(BaseModel):
    title: str
    description: str
    order: int
    learning_objectives: list[str]
    estimated_time_minutes: int | None = None


class EditLessonSchema(BaseModel):
    title: str | None = None
    description: str | None = None
    order: int | None = None
    learning_objectives: list[str] | None = None
    estimated_time_minutes: int | None = None


class LessonTheorySessionFilters(BaseQueryParamFilters):
    created_from: datetime | None = None
    created_to: datetime | None = None


class InvitationCreate(BaseModel):
    course_id: UUID
    email: EmailStr
    role: MemberRole


class InvitationResponse(BaseModel):
    """Приглашение на курс для списков — без токена из письма."""

    id: UUID
    course_id: UUID
    email: EmailStr
    role: MemberRole
    user_id: UUID | None = None
    invited_by: UUID
    created_at: datetime
    expires_at: datetime

    @classmethod
    def from_entity(cls, invitation: Invitation) -> InvitationResponse:
        return cls(
            id=invitation.id,
            course_id=invitation.course_id,
            email=invitation.email.value,
            role=invitation.role,
            user_id=invitation.user_id,
            invited_by=invitation.invited_by,
            created_at=invitation.created_at,
            expires_at=invitation.expires_at,
        )
