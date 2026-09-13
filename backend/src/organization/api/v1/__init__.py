from fastapi import APIRouter

from . import organization

router = APIRouter()

router.include_router(organization.router)
