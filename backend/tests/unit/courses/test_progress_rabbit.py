from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.courses.domain.events import LessonProgressUpdated, LessonProgressUpdate
from src.courses.api.v1.progress import on_lesson_progress_updated


@pytest.mark.asyncio
async def test_on_lesson_progress_updated_updates_repo_and_commits():
    """Обработчик Rabbit обновляет прогресс урока и сохраняет транзакцию."""
    event = LessonProgressUpdated(
        user_id=uuid4(),
        lesson_id=uuid4(),
        progress=LessonProgressUpdate(practice_completed_at=datetime.now(timezone.utc)),
    )
    repo = AsyncMock()
    session = AsyncMock()

    await on_lesson_progress_updated(event, repo, session)

    repo.update_from_event.assert_awaited_once_with(event)
    session.commit.assert_awaited_once_with()
