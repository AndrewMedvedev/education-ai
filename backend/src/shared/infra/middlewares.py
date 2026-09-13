import logging
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIdFilter(logging.Filter):
    def __init__(self, request_id: str):
        super().__init__()
        self.request_id = request_id

    def filter(self, record):
        record.request_id = self.request_id
        return True


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # ruff: ignore[no-self-use]
        request_id = f"{uuid4()}"

        filter_ = RequestIdFilter(request_id)

        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            handler.addFilter(filter_)

        try:
            return await call_next(request)
        finally:
            for handler in root_logger.handlers:
                if filter_ in handler.filters:
                    handler.removeFilter(filter_)
