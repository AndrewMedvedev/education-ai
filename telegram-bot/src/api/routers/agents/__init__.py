__all__ = ["router"]

from fastapi import APIRouter

from .course_generator import router as course_generator_router

router = APIRouter(prefix="/agents", tags=["🤖 AI Agents"])

router.include_router(course_generator_router)
