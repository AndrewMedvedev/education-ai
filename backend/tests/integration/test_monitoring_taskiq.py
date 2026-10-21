"""Запускать только с tests.support.monitoring_smoke в отдельной очереди."""

import asyncio
import importlib
import os
from http import HTTPStatus

import httpx
import pytest
import pytest_asyncio
from prometheus_client.parser import text_string_to_metric_families
from redis.asyncio import Redis

EXPECTED_FAILURE_ATTEMPTS = 2
METRICS_URL = os.getenv("TEST_TASKIQ_METRICS_URL", "http://localhost:9000")

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not os.getenv("MONITORING_CORE_PATH"),
        reason="Isolated monitoring worker is required",
    ),
]


@pytest_asyncio.fixture
async def smoke_module():
    module = importlib.import_module("monitoring_smoke")
    await module.broker.startup()
    try:
        yield module
    finally:
        await module.broker.shutdown()


async def test_success_through_rabbit_and_redis(smoke_module):
    task = await smoke_module.smoke_success.kiq("no-llm-called")
    try:
        result = await task.wait_result(timeout=15)
        assert not result.is_err
        assert result.return_value == "no-llm-called"
        assert await task.is_ready()
    finally:
        async with Redis.from_url(os.environ["TEST_REDIS_URL"]) as redis:
            await redis.delete(f"taskiq:{task.task_id}")


async def test_failure_retries_and_preserves_task_id(smoke_module):
    async with httpx.AsyncClient() as client:
        before = (await client.get(f"{METRICS_URL}/metrics")).text
    task = await smoke_module.smoke_failure.kiq()
    try:
        result = await task.wait_result(timeout=15)
        assert result.is_err
        assert isinstance(result.error, ValueError)
        async with httpx.AsyncClient() as client:
            metrics = (await client.get(f"{METRICS_URL}/metrics")).text

        def error_count(text):
            return next(
                sample.value
                for family in text_string_to_metric_families(text)
                for sample in family.samples
                if sample.name == "found_errors_total"
                and sample.labels["task_name"] == "monitoring_smoke:smoke_failure"
            )

        assert error_count(metrics) - error_count(before) == EXPECTED_FAILURE_ATTEMPTS
    finally:
        async with Redis.from_url(os.environ["TEST_REDIS_URL"]) as redis:
            await redis.delete(f"taskiq:{task.task_id}")


async def test_task_timeout_is_saved_as_failure(smoke_module):
    task = await smoke_module.smoke_timeout.kiq()
    try:
        result = await task.wait_result(timeout=15)
        assert result.is_err
        assert isinstance(result.error, TimeoutError)
    finally:
        async with Redis.from_url(os.environ["TEST_REDIS_URL"]) as redis:
            await redis.delete(f"taskiq:{task.task_id}")


async def test_http_metrics_without_main_application():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        for status in [HTTPStatus.OK, HTTPStatus.BAD_REQUEST, HTTPStatus.INTERNAL_SERVER_ERROR]:
            assert (await client.get(f"/smoke/{status.value}")).status_code == status
        await asyncio.sleep(0)
        metrics = (await client.get("/metrics")).text
    for status_group in ["2xx", "4xx", "5xx"]:
        sample = (
            'http_requests_total{handler="/smoke/{status_code}",'
            f'method="GET",status="{status_group}"}}'
        )
        assert sample in metrics
