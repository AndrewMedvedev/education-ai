import logging

import aiohttp
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from .request_context import (
    create_request_id,
    get_request_id,
    reset_request_id,
    set_request_id,
)


def create_request_id_trace_config() -> aiohttp.TraceConfig:
    """Создаёт конфигурацию для передачи request-id во внутренние запросы."""
    trace_config = aiohttp.TraceConfig()
    trace_config.on_request_start.append(add_request_id_to_outgoing_request)
    return trace_config


async def add_request_id_to_outgoing_request(  # ruff: ignore[unused-async]
    _session: aiohttp.ClientSession,
    _trace_config_ctx: object,
    params: aiohttp.TraceRequestStartParams,
) -> None:
    """Добавляет ID текущего HTTP-запроса во внутренний запрос."""
    request_id = get_request_id()
    if request_id is not None:
        params.headers.setdefault("X-Request-ID", str(request_id))


class RequestIdFilter(logging.Filter):
    def __init__(self, request_id: str):
        super().__init__()
        self.request_id = request_id

    def filter(self, record):
        record.request_id = self.request_id
        return True


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # ruff: ignore[no-self-use]
        request_id = create_request_id(request.headers.get("X-Request-ID"))
        context_token = set_request_id(request_id)

        filter_ = RequestIdFilter(request_id)

        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            handler.addFilter(filter_)

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = str(request_id)
            return response
        finally:
            for handler in root_logger.handlers:
                if filter_ in handler.filters:
                    handler.removeFilter(filter_)
            reset_request_id(context_token)
