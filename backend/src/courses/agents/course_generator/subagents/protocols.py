from typing import Protocol

from uuid import UUID

from src.courses.agents.schemas import Context
from src.courses.domain.vo import AnyContentBlock, ContentType
from src.courses.infra.services.client import SrvCourseClient
from src.llm_service import LLMTextService
from src.llm_service.schemas import Runtime


class TheoryAgent(Protocol):
    async def __call__(
        self,
        content_type: ContentType,
        context: Context,
        prompt: str,
        client: SrvCourseClient,
    ) -> AnyContentBlock: ...


class ReasonerAgent(Protocol):
    def __call__(
        self,
        runtime: Runtime[Context, SrvCourseClient],
    ) -> LLMTextService: ...


class IndexLesson(Protocol):
    async def kiq(
        self,
        course_id: UUID,
        lesson_id: UUID,
    ) -> None: ...
