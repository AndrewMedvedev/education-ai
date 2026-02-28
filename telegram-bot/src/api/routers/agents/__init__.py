__all__ = ["router"]

from fastapi import APIRouter

from .chatbot import router as chatbot_router

router = APIRouter(prefix="/agents", tags=["🤖 AI Agents"])

router.include_router(chatbot_router)
