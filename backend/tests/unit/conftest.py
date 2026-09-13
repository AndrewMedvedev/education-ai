from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_session():
    """Выполняет действие `mock_session`, чтобы поддержать основной сценарий модуля."""
    return AsyncMock(spec=AsyncSession)
