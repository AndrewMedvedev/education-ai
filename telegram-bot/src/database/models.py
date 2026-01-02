from typing import Any

from uuid import UUID

from sqlalchemy import JSON, BigInteger, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class CourseModel(Base):
    __tablename__ = "courses"

    title: Mapped[str]
    description: Mapped[str] = mapped_column(Text)
    discipline: Mapped[str]
    creator_id: Mapped[int] = mapped_column(BigInteger)

    modules: Mapped[list["ModuleModel"]] = relationship(back_populates="course")


class ModuleModel(Base):
    __tablename__ = "modules"

    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), unique=False)
    title: Mapped[str]
    description: Mapped[str] = mapped_column(Text)
    order: Mapped[int]
    content_blocks: Mapped[dict[str, Any]] = mapped_column(JSON)
    dependencies: Mapped[list[UUID]] = mapped_column(JSON)

    course: Mapped["CourseModel"] = relationship(back_populates="modules")
    assessments: Mapped[list["AssessmentModel"]] = relationship(back_populates="module")


class AssessmentModel(Base):
    __tablename__ = "assessments"

    module_id: Mapped[UUID] = mapped_column(ForeignKey("modules.id"), unique=False)
    assessment_type: Mapped[str]
    title: Mapped[str]
    description: Mapped[str] = mapped_column(Text)
    verification_rules: Mapped[dict[str, Any]] = mapped_column(JSON)

    module: Mapped["ModuleModel"] = relationship(back_populates="assessments")
