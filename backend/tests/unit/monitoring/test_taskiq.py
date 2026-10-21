from unittest.mock import AsyncMock

import pytest
from taskiq import TaskiqMessage, TaskiqResult
from taskiq.exceptions import NoResultError
from taskiq.middlewares import SmartRetryMiddleware
from taskiq_aio_pika import AioPikaBroker
from taskiq_redis import RedisAsyncResultBackend

RESULT_TTL = 5 * 60 * 60
RETRIES = 5
MIN_DELAY = 10
MAX_DELAY = 100


def test_broker_queues_results_and_metrics(load_core):
    module = load_core("tkq")
    assert isinstance(module.taskiq_broker, AioPikaBroker)
    assert module.taskiq_broker._task_queues[0].name == "myapp_tasks"
    assert module.taskiq_broker._delay_queue.name == "myapp_tasks.delay"
    assert isinstance(module.taskiq_broker.result_backend, RedisAsyncResultBackend)
    assert module.taskiq_broker.result_backend.result_ex_time == RESULT_TTL
    assert len(module.taskiq_broker.middlewares) == 2
    assert module.taskiq_broker.middlewares[-1] is module.PrometheusMiddleware.return_value
    module.PrometheusMiddleware.assert_called_once_with(server_port=9000)


@pytest.mark.asyncio
@pytest.mark.parametrize("completed_retries", range(RETRIES + 1))
async def test_retry_limit_delay_and_task_id(load_core, completed_retries):
    module = load_core("tkq")
    retry = module.taskiq_broker.middlewares[0]
    assert isinstance(retry, SmartRetryMiddleware)
    module.taskiq_broker.kick = AsyncMock()
    message = TaskiqMessage(
        task_id="unchanged-id",
        task_name="test",
        args=[],
        kwargs={"value": 1},
        labels={"retry_on_error": True, "_retries": completed_retries},
    )
    error = RuntimeError("test")
    result = TaskiqResult(is_err=True, error=error, return_value=None, execution_time=0.01)
    await retry.on_error(message, result, error)
    if completed_retries == RETRIES:
        module.taskiq_broker.kick.assert_not_awaited()
        assert result.error is error
    else:
        module.taskiq_broker.kick.assert_awaited_once()
        sent = module.taskiq_broker.kick.call_args.args[0]
        assert sent.task_id == "unchanged-id"
        assert int(sent.labels["_retries"]) == completed_retries + 1
        assert MIN_DELAY <= float(sent.labels["delay"]) <= MAX_DELAY
        assert isinstance(result.error, NoResultError)


@pytest.mark.asyncio
async def test_retries_disabled_for_other_tasks(load_core):
    module = load_core("tkq")
    module.taskiq_broker.kick = AsyncMock()
    message = TaskiqMessage(task_id="id", task_name="test", args=[], kwargs={}, labels={})
    error = RuntimeError("test")
    result = TaskiqResult(is_err=True, error=error, return_value=None, execution_time=0.01)
    await module.taskiq_broker.middlewares[0].on_error(message, result, error)
    module.taskiq_broker.kick.assert_not_awaited()
