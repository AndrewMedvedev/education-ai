from fastapi import APIRouter, status

router = APIRouter(prefix="/media", tags=["Media"])


@router.post(
    path="/upload",
    status_code=status.HTTP_201_CREATED,
)
async def upload() -> ...: ...
