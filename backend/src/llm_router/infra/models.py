from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class AIModelOrm(Base):
    __tablename__ = "ai_models"

    name: Mapped[str] = mapped_column(nullable=False, unique=True)
    description: Mapped[str] = mapped_column(nullable=False)
    context: Mapped[int] = mapped_column(nullable=False)
