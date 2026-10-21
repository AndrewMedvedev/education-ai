from typing import Any

from uuid import UUID

from sqlalchemy import CheckConstraint, Enum, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.llm_router.domain.enums import Complexity

from ..domain.dataclass import LLMInvocationStatus


class AIModelOrm(Base):
    __tablename__ = "ai_models"

    name: Mapped[str] = mapped_column(nullable=False, unique=True)
    description: Mapped[str] = mapped_column(nullable=False)
    complexity: Mapped[Complexity] = mapped_column(Enum(Complexity))
    context: Mapped[int] = mapped_column(nullable=False)


class LLMInvocationOrm(Base):
    __tablename__ = "llm_invocations"

    request_id: Mapped[UUID] = mapped_column(nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    total_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    request: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    response: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    duration_ms: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    status: Mapped[LLMInvocationStatus] = mapped_column(
        Enum(LLMInvocationStatus),
        nullable=False,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (
        CheckConstraint(
            "total_tokens >= 0",
            name="ck_llm_invocations_tokens_non_negative",
        ),
        Index("ix_llm_invocations_request_id", "request_id"),
    )
