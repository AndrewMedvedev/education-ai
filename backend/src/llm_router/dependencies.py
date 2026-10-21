from typing import Annotated

from fastapi import Depends

from src.core.providers import deepseek_client
from src.llm_router.infra.services import llm_router_client
from src.shared.dependencies.database import DBSession
from src.shared.dependencies.events import EventPublisherDep

from .infra.external_apis import MediaClient
from .infra.repository import SqlAIModelRepository, SqlLLMInvocationRepository
from .services import LLMImageRouter, LLMTextRouter
from .utils import cache_ai_models


def get_ai_model_repo(session: DBSession) -> SqlAIModelRepository:
    """Получает ai model repo, чтобы вызывающий код работал через единый интерфейс."""
    return SqlAIModelRepository(session)


AIModelsRepoDep = Annotated[SqlAIModelRepository, Depends(get_ai_model_repo)]


def get_llm_invocation_repo(session: DBSession) -> SqlLLMInvocationRepository:
    """Получает репозиторий записей мониторинга LLM."""
    return SqlLLMInvocationRepository(session)


LLMInvocationRepoDep = Annotated[
    SqlLLMInvocationRepository,
    Depends(get_llm_invocation_repo),
]


async def get_media_client() -> MediaClient:
    return MediaClient(llm_router_client)


MediaClientDep = Annotated[MediaClient, Depends(get_media_client)]


def get_llm_image_router(
    repository: AIModelsRepoDep,
    event_publisher: EventPublisherDep,
    media_client: MediaClientDep,
) -> LLMImageRouter:
    """Получает llm image router, чтобы вызывающий код работал через единый интерфейс."""
    return LLMImageRouter(
        ai_model_repos=repository,
        event_publisher=event_publisher,
        client=deepseek_client,
        image_client=deepseek_client,
        media_client=media_client,
        wrapper=cache_ai_models,
    )


def get_llm_text_router(
    repository: AIModelsRepoDep,
    event_publisher: EventPublisherDep,
) -> LLMTextRouter:
    """Получает llm text router, чтобы вызывающий код работал через единый интерфейс."""
    return LLMTextRouter(
        ai_model_repos=repository,
        event_publisher=event_publisher,
        client=deepseek_client,
        wrapper=cache_ai_models,
    )


LLMTextRouterDep = Annotated[LLMTextRouter, Depends(get_llm_text_router)]

LLMImageRouterDep = Annotated[LLMImageRouter, Depends(get_llm_image_router)]
