from typing import Annotated

from fastapi import APIRouter, Body, status

from src.iam.application.dtos import (
    IdentityResponse,
    LoginResponse,
    LogoutRequest,
    TokenRequest,
    TokensResponse,
    UserCredentials,
)
from src.iam.dependencies import CurrentIdentity
from src.iam.dependencies.services import AuthServiceDep

router = APIRouter(prefix="/auth", tags=["Аутентификация | Auth"])


@router.post(
    path="/login",
    status_code=status.HTTP_200_OK,
    response_model=LoginResponse,
    summary="Проверка личности",
)
async def login(credentials: UserCredentials, service: AuthServiceDep) -> LoginResponse:
    return await service.login(credentials)


@router.post(
    path="/token",
    status_code=status.HTTP_200_OK,
    response_model=TokensResponse,
    summary="Получить пару токенов",
)
async def get_token(request: TokenRequest, service: AuthServiceDep) -> TokensResponse:
    return await service.authenticate(request)


@router.post(
    path="/token/refresh",
    status_code=status.HTTP_200_OK,
    response_model=TokensResponse,
    summary="Обновить пару токенов",
)
async def refresh_tokens(
        refresh_token: Annotated[str, Body(description="Refresh токен (долгоживущий)")],
        service: AuthServiceDep,
) -> TokensResponse:
    return await service.refresh_tokens(refresh_token)


@router.post(
    path="/logout",
    status_code=status.HTTP_200_OK,
    summary="Выйти из аккаунта",
)
async def logout(request: LogoutRequest, service: AuthServiceDep) -> TokensResponse:
    return await service.logout(request)


@router.get(
    path="/identity",
    status_code=status.HTTP_200_OK,
    response_model=IdentityResponse,
    summary="Получить текущий авторизованный субъект"
)
async def get_current_identity(identity: CurrentIdentity) -> IdentityResponse:
    return IdentityResponse.model_validate(identity)
