"""
Регистрация FastAPI роутеров из всех модулей.
"""

from fastapi import APIRouter

from src.core.settings import ENV_FILE  # noqa: F401

from .courses.api.v1 import router as courses_router
from .iam.api.v1 import router as iam_router
from .feedback.api.v1.feedback import router as feedback_router
from .llm_router.api.v1 import router as llm_router
from .llm_router.infra import invocation_rabbit as llm_invocation_events  # noqa: F401
from .media.api.v1 import router as media_router
from .notifications.api.v1 import router as notifications_router
from .organization.api.v1 import router as organization_router

router = APIRouter(prefix="/api/v1")

router.include_router(iam_router)
router.include_router(notifications_router)
router.include_router(organization_router)
router.include_router(media_router)
router.include_router(courses_router)
router.include_router(llm_router)
router.include_router(feedback_router)


__all__ = ["router"]
