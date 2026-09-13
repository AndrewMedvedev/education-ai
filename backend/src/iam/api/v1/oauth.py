from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.iam.application.dtos import OAuthCredentials, OAuthTokenResponse
from src.iam.dependencies.services import OAuthServiceDep

router = APIRouter(prefix="/oauth", tags=["OAuth | Machine2Machine"])


@router.post(
    path="/token",
    status_code=status.HTTP_200_OK,
    summary="Получить токен",
)
async def issue_token(
        credentials: Annotated[OAuthCredentials, Depends()],
        service: OAuthServiceDep,
) -> OAuthTokenResponse:
    return await service.issue_token(credentials)
