from typing import Any

from datetime import datetime
from uuid import UUID

from sqlalchemy import TEXT, BigInteger, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class GroupOrm(Base):
    __tablename__ = "groups"

    course_id: Mapped[UUID]
    teacher_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str]

    students: Mapped[list["StudentOrm"]] = relationship(back_populates="group")


class StudentOrm(Base):
    __tablename__ = "students"

    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    group_id: Mapped[UUID] = mapped_column(ForeignKey("groups.id"), unique=False)
    full_name: Mapped[str]
    login: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str] = mapped_column(unique=True)
    is_active: Mapped[bool]

    group: Mapped["GroupOrm"] = relationship(back_populates="students")


class IndividualAssignmentOrm(Base):
    __tablename__ = "individual_assignments"

    student_id: Mapped[UUID]
    module_id: Mapped[UUID]
    version: Mapped[int]
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool]


class SubmissionOrm(Base):
    __tablename__ = "submissions"

    student_id: Mapped[UUID]
    individual_assignment_id: Mapped[UUID]
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    score: Mapped[float]
    ai_feedback: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
