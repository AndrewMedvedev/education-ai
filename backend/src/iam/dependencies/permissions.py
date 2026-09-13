from typing import Annotated

from collections.abc import Callable

from fastapi import Depends

from src.iam.application.dtos import Identity, PermissionQueryParamFilters, PermissionResponse
from src.iam.domain.exceptions import PermissionDeniedError
from src.shared.application.dtos import Page
from src.shared.dependencies import PaginationDep

from .identity import CurrentIdentity
from .repos import PermissionRepositoryDep


async def get_permission_list(
    permission_repo: PermissionRepositoryDep,
    pagination: PaginationDep,
    filters: Annotated[PermissionQueryParamFilters, Depends()],
) -> Page[PermissionResponse]:
    permission_page = await permission_repo.find(pagination, filters)
    return permission_page.to_response(PermissionResponse.model_validate)


def require_permissions(*permissions: str, any_of: bool = True) -> Callable[[Identity], Identity]:
    """
    Создаёт FastAPI dependency для проверки permissions текущего Identity.

    При `any_of=True` достаточно одного из указанных permissions.
    При `any_of=False` Identity должен обладать всеми permissions.
    """

    if not permissions:
        raise ValueError("At leat one permissions must be provided.")

    required = set(permissions)

    def dependency(identity: CurrentIdentity) -> Identity:

        granted = identity.permissions

        if any_of:
            if required.isdisjoint(granted):
                raise PermissionDeniedError(
                    "At least one of the following permissions is required: "
                    f"{', '.join(sorted(required))}."
                )

            return identity

        missing = required - granted
        if missing:
            raise PermissionDeniedError(
                f"The following permissions are required: {', '.join(sorted(missing))}."
            )

        return identity

    return dependency
