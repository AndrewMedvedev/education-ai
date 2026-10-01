import importlib
import pkgutil
from collections.abc import Iterable

from fastapi import APIRouter


def include_routers(
    router: APIRouter,
    package: str,
    package_path: Iterable[str],
    *,
    exclude: set[str] | None = None,
) -> None:
    """Подключает к `router` все FastAPI роутеры из модулей пакета.

    Обычно вызывается из `src.<module>.api.v1.__init__` так:

        router = APIRouter()
        include_routers(router, __name__, __path__)

    Helper импортирует все `.py` файлы внутри текущей папки `v1` и, если в модуле
    есть переменная `router` типа `APIRouter`, добавляет её через `include_router`.
    """

    excluded_modules = exclude or set()

    for module_info in sorted(pkgutil.iter_modules(package_path), key=lambda item: item.name):
        module_name = module_info.name

        if module_info.ispkg or module_name.startswith("_") or module_name in excluded_modules:
            continue

        module = importlib.import_module(f"{package}.{module_name}")
        module_router = getattr(module, "router", None)

        if isinstance(module_router, APIRouter):
            router.include_router(module_router)


__all__ = ["include_routers"]
