# ruff: file-ignore[no-self-use,unused-method-argument]

from __future__ import annotations

from typing import Any

from dataclasses import asdict

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeDecorator

from ..domain.constants import _BLOCK_REGISTRY, ExtendedContentType
from ..domain.entities import AnyContentBlock, QuizBlock


def block_from_dict(data: dict[str, Any]) -> AnyContentBlock:
    content_type = ExtendedContentType(data["content_type"])
    block_cls = _BLOCK_REGISTRY[content_type]

    kwargs = dict(data)
    kwargs["content_type"] = content_type

    if block_cls is QuizBlock and "questions" in kwargs:
        kwargs["questions"] = [tuple(q) for q in kwargs["questions"]]

    return block_cls(**kwargs)


class ContentBlockListType(TypeDecorator):
    """Хранит list[AnyContentBlock] как JSONB, отдаёт настоящие датаклассы."""

    impl = JSONB
    cache_ok = True

    def process_bind_param(
        self,
        value: list[AnyContentBlock] | None,
        dialect: Dialect,
    ) -> list[dict] | None:
        # Python -> JSON перед записью в базу
        """Обрабатывает bind param, чтобы подготовить данные для следующего этапа."""
        if value is None:
            return value
        return [asdict(block) for block in value]

    def process_result_value(
        self,
        value: list[dict] | None,
        dialect: Dialect,
    ) -> list[AnyContentBlock] | None:
        # JSON -> Python после чтения из базы
        """Обрабатывает result value, чтобы подготовить данные для следующего этапа."""
        if value is None:
            return value
        return [block_from_dict(b) for b in value]
