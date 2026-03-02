__all__ = ["router"]

from aiogram import Router

from .leaderboard import router as leaderboard_router
from .profile import router as profile_router
from .sign_up import router as sign_up_router
from .start import router as start_router
from .study import router as study_router

router = Router()

router.include_routers(
    start_router,
    sign_up_router,
    study_router,
    profile_router,
    leaderboard_router,
)
