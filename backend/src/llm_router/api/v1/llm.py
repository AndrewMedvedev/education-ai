from __future__ import annotations

from fastapi import APIRouter

from src.iam.dependencies.identity import CurrentIdentity
from src.llm_service import LLMImageRequest, LLMImageResponse, LLMTextRequest, LLMTextResponse

from ...dependencies import LLMImageRouterDep, LLMTextRouterDep

router = APIRouter(prefix="/responses", tags=["LLM Router"])


@router.post(
    path="/text",
    summary="Получить текстовый ответ от AI-модели",
    description="Отправляет текстовый запрос выбранной AI-модели и возвращает сгенерированный ответ.",
)
async def invoke_text(
    schema: LLMTextRequest,
    service: LLMTextRouterDep,
    _identity: CurrentIdentity,
    model: str | None = None,
) -> LLMTextResponse:
    """Обрабатывает HTTP-запрос `invoke_text` и связывает API с сервисным слоем."""
    return await service.call_llm(schema=schema, model=model)


@router.post(
    path="/image",
    summary="Сгенерировать изображение с помощью AI-модели",
    description="Отправляет запрос на генерацию изображения выбранной AI-модели и возвращает результат.",
)
async def invoke(
    schema: LLMImageRequest,
    service: LLMImageRouterDep,
    _identity: CurrentIdentity,
    model: str | None = None,
) -> LLMImageResponse:
    """Запускает обращение к сервису и возвращает обработанный результат."""
    return await service.call_llm(schema=schema, model=model)
