import importlib.util
import sys
from functools import partial
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from prometheus_client import CollectorRegistry
from prometheus_fastapi_instrumentator import middleware

CORE = Path(__file__).resolve().parents[3] / "src" / "core"


@pytest.fixture
def load_core(monkeypatch):
    """Загружает проверяемый модуль без запуска приложения и внешних клиентов."""
    package = ModuleType("monitoring_test_core")
    package.__path__ = [str(CORE)]
    monkeypatch.setitem(sys.modules, package.__name__, package)
    rabbit = ModuleType("monitoring_test_core.rabbit")
    rabbit.rabbit_config = SimpleNamespace(uri="amqp://guest:guest@localhost/")
    monkeypatch.setitem(sys.modules, rabbit.__name__, rabbit)
    redis = ModuleType("monitoring_test_core.redis")
    redis.__path__ = []
    monkeypatch.setitem(sys.modules, redis.__name__, redis)
    redis_config = ModuleType("monitoring_test_core.redis.config")
    redis_config.redis_config = SimpleNamespace(url="redis://localhost:6379/15")
    redis.redis_config = redis_config.redis_config
    monkeypatch.setitem(sys.modules, redis_config.__name__, redis_config)

    def load(relative_path):
        name = "monitoring_test_core." + relative_path.replace("/", ".")
        spec = importlib.util.spec_from_file_location(name, CORE / f"{relative_path}.py")
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, module)
        if relative_path == "tkq":
            from taskiq.abc.middleware import TaskiqMiddleware

            with monkeypatch.context() as isolated:
                isolated.setattr("taskiq.PrometheusMiddleware", Mock(return_value=Mock(spec=TaskiqMiddleware)))
                spec.loader.exec_module(module)
        else:
            spec.loader.exec_module(module)
        return module

    return load


@pytest.fixture
def metrics_app(load_core, monkeypatch):
    monitoring = load_core("monitoring/prometheus")
    registry = CollectorRegistry()
    monkeypatch.setattr(
        monitoring,
        "Instrumentator",
        partial(monitoring.Instrumentator, registry=registry),
    )
    # Instrumentator's in-progress Gauge uses the default registry separately.
    monkeypatch.setattr(middleware, "Gauge", partial(middleware.Gauge, registry=registry))
    app = FastAPI()
    monitoring.setup_prometheus(app)
    return app, registry
