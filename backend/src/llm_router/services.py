# pyright: reportOptionalMemberAccess=false,reportArgumentType=false, reportOptionalSubscript=false,reportAttributeAccessIssue=false


import base64
import logging

from aiohttp import ClientSession
from langsmith import traceable
from openai import (
    AsyncOpenAI,
)
from openai.types.responses.response import Response
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
)

from src.core.providers import aitunnel_config
from src.core.settings import settings
from src.llm_router.infra.external_apis import MediaClient
from src.llm_service.schemas import (
    LLMImageRequest,
    LLMImageResponse,
    LLMTextRequest,
    LLMTextResponse,
)
from src.shared.domain.events import EventPublisher

from .decorators import track_image_invocation, track_text_invocation
from .domain.events import LLMInvocationCreated
from .infra.repository import SqlAIModelRepository
from .schemas import CacheAIModelsProtocol, ClassificationInput
from .utils import (
    is_retryable_error,
    parse_llm_response,
    stop_strategy,
    to_langsmith_llm_output,
    wait_strategy,
)

logger = logging.getLogger(__name__)


PAGINATION_SIZE = 50

BASE_MODEL_CONTEXT = 400000

LLM_RETRY = {
    "retry": retry_if_exception(is_retryable_error),
    "wait": wait_strategy,
    "stop": stop_strategy,
    "reraise": True,
    "before_sleep": before_sleep_log(
        logger,
        logging.WARNING,
    ),
}


class LLMRouter:
    def __init__(
        self,
        ai_model_repos: SqlAIModelRepository,
        event_publisher: EventPublisher,
        client: AsyncOpenAI,
        wrapper: CacheAIModelsProtocol,
    ) -> None:
        self._client = client
        self._ai_model_repos = ai_model_repos
        self._event_publisher = event_publisher
        self._wrapper = wrapper

    async def _publish_invocation(
        self,
        event: LLMInvocationCreated,
    ) -> None:
        """Публикует событие для асинхронного сохранения мониторинга."""
        try:
            await self._event_publisher.publish(event)
            logger.info(
                "LLM invocation published",
                extra={
                    "request_id": str(event.request_id),
                    "model": event.model,
                    "total_tokens": event.total_tokens,
                    "request": event.request,
                    "response": event.response,
                    "duration_ms": event.duration_ms,
                    "status": event.status,
                    "error": event.error,
                },
            )
        except Exception:
            logger.exception(
                "Failed to publish LLM invocation",
                extra={
                    "request_id": str(event.request_id),
                    "model": event.model,
                },
            )

    @retry(**LLM_RETRY)
    @traceable(run_type="chain", name="CallClassification")
    async def _classification_task(self, request: ClassificationInput) -> str:
        async with ClientSession() as session:
            response = await session.post(
                url="https://api.aitunnel.ru/v1/decisions",
                headers={
                    "Authorization": f"Bearer {aitunnel_config.key}",
                    "Content-Type": "application/json",
                },
                json=request.model_dump(
                    exclude_none=True,
                ),
            )
            # result = await self._client.post(
            #     path="/decisions",
            #     cast_to=dict,
            #     body=request.model_dump(
            #         exclude_none=True,
            #     ),
            # )
            response.raise_for_status()
            result = await response.json()
            return result["answers"]["complexity"]["choice"]

    @retry(**LLM_RETRY)
    @traceable(run_type="llm", process_outputs=to_langsmith_llm_output)
    @track_text_invocation
    async def _invoke(
        self,
        model: str,
        schema: LLMTextRequest,
    ) -> LLMTextResponse:
        result: Response = await self._client.responses.create(
            model=model,
            **schema.model_dump(exclude_none=True, by_alias=True),
        )
        return parse_llm_response(
            response=result,
            input_messages=schema.messages,
            text_format=schema.text,
        )


class LLMTextRouter(LLMRouter):
    def __init__(
        self,
        ai_model_repos: SqlAIModelRepository,
        event_publisher: EventPublisher,
        client: AsyncOpenAI,
        wrapper: CacheAIModelsProtocol,
    ) -> None:
        super().__init__(
            ai_model_repos=ai_model_repos,
            event_publisher=event_publisher,
            client=client,
            wrapper=wrapper,
        )

    @traceable(run_type="chain", name="CallTextLLM")
    async def call_llm(
        self,
        schema: LLMTextRequest,
        model: str | None = None,
    ) -> LLMTextResponse:
        # models = (
        #     await self._wrapper(
        #         func=self._ai_model_repos.read_fields, params=Pagination(size=PAGINATION_SIZE)
        #     )
        # ).items
        # if model is None:
        #     classification = await self._classification_task(
        #         ClassificationInput(
        #             model="gpt-6-luna-decisions",
        #             state=ClassificationState(
        #                 messages=schema.messages,
        #                 instructions=schema.instructions,
        #                 tools=schema.tools,
        #                 output=schema.text,
        #             ),
        #         )
        #     )
        #     selected_model = [
        #         item["name"] for item in models if item["complexity"] == classification
        #     ]

        #     return await self._invoke(
        #         model=selected_model[0],
        #         schema=schema,
        #     )
        # selected_model = [
        #     model["name"] for model in models.items if model["complexity"] == Complexity.MEDIUM
        # ]
        return await self._invoke(
            model="deepseek-v4-pro",
            **schema.model_dump(exclude_none=True, by_alias=True),
        )


class LLMImageRouter(LLMRouter):
    def __init__(
        self,
        ai_model_repos: SqlAIModelRepository,
        event_publisher: EventPublisher,
        client: AsyncOpenAI,
        image_client: AsyncOpenAI,
        wrapper: CacheAIModelsProtocol,
        media_client: MediaClient,
    ) -> None:
        self._image_client = image_client
        self._media_client = media_client
        super().__init__(
            ai_model_repos=ai_model_repos,
            event_publisher=event_publisher,
            client=client,
            wrapper=wrapper,
        )

    @track_image_invocation
    @retry(**LLM_RETRY)
    @traceable(run_type="llm", process_outputs=to_langsmith_llm_output)
    async def _invoke_image(
        self,
        model: str,
        schema: LLMImageRequest,
    ) -> LLMImageResponse:
        """Отдельный метод для генерации изображения на основе текста"""
        result = await self._image_client.images.generate(
            model=model,
            **schema.model_dump(exclude_none=True, by_alias=True),
        )
        return LLMImageResponse(
            size=result.size,
            image=result.data[0].b64_json,
            total_tokens=result.usage.total_tokens or 0,
            output_format=result.output_format,
        )

    @track_image_invocation
    @retry(**LLM_RETRY)
    @traceable(run_type="llm", process_outputs=to_langsmith_llm_output)
    async def _invoke_image_based(
        self,
        model: str,
        schema: LLMImageRequest,
    ) -> LLMImageResponse:
        """Отдельный метод для генерации изображения на основе изображения"""
        images = [base64.b64decode(image) for image in schema.image or []]
        request = schema.model_dump(
            exclude_none=True,
            by_alias=True,
            exclude={"image"},
        )
        result = await self._image_client.images.edit(model=model, image=images, **request)
        return LLMImageResponse(
            size=result.size,
            image=result.data[0].b64_json,
            total_tokens=result.usage.total_tokens or 0,
            output_format=result.output_format,
        )

    async def call_llm(
        self,
        schema: LLMImageRequest,
        model: str | None = None,
    ) -> LLMImageResponse:
        if schema.image is not None:
            return await self._invoke_image_based(model=settings.image_ai_model, schema=schema)
        return await self._invoke_image(model=settings.image_ai_model, schema=schema)
