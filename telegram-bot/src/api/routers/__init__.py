__all__ = ["router"]

from fastapi import APIRouter

from .agents import router as agents_router
from .auth import router as auth_router
from .users import router as users_router

router = APIRouter(prefix="/api/v1")

router.include_router(agents_router)
router.include_router(auth_router)
router.include_router(users_router)
