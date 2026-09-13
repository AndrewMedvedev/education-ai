from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from src.shared.infra.middlewares import LoggingMiddleware

from .lifespan import lifespan
from .monitoring import health, setup_prometheus
from .settings import app_config

app = FastAPI(
    title="DIO COURSES API",
    description="REST API сервис ITSM системы",
    contact={
        "name": "ДИО-Консалт (Официальный сайт)",
        "url": "https://diocon.ru/",
    },
    version=app_config.version,
    lifespan=lifespan,
)
Instrumentator(
    should_group_status_codes=True,
    should_group_untemplated=True,
    excluded_handlers=["/health", "/metrics"],
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

app.add_middleware(LoggingMiddleware)


app.add_middleware(
    CORSMiddleware,
    allow_origins=app_config.cors_origins,
    allow_credentials=app_config.cors_allow_credentials,
    allow_methods=app_config.cors_allow_methods,
    allow_headers=app_config.cors_allow_headers,
)

setup_prometheus(app)

app.include_router(health.router)
