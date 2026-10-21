from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar
from uuid import UUID

from pydantic import BaseModel

from src.shared.domain.events import Event
from src.shared.domain.vo import Email

from .vo import MemberRole


class LessonProgressUpdate(BaseModel):
    practice_completed_at: datetime | None = None
    test_completed_at: datetime | None = None


@dataclass(frozen=True, kw_only=True)
class LessonProgressUpdated(Event):
    event_type: ClassVar[str] = "courses.lesson.progress.updated"
    user_id: UUID
    lesson_id: UUID
    progress: LessonProgressUpdate


@dataclass(frozen=True, kw_only=True)
class CourseInvited(Event):
    """Приглашение в курс"""

    event_type: str = "courses.invited"

    invitation_id: UUID
    course_id: UUID
    invited_by: UUID
    user_id: UUID | None = None
    email: Email
    role: MemberRole
    title: str
    url: str
