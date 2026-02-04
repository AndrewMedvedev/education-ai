from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Student(Base):
    __tablename__ = "students"

    user_id: Mapped[int] = mapped_column(BigInteger)
    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), unique=False)
    invited_by: Mapped[int] = mapped_column(BigInteger)
    login: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str] = mapped_column(unique=True)
    is_active: Mapped[bool]
