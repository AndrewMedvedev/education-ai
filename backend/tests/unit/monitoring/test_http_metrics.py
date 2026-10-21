import ast
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from starlette.responses import Response

from .conftest import CORE


def test_api_connects_instrumentation_once():
    source = ast.parse((CORE / "fastapi.py").read_text(encoding="utf-8"))
    calls = [node for node in ast.walk(source) if isinstance(node, ast.Call)]
    names = [node.func.id for node in calls if isinstance(node.func, ast.Name)]
    assert names.count("Instrumentator") == 1
    assert "setup_prometheus" not in names


def test_single_metrics_route_and_middleware(metrics_app):
    app, _ = metrics_app
    assert sum(route.path == "/metrics" for route in app.routes) == 1
    assert (
        sum(m.cls.__name__ == "PrometheusInstrumentatorMiddleware" for m in app.user_middleware)
        == 1
    )


@pytest.mark.parametrize("status", [200, 400, 500])
def test_requests_status_duration_and_no_double_count(metrics_app, status):
    app, registry = metrics_app

    @app.get("/example")
    def example():
        return Response(status_code=status)

    with TestClient(app) as client:
        assert client.get("/example").status_code == status
        metrics = client.get("/metrics")
    assert metrics.status_code == HTTPStatus.OK
    labels = {"handler": "/example", "method": "GET", "status": f"{status // 100}xx"}
    assert registry.get_sample_value("http_requests_total", labels) == 1
    assert (
        registry.get_sample_value(
            "http_request_duration_seconds_count",
            {"handler": "/example", "method": "GET"},
        )
        == 1
    )


def test_health_ready_and_metrics_are_excluded(metrics_app):
    app, registry = metrics_app

    @app.get("/health")
    @app.get("/ready")
    def health():
        return {"status": "ok"}

    with TestClient(app) as client:
        for path in ["/health", "/ready", "/metrics"]:
            assert client.get(path).status_code == HTTPStatus.OK
    samples = [
        s
        for family in registry.collect()
        for s in family.samples
        if s.name == "http_requests_total"
    ]
    assert samples == []


def test_unhandled_errors_are_counted(metrics_app):
    app, registry = metrics_app

    @app.get("/failure")
    def failure():
        raise RuntimeError("Test failure")

    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/failure").status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert (
        registry.get_sample_value(
            "http_requests_total",
            {"handler": "/failure", "method": "GET", "status": "5xx"},
        )
        == 1
    )
