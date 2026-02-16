from fastapi import APIRouter, Depends, status

from src.app.schemas import CurrentUser

from ..dependencies import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    path="/me",
    status_code=status.HTTP_200_OK,
    response_model=CurrentUser,
    summary="Получит информацию о себе"
)
async def get_me(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return current_user
