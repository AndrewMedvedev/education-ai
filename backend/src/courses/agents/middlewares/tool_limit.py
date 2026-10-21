from typing import Any

import json
import logging
from collections.abc import Awaitable, Callable

from src.llm_service import (
    BaseAgentMiddleware,
    LLMTextServiceProtocol,
)
from src.llm_service.schemas import ToolCallParsed

logger = logging.getLogger(__name__)


class ToolCallLimitMiddleware(BaseAgentMiddleware):
    def __init__(self, tool_limits: dict[str, int]) -> None:
        self.tool_limits = dict(tool_limits)

    @staticmethod
    def _is_tool_error(result: dict[str, Any]) -> bool:
        output = result.get("output")
        if not isinstance(output, str):
            return False
        try:
            parsed = json.loads(output)
        except (json.JSONDecodeError, TypeError):
            return False
        return isinstance(parsed, dict) and "error" in parsed

    async def wrap_tool_call(
        self,
        service: LLMTextServiceProtocol,
        tool: ToolCallParsed,
        handler: Callable[[ToolCallParsed], Awaitable[dict]],
    ) -> dict:
        if tool.name in self.tool_limits:
            if self.tool_limits[tool.name] > 0:
                result = await handler(tool)
                if not self._is_tool_error(result):
                    self.tool_limits[tool.name] -= 1
                return result
            callable_func = service.tools[tool.name]  # pyright: ignore[reportOptionalSubscript]
            logger.info("The tool %s call has reached the limit", tool.name)
            return callable_func.to_tool_result(
                call_id=tool.call_id,
                result=f"The tool's call limit is exhausted, do not call again {tool.name}.",
            )
        return await super().wrap_tool_call(service, tool, handler)
