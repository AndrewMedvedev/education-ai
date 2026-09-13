from __future__ import annotations

from typing import Any

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    TEXT,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

from ..domain.entities import (
    AnyContentBlock,
)
from ..domain.vo import (
    CourseStatus,
    DifficultyLevel,
    DocumentNodeType,
    PracticeStatus,
)
from .types import ContentBlockListType


class CourseOrm(Base):
    __tablename__ = "courses"

    title: Mapped[str]
    description: Mapped[str] = mapped_column(TEXT)
    difficulty: Mapped[DifficultyLevel] = mapped_column(Enum(DifficultyLevel))
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    status: Mapped[CourseStatus] = mapped_column(Enum(CourseStatus))
    popularity: Mapped[int] = mapped_column(Integer, default=0)
    creator_id: Mapped[UUID]
    image_url: Mapped[str | None] = mapped_column(nullable=True)
    learning_objectives: Mapped[list[str]] = mapped_column(JSONB, default=list)

    modules: Mapped[list[ModuleOrm]] = relationship(
        back_populates="course",
        order_by="ModuleOrm.id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    students: Mapped[list[StudentOrm]] = relationship(back_populates="course")


class ModuleOrm(Base):
    __tablename__ = "modules"

    course_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=True
    )
    title: Mapped[str]
    description: Mapped[str] = mapped_column(TEXT)
    order: Mapped[int | None] = mapped_column(nullable=True)
    learning_objectives: Mapped[list[str]] = mapped_column(JSONB, default=list)

    course: Mapped[CourseOrm | None] = relationship(back_populates="modules")
    lessons: Mapped[list[LessonOrm]] = relationship(
        back_populates="module",
        order_by="LessonOrm.id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (Index("ix_modules_course_id", "course_id"),)


class LessonOrm(Base):
    __tablename__ = "lessons"

    module_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("modules.id", ondelete="CASCADE"), nullable=True
    )
    title: Mapped[str]
    description: Mapped[str] = mapped_column(TEXT)
    order: Mapped[int | None] = mapped_column(nullable=True)
    learning_objectives: Mapped[list[str]] = mapped_column(JSONB, default=list)
    estimated_time_minutes: Mapped[int | None] = mapped_column(nullable=True)
    content_blocks: Mapped[list[AnyContentBlock]] = mapped_column(
        ContentBlockListType,
        default=list,
    )

    module: Mapped[ModuleOrm | None] = relationship(back_populates="lessons")

    __table_args__ = (Index("ix_lessons_module_id", "module_id"),)


class LessonTheorySessionOrm(Base):
    __tablename__ = "lesson_theory_sessions"

    __table_args__ = (
        CheckConstraint(
            "active_time_seconds >= 0",
            name="ck_lesson_theory_session_active_time_non_negative",
        ),
        CheckConstraint(
            "max_scroll_depth_percent BETWEEN 0 AND 100",
            name="ck_lesson_theory_session_scroll_depth_range",
        ),
    )

    lesson_id: Mapped[UUID] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID]
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    active_time_seconds: Mapped[int] = mapped_column(default=0)
    max_scroll_depth_percent: Mapped[int] = mapped_column(default=0)


class ChatOrm(Base):
    __tablename__ = "chats"

    user_id: Mapped[UUID]
    course_id: Mapped[UUID]
    messages: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)


class StudentOrm(Base):
    __tablename__ = "students"

    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"))
    user_id: Mapped[UUID]

    course: Mapped[CourseOrm] = relationship(back_populates="students")

    __table_args__ = (
        UniqueConstraint("course_id", "user_id", name="uq_student"),
        Index("ix_students_user_id", "user_id"),
    )


class DocumentOrm(Base):
    __tablename__ = "documents"

    owner_id: Mapped[UUID] = mapped_column(nullable=False)

    # ── Дерево ────────────────────────────────────────────────────────────────
    parent_node_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    node_type: Mapped[DocumentNodeType] = mapped_column(index=True)

    # Заголовок (для TOC + HEADING)
    title: Mapped[str | None] = mapped_column(TEXT, index=True)

    # Текст (только для TEXT leaf-узлов)
    content: Mapped[str | None] = mapped_column(TEXT)

    # ── Relations ─────────────────────────────────────────────────────────────

    # FIX 1: Mapped[Optional[...]] — parent_node может быть None у TOC-корня.
    # FIX 2: foreign_keys явно указан, иначе SQLAlchemy выбрасывает
    #         AmbiguousForeignKeysError для self-referential таблиц.
    parent_node: Mapped[DocumentOrm | None] = relationship(
        "DocumentOrm",
        remote_side="DocumentOrm.id",
        back_populates="children",
        foreign_keys="[DocumentOrm.parent_node_id]",
    )

    # FIX 3: passive_deletes=True — доверяем CASCADE на уровне БД.
    #         Без него SQLAlchemy загружает всё дерево потомков в память
    #         и удаляет по одному (катастрофа для больших деревьев).
    # FIX 2 (продолжение): foreign_keys обязателен и здесь.
    children: Mapped[list[DocumentOrm]] = relationship(
        "DocumentOrm",
        back_populates="parent_node",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="[DocumentOrm.parent_node_id]",
    )

    # ── Indexes & constraints ──────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_doc_owner_parent", "owner_id", "parent_node_id"),
        Index("ix_doc_owner_type", "owner_id", "node_type"),
        # FIX 4: Защита только от прямой самоссылки — циклы A→B→A
        #         не покрываются; полная защита требует триггера или
        #         проверки на уровне приложения (см. pipeline ниже).
        CheckConstraint("id != parent_node_id", name="ck_no_self_parent"),
    )


class PracticeOrm(Base):
    __tablename__ = "practices"

    user_id: Mapped[UUID]
    module_id: Mapped[UUID]
    lesson_id: Mapped[UUID]
    status: Mapped[PracticeStatus] = mapped_column(Enum(PracticeStatus))

    practice: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
