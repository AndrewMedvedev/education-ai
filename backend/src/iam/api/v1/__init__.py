from fastapi import APIRouter

from . import auth, invitations, oauth, permissions, roles, service_accounts, users

router = APIRouter()

router.include_router(auth.router)
router.include_router(service_accounts.router)
router.include_router(oauth.router)
router.include_router(invitations.router)
router.include_router(permissions.router)
router.include_router(roles.router)
router.include_router(users.router)
