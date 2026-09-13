import contextlib
import importlib
from collections.abc import Sequence

from .base import Base
from .config import postgres_config
from .connection import get_db, session_factory


def import_all_models(modules: Sequence[str]) -> None:  # ruff: ignore[non-empty-init-module]
    """Динамически сканирует и импортирует файлы ORM моделей для указанных модулей.
    Если модели находятся в отличном от `src.{module}.infra.database.models`, то
    рекомендуется импортировать их в ручную для миграций.
    """

    for module in modules:
        with contextlib.suppress(ModuleNotFoundError):
            importlib.import_module(f"src.{module}.infra.database.models")


__all__ = ["Base", "get_db", "import_all_models", "postgres_config", "session_factory"]
