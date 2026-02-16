from typing import Any

from uuid import UUID

from sqlalchemy import ARRAY, TEXT, BigInteger, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...core.database import Base


class Course(Base):
    __tablename__ = "courses"

    creator_id: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str]
    image_url: Mapped[str | None] = mapped_column(nullable=True)
    title: Mapped[str]
    description: Mapped[str]
    learning_objectives: Mapped[list[str]] = mapped_column(ARRAY(String))
    modules: Mapped[list["Module"]] = relationship(back_populates="course", lazy="selectin")
    final_assessment: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class Module(Base):
    __tablename__ = "modules"

    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), unique=False)
    title: Mapped[str]
    description: Mapped[str] = mapped_column(TEXT)
    order: Mapped[int]
    content_blocks: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    assignment: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    course: Mapped["Course"] = relationship(back_populates="modules")
