from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class OrganizationOrm(Base):
    __tablename__ = "organizations"

    name: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str]
    is_active: Mapped[bool]
