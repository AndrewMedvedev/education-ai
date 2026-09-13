from typing import Annotated, Any

from collections.abc import Callable
from uuid import UUID

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.iam.application.dtos import Identity, IdentityType
from src.iam.application.services import blacklist
from src.iam.domain.exceptions import UnauthorizedError
from src.iam.domain.vo import Email
from src.iam.security import decode_token
from src.shared.infra.cache import Cache

from .repos import get_cache

http_bearer = HTTPBearer(auto_error=False)


def _require_claim[T](payload: dict[str, Any], field: str, expected_type: Callable[[Any], T]) -> T:

    if field not in payload:
        raise UnauthorizedError(f"Missing required claim '{field}'.")

    if not (value := payload[field]):
        raise UnauthorizedError(f"Claim '{field}' cannot be null.")

    try:
        return None if value is None else expected_type(value)
    except (ValueError, TypeError):
        raise UnauthorizedError(f"Invalid claim '{field}' value.") from None


def _build_identity_from_payload(payload: dict[str, Any]) -> Identity:
    """Выполняет парсинг JWT payload и валидирует claims."""

    identity_type = _require_claim(payload, "idt", IdentityType)

    common = {
        "id": _require_claim(payload, "sub", UUID),
        "type": identity_type,
        "organization_id": _require_claim(payload, "org_id", UUID),
        "roles": _require_claim(payload, "roles", frozenset),
        "permissions": _require_claim(payload, "perms", frozenset),
    }

    match identity_type:
        case IdentityType.USER:
            return Identity(
                **common,
                email=_require_claim(payload, "email", Email),
                membership_id=_require_claim(payload, "mid", UUID),
            )
        case IdentityType.SERVICE_ACCOUNT:
            return Identity(**common)

    raise UnauthorizedError(f"Unsupported identity type: {identity_type!r}.")


async def get_current_identity(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)],
        cache: Cache[bool] = Depends(get_cache),
) -> Identity:
    if credentials is None:
        raise UnauthorizedError("Authorization header is missing.")

    payload = decode_token(credentials.credentials)

    jti = payload.get("jti")
    if jti is None:
        raise UnauthorizedError("Missing required jti claim.")

    if await blacklist.is_revoked(jti, cache):
        raise UnauthorizedError("Token was revoked.")

    return _build_identity_from_payload(payload)


require_authentication = Security(get_current_identity)
CurrentIdentity = Annotated[Identity, Depends(get_current_identity)]
