"""
Регистрация FastAPI роутеров из всех модулей.
"""

# ruff: file-ignore[non-empty-init-module,unused-import]
from fastapi import APIRouter

from src.core import dramatiq

from .courses.api.v1 import router as courses_router
from .iam.api.v1 import router as iam_router
from .llm_router.api.v1 import router as llm_router
from .media.router import router as media_router
from .organization.api.v1 import router as organization_router

router = APIRouter(prefix="/api/v1")

router.include_router(iam_router)
router.include_router(organization_router)
router.include_router(media_router)
router.include_router(courses_router)
router.include_router(llm_router)


__all__ = ["router"]
