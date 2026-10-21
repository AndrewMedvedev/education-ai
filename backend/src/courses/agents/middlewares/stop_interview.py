import logging

from src.llm_service import (
    BaseAgentMiddleware,
    LLMServiceProtocol,
    LLMTextResponse,
)

logger = logging.getLogger(__name__)


class StopInterview(BaseAgentMiddleware):
    async def after_model(
        self,
        service: LLMServiceProtocol,
        response: LLMTextResponse,
    ) -> LLMTextResponse:
        task_id = self._get_task_id(service)
        if task_id:
            logger.info("Interview completed, task_id=%s", task_id)
            response.tool_calls = []  # останавливает рекурсию в _process_response
            response.raw_text = {"task_id": task_id}  # прячем payload в уже существующее поле
        return response

    @staticmethod
    def _get_task_id(service: LLMServiceProtocol) -> str | None:
        runtime = service.runtime
        if runtime is None or runtime.state is None:
            return None
        return getattr(runtime.state, "task_id", None)
