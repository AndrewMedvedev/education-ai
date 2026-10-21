"""Изолированные HTTP/Taskiq заглушки: без импорта приложения и LLM-клиентов."""

import asyncio
import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from starlette.responses import Response

CORE = Path(os.environ["MONITORING_CORE_PATH"])
package = ModuleType("smoke_core")
package.__path__ = [str(CORE)]
sys.modules[package.__name__] = package
rabbit = ModuleType("smoke_core.rabbit")
rabbit.rabbit_config = SimpleNamespace(uri=os.environ["TEST_RABBIT_URL"])
sys.modules[rabbit.__name__] = rabbit
redis = ModuleType("smoke_core.redis")
redis.__path__ = []
sys.modules[redis.__name__] = redis
redis_config = ModuleType("smoke_core.redis.config")
redis_config.redis_config = SimpleNamespace(url=os.environ["TEST_REDIS_URL"])
redis.redis_config = redis_config.redis_config
sys.modules[redis_config.__name__] = redis_config


def load(relative_path):
    name = "smoke_core." + relative_path.replace("/", ".")
    spec = importlib.util.spec_from_file_location(name, CORE / f"{relative_path}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


with patch("taskiq_fastapi.init"):
    broker = load("tkq").taskiq_broker
app = FastAPI()
load("monitoring/prometheus").setup_prometheus(app)


@app.get("/smoke/{status_code}")
def smoke(status_code: int):
    return Response(status_code=status_code)


@broker.task
async def smoke_success(value: str) -> str:
    return value


@broker.task(retry_on_error=True, max_retries=2, delay=0.2)
async def smoke_failure() -> None:
    raise ValueError("Monitoring smoke test")


@broker.task(timeout=0.1)
async def smoke_timeout() -> None:
    await asyncio.sleep(1)
