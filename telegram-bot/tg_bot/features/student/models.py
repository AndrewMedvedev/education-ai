from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tg_bot.core.database import Base


class Group(Base):
    __tablename__ = "groups"

    course_id: Mapped[UUID]
    teacher_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str]
    is_active: Mapped[bool]

    students: Mapped[list["Student"]] = relationship(back_populates="group")


class Student(Base):
    __tablename__ = "students"

    group_id: Mapped[UUID] = mapped_column(ForeignKey("groups.id"), unique=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    full_name: Mapped[str]
    login: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str] = mapped_column(unique=True)
    is_active: Mapped[bool]

    group: Mapped["Group"] = relationship(back_populates="students")
    progress: Mapped["StudentProgress"] = relationship(back_populates="student")


class StudentProgress(Base):
    __tablename__ = "students_progress"

    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), unique=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_score: Mapped[float]
    current_module_id: Mapped[UUID]
    overall_percentage: Mapped[float]

    student: Mapped["Student"] = relationship(back_populates="progress")
