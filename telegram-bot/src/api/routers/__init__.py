__all__ = ["router"]

from fastapi import APIRouter

from .courses import router as courses_router

router = APIRouter(prefix="/api/v1")

router.include_router(courses_router)
