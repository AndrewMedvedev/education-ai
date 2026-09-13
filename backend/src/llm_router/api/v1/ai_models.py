from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.iam.dependencies import require_permissions
from src.iam.dependencies.identity import CurrentIdentity
from src.shared.application.dtos import Page, Pagination

from ...dependencies import AIModelsRepoDep, DBSession
from ...domain.dataclass import AIModel
from ...domain.permissions.ai_models import CREATE, DELETE
from ...schemas import AIModelSchema

router = APIRouter(prefix="/ai-models", tags=["AI Models"])


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(CREATE.code))],
)
async def add_model(
    schema: AIModelSchema,
    repository: AIModelsRepoDep,
    session: DBSession,
) -> AIModel:
    """Обрабатывает HTTP-запрос `add_model` и связывает API с сервисным слоем."""
    result = await repository.create(
        AIModel(name=schema.name, description=schema.description, context=schema.context)
    )
    await session.commit()
    return result


@router.post(
    "/get",
    response_model=Page[AIModel],
    summary="Список AI-моделей",
    status_code=status.HTTP_200_OK,
)
async def get_models(
    params: Pagination,
    repository: AIModelsRepoDep,
    _identity: CurrentIdentity,
) -> Page[AIModel]:
    """Получает models, чтобы вызывающий код работал через единый интерфейс."""
    return await repository.find(params)


@router.delete(
    "/{uid}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions(DELETE.code))],
)
async def delete_model(
    uid: UUID,
    session: DBSession,
    repository: AIModelsRepoDep,
) -> None:
    """Обрабатывает HTTP-запрос `delete_model` и связывает API с сервисным слоем."""
    await repository.delete(uid)
    await session.commit()
