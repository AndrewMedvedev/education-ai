from typing import Any

import asyncio
import logging
from functools import partial

from headroom import compress

from src.core.others import thread_executor, tokens_encoder
from src.llm_service import BaseAgentMiddleware
from src.llm_service.protocols import LLMTextServiceProtocol
from src.llm_service.schemas import ToolCallParsed

logger = logging.getLogger(__name__)

MIN_TOKENS = 800
MIN_SAVING_RATIO = 0.1


class ToolOutputCompressionMiddleware(BaseAgentMiddleware):
    def __init__(
        self,
        model: str = "gpt-4o",
    ) -> None:
        self.model = model

    async def _compressed_async(self, output: str):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            thread_executor,
            partial(
                compress,
                [{"role": "tool", "content": output}],
                model=self.model,
            ),
        )

    async def wrap_tool_call(
        self,
        service: LLMTextServiceProtocol,  # noqa: ARG002
        tool: ToolCallParsed,
        handler,
    ) -> dict[str, Any]:
        result = await handler(tool)
        output = result.get("output")

        if not isinstance(output, str):
            return result

        before_tokens = len(tokens_encoder.encode(text=output))

        if before_tokens < MIN_TOKENS:
            return result

        compressed = await self._compressed_async(output)

        compressed_output = compressed.messages[0]["content"]
        after_tokens = len(tokens_encoder.encode(text=compressed_output))

        if after_tokens >= before_tokens:
            return result

        saving_ratio = (before_tokens - after_tokens) / before_tokens

        if saving_ratio < MIN_SAVING_RATIO:
            return result

        logger.info(
            "Headroom compressed tool output: tool=%s before=%s after=%s saved=%s ratio=%.2f",
            tool.name,
            before_tokens,
            after_tokens,
            before_tokens - after_tokens,
            saving_ratio,
        )

        return {
            **result,
            "output": compressed_output,
        }
