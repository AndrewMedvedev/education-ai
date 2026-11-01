"""Opt-in PostgreSQL regression tests using an isolated disposable schema.

Run inside compose backend with PRACTICE_RECOVERY_POSTGRES_TESTS=1.
No application rows are read or changed; only the practices table definition is copied.
"""

import asyncio
import os
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.database.config import postgres_config
from src.courses.agents.external_agents.practicer import PracticerAgent
from src.courses.domain.entities import Practice
from src.courses.infra.database.repos.practice import SqlPracticeRepository
from src.shared.application.transaction import Transaction
from src.shared.utils.time import current_datetime

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        os.getenv("PRACTICE_RECOVERY_POSTGRES_TESTS") != "1",
        reason="Explicit opt-in required to create a disposable PostgreSQL schema",
    ),
]


@pytest_asyncio.fixture
async def sessions():
    engine = create_async_engine(postgres_config.uri)
    schema = f"test_practice_recovery_{uuid4().hex}"
    async with engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        await conn.execute(
            text(
                f'CREATE TABLE "{schema}".practices (LIKE public.practices INCLUDING ALL)',
            )
        )
    factory = async_sessionmaker(
        engine.execution_options(schema_translate_map={None: schema}),
        expire_on_commit=False,
    )
    try:
        yield factory
    finally:
        async with engine.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await engine.dispose()


def practice(user_id, module_id, lesson_id, payload, age=0):
    return Practice(
        user_id=user_id,
        module_id=module_id,
        lesson_id=lesson_id,
        practice=payload,
        created_at=current_datetime() - timedelta(seconds=age),
    )


async def test_latest_filters_user_module_lesson_type_and_supports_checked_shape(sessions):
    ids = uuid4(), uuid4(), uuid4()
    assignment = {"assignment_type": "file_upload", "title": "Report"}
    async with sessions() as session:
        repo = SqlPracticeRepository(session)
        old = await repo.create(practice(*ids, [assignment], age=60))
        await repo.create(practice(*ids, [{"test_type": "multiple_choice"}]))
        await repo.create(practice(uuid4(), ids[1], ids[2], [assignment]))
        await repo.create(practice(ids[0], uuid4(), ids[2], [assignment]))
        await repo.create(practice(ids[0], ids[1], uuid4(), [assignment]))
        await session.commit()
        assert (await repo.read_latest_file_upload(*ids)).id == old.id
        latest = await repo.create(
            practice(
                *ids,
                {
                    "practice": assignment,
                    "score": 0,
                    "ai_feedback": "Retry",
                },
                age=30,
            )
        )
        await session.commit()
        restored = await repo.read_latest_file_upload(*ids)
        assert restored.id == latest.id
        assert PracticerAgent.practice_response(restored)["result"] == {
            "score": 0.0,
            "ai_feedback": "Retry",
        }
        assert await repo.read_latest_file_upload(uuid4(), ids[1], ids[2]) is None


async def test_simultaneous_posts_generate_once_across_sessions(sessions, monkeypatch):
    ids = uuid4(), uuid4(), uuid4()
    entered, finish = asyncio.Event(), asyncio.Event()
    assignment = {
        "assignment_type": "file_upload",
        "title": "Report",
        "description": "Write a report",
        "evaluation_criteria": ["Correctness"],
        "submission_instructions": "Upload Markdown",
    }
    invocations = 0

    async def invoke(**kwargs):
        nonlocal invocations
        invocations += 1
        entered.set()
        await finish.wait()
        return SimpleNamespace(output=assignment)

    monkeypatch.setattr(
        "src.courses.agents.external_agents.practicer.LLMTextService",
        lambda **_: SimpleNamespace(invoke=invoke),
    )
    monkeypatch.setattr(
        "src.courses.agents.external_agents.practicer.async_load_assignment_example",
        AsyncMock(return_value="Example"),
    )

    async def post():
        async with sessions() as session:
            lessons = AsyncMock()
            lessons.read.return_value = SimpleNamespace(module_id=ids[1], content_blocks=[])
            agent = PracticerAgent(
                practice_repo=SqlPracticeRepository(session),
                lesson_repo=lessons,
                transaction=Transaction(session, AsyncMock()),
                client=object(),
            )
            return await agent.call_agent_creator(*ids)

    first = asyncio.create_task(post())
    await asyncio.wait_for(entered.wait(), timeout=5)
    second = asyncio.create_task(post())
    try:
        await asyncio.sleep(0.1)
        # A refreshed GET sees no committed practice yet, without waiting for the LLM.
        async with sessions() as session:
            assert await SqlPracticeRepository(session).read_latest_file_upload(*ids) is None
        assert not second.done()
    finally:
        finish.set()
    responses = await asyncio.wait_for(asyncio.gather(first, second), timeout=5)
    assert invocations == 1
    assert responses[0] == responses[1]
    async with sessions() as session:
        restored = await SqlPracticeRepository(session).read_latest_file_upload(*ids)
        assert restored.id == responses[0]["practice_id"]
