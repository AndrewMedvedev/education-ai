from uuid import UUID

from fastapi import APIRouter, Body, Query, status
from pydantic import PositiveInt

from src.infra.ai.agents.chatbot.agent import call_chatbot

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


@router.post(
    path="",
    status_code=status.HTTP_200_OK,
    summary="Получить ответ от чат-бота"
)
async def generate_response(
        course_id: UUID = Query(..., description="ID курса"),
        user_id: PositiveInt = Body(..., embed=True, description="ID студента"),
        text: str = Body(..., embed=True, description="Текст запроса студента")
) -> dict[str, str]:
    content = await call_chatbot(course_id, user_id, text)
    return {"text": content}
