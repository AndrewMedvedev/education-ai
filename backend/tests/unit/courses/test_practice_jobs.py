import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.courses.infra import practice_jobs


class MemoryRedis:
    def __init__(self):
        self.values = {}

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, *, ex, nx):
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True

    async def eval(self, script, count, key, old, new, ttl):
        if self.values.get(key) != old:
            return 0
        self.values[key] = new
        return 1


@pytest.fixture
def redis(monkeypatch):
    value = MemoryRedis()
    monkeypatch.setattr(practice_jobs, "redis_client", value)
    return value


@pytest.mark.asyncio
async def test_simultaneous_starts_share_job_and_user_scope(redis):
    ids = uuid4(), uuid4(), uuid4()
    results = await asyncio.gather(*(practice_jobs.begin(*ids) for _ in range(5)))
    assert len({job["job_id"] for job, _ in results}) == 1
    assert sum(created for _, created in results) == 1
    assert await practice_jobs.read(uuid4(), *ids[1:]) is None


@pytest.mark.asyncio
async def test_failure_can_retry_and_old_worker_cannot_overwrite(redis):
    ids = uuid4(), uuid4(), uuid4()
    first, _ = await practice_jobs.begin(*ids)
    assert await practice_jobs.transition(*ids, first["job_id"], ("queued",), "running", 30)
    assert await practice_jobs.transition(*ids, first["job_id"], ("running",), "failed", 30)
    second, created = await practice_jobs.begin(*ids)
    assert created and second["job_id"] != first["job_id"]
    assert not await practice_jobs.transition(*ids, first["job_id"], ("running",), "succeeded", 30)
    assert (await practice_jobs.read(*ids))["job_id"] == second["job_id"]


@pytest.mark.asyncio
async def test_expired_queue_and_running_job_ignore_late_task(redis):
    ids = uuid4(), uuid4(), uuid4()
    job, _ = await practice_jobs.begin(*ids)
    del redis.values[practice_jobs.key(*ids)]
    assert not await practice_jobs.transition(*ids, job["job_id"], ("queued",), "running", 30)
    assert await practice_jobs.read(*ids) is None


@pytest.mark.asyncio
async def test_status_checks_access_and_returns_saved_assignment(monkeypatch):
    from src.courses.api.v1.agents import get_practice_generation

    user_id, module_id, lesson_id = uuid4(), uuid4(), uuid4()
    check = AsyncMock()
    agent = SimpleNamespace(get_latest_practice=AsyncMock(return_value={
        "practice_id": uuid4(), "practice": {"title": "task"}, "result": None,
    }))
    monkeypatch.setattr(practice_jobs, "read", AsyncMock(return_value={"status": "running", "job_id": "id"}))
    result = await get_practice_generation(module_id, lesson_id, agent, SimpleNamespace(id=user_id), check)
    assert result["status"] == "succeeded"
    assert result["practice"]["title"] == "task"
    check.assert_awaited_once()
    agent.get_latest_practice.assert_awaited_once_with(user_id, module_id, lesson_id)


@pytest.mark.asyncio
async def test_status_denied_does_not_inspect_job(monkeypatch):
    from src.courses.api.v1.agents import get_practice_generation

    read = AsyncMock()
    monkeypatch.setattr(practice_jobs, "read", read)
    check = AsyncMock(side_effect=PermissionError())
    with pytest.raises(PermissionError):
        await get_practice_generation(uuid4(), uuid4(), object(), SimpleNamespace(id=uuid4()), check)
    read.assert_not_awaited()


@pytest.mark.asyncio
async def test_start_queue_failure_is_visible_and_retryable(redis, monkeypatch):
    from fastapi import HTTPException
    from src.courses.api.v1.agents import start_practice_generation
    from src.courses.infra import tasks

    ids = uuid4(), uuid4(), uuid4()
    agent = SimpleNamespace(get_latest_practice=AsyncMock(return_value={"practice_id": None}))
    enqueue = AsyncMock(side_effect=RuntimeError("broker unavailable"))
    monkeypatch.setattr(tasks, "generate_practice", SimpleNamespace(kiq=enqueue))
    with pytest.raises(HTTPException) as exc:
        await start_practice_generation(ids[1], ids[2], agent, SimpleNamespace(id=ids[0]), AsyncMock())
    assert exc.value.status_code == 503
    assert (await practice_jobs.read(*ids))["status"] == "failed"
    enqueue.side_effect = None
    result = await start_practice_generation(ids[1], ids[2], agent, SimpleNamespace(id=ids[0]), AsyncMock())
    assert result["status"] == "queued"
    assert enqueue.await_count == 2


@pytest.mark.asyncio
async def test_worker_completes_and_records_failure_or_cancellation(redis):
    from src.courses.infra.tasks import generate_practice

    ids = uuid4(), uuid4(), uuid4()
    agent = SimpleNamespace(create_in_background=AsyncMock())
    job, _ = await practice_jobs.begin(*ids)
    await generate_practice.original_func(*(str(value) for value in ids), job["job_id"], agent)
    assert (await practice_jobs.read(*ids))["status"] == "succeeded"
    agent.create_in_background.side_effect = RuntimeError("LLM unavailable")
    job, _ = await practice_jobs.begin(*ids)
    with pytest.raises(RuntimeError):
        await generate_practice.original_func(*(str(value) for value in ids), job["job_id"], agent)
    assert (await practice_jobs.read(*ids))["status"] == "failed"
    agent.create_in_background.side_effect = asyncio.CancelledError()
    job, _ = await practice_jobs.begin(*ids)
    with pytest.raises(asyncio.CancelledError):
        await generate_practice.original_func(*(str(value) for value in ids), job["job_id"], agent)
    assert (await practice_jobs.read(*ids))["status"] == "failed"


@pytest.mark.asyncio
async def test_start_worker_and_poll_returns_persisted_practice(redis, monkeypatch):
    from src.courses.api.v1.agents import get_practice_generation, start_practice_generation
    from src.courses.infra import tasks

    ids = uuid4(), uuid4(), uuid4()
    identity, check = SimpleNamespace(id=ids[0]), AsyncMock()
    stored = {"practice_id": None, "practice": None, "result": None}
    practice_id = uuid4()

    async def latest(*args):
        return dict(stored)

    async def generate(*args):
        stored.update(practice_id=practice_id, practice={"title": "Generated"})

    agent = SimpleNamespace(get_latest_practice=AsyncMock(side_effect=latest),
                            create_in_background=AsyncMock(side_effect=generate))
    original_task = tasks.generate_practice
    queued = []
    enqueue = AsyncMock(side_effect=lambda *args: queued.append(args))
    monkeypatch.setattr(tasks, "generate_practice", SimpleNamespace(kiq=enqueue))
    first = await start_practice_generation(ids[1], ids[2], agent, identity, check)
    again = await start_practice_generation(ids[1], ids[2], agent, identity, check)
    assert first["job_id"] == again["job_id"]
    assert enqueue.await_count == 1
    assert (await get_practice_generation(ids[1], ids[2], agent, identity, check))["status"] == "queued"
    await original_task.original_func(*queued[0], agent)
    result = await get_practice_generation(ids[1], ids[2], agent, identity, check)
    assert result["status"] == "succeeded"
    assert result["practice_id"] == practice_id
    assert result["practice"]["title"] == "Generated"
