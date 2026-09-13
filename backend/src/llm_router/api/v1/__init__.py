from fastapi import APIRouter

from . import ai_models, llm

router = APIRouter()

router.include_router(llm.router)
router.include_router(ai_models.router)
