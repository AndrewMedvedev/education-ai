from typing import Any

from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tg_bot.core.database import Base


class StudentPractice(Base):
    __tablename__ = "student_practices"

    module_id: Mapped[UUID]
    user_id: Mapped[int] = mapped_column(BigInteger)
    assignment: Mapped[dict[str, Any]] = mapped_column(JSONB)
    ai_generated: Mapped[bool]

    submissions: Mapped[list["Submission"]] = relationship(back_populates="student_practice")


class Submission(Base):
    """Сданная работа"""

    practice_id: Mapped[UUID] = mapped_column(
        ForeignKey("student_practices.id"), unique=False
    )
    user_id: Mapped[int] = mapped_column(BigInteger)
    score: Mapped[float]
    is_passed: Mapped[bool]

    student_practice: Mapped["StudentPractice"] = relationship(back_populates="submissions")
