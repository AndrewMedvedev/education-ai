from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.shared.domain.exceptions import DomainError


def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "grant": "VALIDATION_ERROR",
                "message": str(exc),
                "status": status.HTTP_400_BAD_REQUEST,
                "details": {},
            },
        },
    )


def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        },
    )


def setup_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ValueError, value_error_handler)  # pyright: ignore[reportArgumentType]
    app.add_exception_handler(DomainError, domain_error_handler)  # pyright: ignore[reportArgumentType]


__all__ = ["setup_exception_handlers"]
