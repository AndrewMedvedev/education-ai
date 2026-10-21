import logging
from collections.abc import Callable
from functools import wraps
from time import perf_counter
from uuid import uuid4

from src.llm_service.schemas import (
    LLMImageRequest,
    LLMImageResponse,
    LLMTextRequest,
    LLMTextResponse,
)
from src.shared.infra.request_context import get_request_id

from .domain.events import LLMInvocationCreated
from .domain.vo import LLMInvocationStatus

logger = logging.getLogger(__name__)


def track_text_invocation(func: Callable) -> Callable:
    """Публикует мониторинг вызова текстовой модели."""

    @wraps(func)
    async def wrapper(
        self,
        model: str,
        schema: LLMTextRequest,
    ) -> LLMTextResponse:
        started_at = perf_counter()
        request_id = get_request_id() or uuid4()
        request = schema.model_dump(mode="json", by_alias=True, exclude_none=True)

        try:
            result = await func(self, model=model, schema=schema)
        except Exception as error:
            await self._publish_invocation(
                LLMInvocationCreated(
                    request_id=request_id,
                    model=model,
                    total_tokens=0,
                    request=request,
                    response={},
                    duration_ms=round((perf_counter() - started_at) * 1000),
                    status=LLMInvocationStatus.FAILED,
                    error=str(error),
                )
            )
            logger.exception("LLM text invocation failed")
            raise

        await self._publish_invocation(
            LLMInvocationCreated(
                request_id=request_id,
                model=model,
                total_tokens=result.total_tokens,
                request=request,
                response=result.model_dump(mode="json", exclude_none=True),
                duration_ms=round((perf_counter() - started_at) * 1000),
                status=LLMInvocationStatus.COMPLETED,
            )
        )
        return result

    return wrapper


def track_image_invocation(func: Callable) -> Callable:
    """Публикует мониторинг вызова модели изображений."""

    @wraps(func)
    async def wrapper(
        self,
        model: str,
        schema: LLMImageRequest,
    ) -> LLMImageResponse:
        started_at = perf_counter()
        request_id = get_request_id() or uuid4()
        request = schema.model_dump(mode="json", by_alias=True, exclude_none=True)
        result = None

        try:
            result = await func(self, model=model, schema=schema)
            duration_ms = round((perf_counter() - started_at) * 1000)
            result.image = await self._media_client.save_image(result.image, folder="llm-outputs")
        except Exception as error:
            await self._publish_invocation(
                LLMInvocationCreated(
                    request_id=request_id,
                    model=model,
                    total_tokens=result.total_tokens if result is not None else 0,
                    request=request,
                    response={},
                    duration_ms=round((perf_counter() - started_at) * 1000),
                    status=LLMInvocationStatus.FAILED,
                    error=str(error),
                )
            )
            logger.exception("LLM image invocation failed")
            raise

        await self._publish_invocation(
            LLMInvocationCreated(
                request_id=request_id,
                model=model,
                total_tokens=result.total_tokens,
                request=request,
                response=result.model_dump(mode="json", exclude_none=True),
                duration_ms=duration_ms,
                status=LLMInvocationStatus.COMPLETED,
            )
        )
        return result

    return wrapper
