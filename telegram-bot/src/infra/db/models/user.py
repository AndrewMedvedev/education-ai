from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class UserOrm(Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(unique=True)
    full_name: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str] = mapped_column(unique=True)
    role: Mapped[str]
    is_active: Mapped[bool]
