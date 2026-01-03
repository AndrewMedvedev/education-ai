__all__ = ["router"]

from fastapi import APIRouter

from .media import router as media_router

router = APIRouter(prefix="/api/v1", tags=["REST API"])

router.include_router(media_router)
