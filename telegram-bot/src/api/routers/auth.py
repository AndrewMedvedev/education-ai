from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from src.app.schemas import TokensPair, UserRegister, UserResponse
from src.app.services.auth import AuthService
from src.infra.db.repos import UserRepository
from src.utils.secutiry import decode_token

from ..dependencies import get_user_repo

router = APIRouter(prefix="/auth", tags=["Auth"])


def get_auth_service(repository: UserRepository = Depends(get_user_repo)) -> AuthService:
    return AuthService(repository)


@router.post(
    path="/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
    summary="Регистрирует нового пользователя"
)
async def register(
        user: UserRegister, service: AuthService = Depends(get_auth_service)
) -> UserResponse:
    return await service.register(user)


@router.post(
    path="/login",
    status_code=status.HTTP_200_OK,
    response_model=TokensPair,
    summary="Аутентификация пользователя"
)
async def login(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        service: AuthService = Depends(get_auth_service)
) -> TokensPair:
    return await service.authenticate(form_data.username, form_data.password)


@router.post(
    path="/verify",
    status_code=status.HTTP_200_OK,
    summary="Верификация токена"
)
async def verify_token(token: str = Body(..., embed=True)) -> dict[str, Any]:
    return decode_token(token)
