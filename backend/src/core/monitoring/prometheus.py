from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator


def setup_prometheus(app: FastAPI) -> None:
    Instrumentator(
        should_group_status_codes=True,
        should_group_untemplated=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/health", "/ready", "/metrics"],
    ).instrument(app).expose(
        app,
        endpoint="/metrics",
        include_in_schema=False,
        should_gzip=True,
    )
