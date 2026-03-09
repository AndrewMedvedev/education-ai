from typing import Any

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import ARRAY, TEXT, BigInteger, Date, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.entities.student import ModuleProgress
from src.infra.db.base import Base


class UserOrm(Base):
    __tablename__ = "users"
    __mapper_args__ = {  # noqa: RUF012
        "polymorphic_on": "role",
        "polymorphic_identity": "user",
        "with_polymorphic": "*",
    }

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(unique=True, nullable=True)
    role: Mapped[str]


class StudentOrm(UserOrm):
    __mapper_args__ = {"polymorphic_identity": "student"}  # noqa: RUF012

    group_id: Mapped[UUID | None] = mapped_column(ForeignKey("groups.id"), nullable=True)
    full_name: Mapped[str | None] = mapped_column(nullable=True)

    group: Mapped["GroupOrm"] = relationship(back_populates="students")
    learning_progress: Mapped["LearningProgressOrm"] = relationship(back_populates="student")


class TeacherOrm(UserOrm):
    __mapper_args__ = {"polymorphic_identity": "teacher"}  # noqa: RUF012

    password_hash: Mapped[str | None] = mapped_column(unique=True, nullable=True)


AnyUserOrm = StudentOrm | TeacherOrm


class GroupOrm(Base):
    __tablename__ = "groups"

    course_id: Mapped[UUID]
    title: Mapped[str]

    students: Mapped[list["StudentOrm"]] = relationship(back_populates="group")


class CourseOrm(Base):
    __tablename__ = "courses"

    creator_id: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str]
    image_url: Mapped[str | None] = mapped_column(nullable=True)
    title: Mapped[str]
    description: Mapped[str]
    learning_objectives: Mapped[list[str]] = mapped_column(ARRAY(String))
    modules: Mapped[list["ModuleOrm"]] = relationship(
        back_populates="course", lazy="selectin", order_by="ModuleOrm.order"
    )
    final_assessment: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class ModuleOrm(Base):
    __tablename__ = "modules"

    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), unique=False)
    title: Mapped[str]
    description: Mapped[str] = mapped_column(TEXT)
    learning_objectives: Mapped[list[str]] = mapped_column(ARRAY(String))
    order: Mapped[int]
    content_blocks: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    assignment: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    course: Mapped["CourseOrm"] = relationship(back_populates="modules")


class LearningProgressOrm(Base):
    __tablename__ = "learning_progress"

    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    course_id: Mapped[UUID]
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_score: Mapped[float]
    current_module_id: Mapped[UUID | None] = mapped_column(nullable=True)
    score_per_module: Mapped[dict[str, ModuleProgress]] = mapped_column(JSONB)

    student: Mapped["StudentOrm"] = relationship(back_populates="learning_progress")


class StudentTaskOrm(Base):
    __tablename__ = "student_tasks"

    student_id: Mapped[int] = mapped_column(BigInteger)
    module_id: Mapped[UUID]
    assignment: Mapped[dict[str, Any]] = mapped_column(JSONB)
    submission_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_finished: Mapped[bool]


class DailyChatLimitOrm(Base):
    """Модель для лимитирования количества сообщений в день для чата с ИИ.
    По умолчанию максимум 10 сообщений в день.
    """

    __tablename__ = "daily_chat_limits"

    user_id: Mapped[int] = mapped_column(BigInteger)
    date: Mapped[date] = mapped_column(Date)
    max_count: Mapped[int]
    current_count: Mapped[int]
