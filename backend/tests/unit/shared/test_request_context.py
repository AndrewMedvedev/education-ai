import asyncio
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, Request, status
from fastapi.testclient import TestClient

from src.shared.infra.middlewares import (
    LoggingMiddleware,
    add_request_id_to_outgoing_request,
)
from src.shared.infra.request_context import get_request_id, reset_request_id, set_request_id


def _create_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)

    @app.get("/request-id")
    async def read_request_id(_: Request) -> dict[str, str | None]:
        request_id = get_request_id()
        return {"context": str(request_id) if request_id else None}

    return app


def test_middleware_preserves_valid_request_id() -> None:
    request_id = str(uuid4())

    with TestClient(_create_app()) as client:
        response = client.get("/request-id", headers={"X-Request-ID": request_id})

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["X-Request-ID"] == request_id
    assert response.json() == {"context": request_id}


def test_middleware_replaces_invalid_request_id() -> None:
    with TestClient(_create_app()) as client:
        response = client.get("/request-id", headers={"X-Request-ID": "not-a-uuid"})

    generated_request_id = response.headers["X-Request-ID"]
    assert str(UUID(generated_request_id)) == generated_request_id
    assert response.json() == {"context": generated_request_id}


async def _read_isolated_context(request_id: str) -> str | None:
    token = set_request_id(request_id)
    try:
        await asyncio.sleep(0)
        return get_request_id()
    finally:
        reset_request_id(token)


@pytest.mark.asyncio
async def test_request_id_is_isolated_between_tasks() -> None:
    first_id = str(uuid4())
    second_id = str(uuid4())

    assert await asyncio.gather(
        _read_isolated_context(first_id),
        _read_isolated_context(second_id),
    ) == [first_id, second_id]


@pytest.mark.asyncio
async def test_shared_http_client_forwards_request_id() -> None:
    request_id = str(uuid4())
    token = set_request_id(request_id)
    params = SimpleNamespace(headers={})

    try:
        await add_request_id_to_outgoing_request(None, None, params)  # type: ignore[arg-type]
    finally:
        reset_request_id(token)

    assert params.headers == {"X-Request-ID": request_id}
