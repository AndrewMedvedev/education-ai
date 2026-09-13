from typing import Annotated

from fastapi import Depends
from openai import AsyncOpenAI

from src.core.providers import aitunnel_config, proxy_api_config
from src.shared.dependencies.database import DBSession

from .infra.repository import SqlAIModelRepository
from .services import LLMImageRouter, LLMTextRouter
from .utils import cache_ai_models

text_client = AsyncOpenAI(
    api_key=aitunnel_config.key,
    base_url=aitunnel_config.base_url,
    max_retries=0,
    timeout=340,
)

image_client = AsyncOpenAI(
    api_key=proxy_api_config.key,
    base_url=proxy_api_config.base_url,
    max_retries=0,
    timeout=340,
)


def get_ai_model_repo(session: DBSession) -> SqlAIModelRepository:
    """Получает ai model repo, чтобы вызывающий код работал через единый интерфейс."""
    return SqlAIModelRepository(session)


AIModelsRepoDep = Annotated[SqlAIModelRepository, Depends(get_ai_model_repo)]


def get_llm_image_router(repository: AIModelsRepoDep) -> LLMImageRouter:
    """Получает llm image router, чтобы вызывающий код работал через единый интерфейс."""
    return LLMImageRouter(
        ai_model_repos=repository,
        client=text_client,
        image_client=image_client,
        wrapper=cache_ai_models,
    )


def get_llm_text_router(repository: AIModelsRepoDep) -> LLMTextRouter:
    """Получает llm text router, чтобы вызывающий код работал через единый интерфейс."""
    return LLMTextRouter(ai_model_repos=repository, client=text_client, wrapper=cache_ai_models)


LLMTextRouterDep = Annotated[LLMTextRouter, Depends(get_llm_text_router)]

LLMImageRouterDep = Annotated[LLMImageRouter, Depends(get_llm_image_router)]
