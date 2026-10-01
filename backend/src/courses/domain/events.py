from dataclasses import dataclass
from uuid import UUID

from src.shared.domain.events import Event
from src.shared.domain.vo import Email

from .vo import MemberRole


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
