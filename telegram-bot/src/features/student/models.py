from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


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
