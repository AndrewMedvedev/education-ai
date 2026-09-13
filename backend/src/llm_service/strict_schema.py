"""
strict_schema.py
=================

Автономный модуль (без зависимостей от пакета `openai`) для превращения
обычной JSON-схемы pydantic-модели в "строгую" (strict) JSON-схему —
такую, какую требуют, например, OpenAI Structured Outputs / function calling
в строгом режиме.

Что значит "строгая" схема:
  1. У каждого объекта (`type: object`) явно указано `additionalProperties: false`
     — модели нельзя добавлять поля, которых нет в схеме.
  2. Все свойства объекта попадают в `required` — pydantic по умолчанию
     не считает Optional-поля обязательными, а строгий режим требует,
     чтобы ВСЕ ключи были перечислены как required (опциональность
     выражается через `anyOf: [..., {"type": "null"}]`, а не через
     отсутствие поля).
  3. `$ref`, стоящий рядом с другими ключами (например, с `description`),
     разворачивается (inline), потому что по JSON Schema спецификации
     соседние с `$ref` ключи должны игнорироваться, а строгий режим
     этого не допускает — нужно either чистый `$ref`, either полностью
     развёрнутая схема.
  4. `default: null` убирается, так как в строгом режиме модель всё равно
     не может использовать "default"-подсказку — за неё отвечает `anyOf`
     с `null`.

Зависимости: только pydantic >= 2.0. Ничего из пакета `openai` не требуется.
"""

from __future__ import annotations

from typing import Any, TypeGuard

import inspect

import pydantic

# Локальный "часовой" объект вместо NOT_GIVEN из openai._types.
# Нужен, чтобы отличить "поля 'default' нет вообще" от "default явно = None".
_SENTINEL = object()


# ---------------------------------------------------------------------------
# Публичная точка входа
# ---------------------------------------------------------------------------
def to_strict_json_schema(
    model: type[pydantic.BaseModel] | pydantic.TypeAdapter[Any],
) -> dict[str, Any]:
    """
    Строит строгую JSON-схему для pydantic-модели или pydantic.TypeAdapter.

    Параметры
    ---------
    model:
        - класс, унаследованный от pydantic.BaseModel, ИЛИ
        - экземпляр pydantic.TypeAdapter (например, TypeAdapter(list[int]))

    Возвращает
    ----------
    dict — итоговая JSON-схема, пригодная для strict-режима.

    Исключения
    ----------
    TypeError — если передан не BaseModel-класс и не TypeAdapter.
    """
    if inspect.isclass(model) and is_basemodel_type(model):
        schema = model.model_json_schema()
    elif isinstance(model, pydantic.TypeAdapter):
        schema = model.json_schema()
    else:
        raise TypeError(
            "Ожидался класс pydantic.BaseModel или экземпляр pydantic.TypeAdapter, "
            f"получено: {model!r}"
        )

    return _ensure_strict_json_schema(schema, path=(), root=schema)


# ---------------------------------------------------------------------------
# Основная рекурсивная функция
# ---------------------------------------------------------------------------
def _ensure_strict_json_schema(  # ruff: ignore[complex-structure]
    json_schema: object,
    *,
    path: tuple[str, ...],
    root: dict[str, object],
) -> dict[str, Any]:
    """
    Рекурсивно модифицирует (in-place) переданную JSON-схему так, чтобы
    она соответствовала strict-стандарту.

    `path` используется только для информативных сообщений об ошибках —
    показывает, в какой части схемы возникла проблема.
    `root` — ссылка на схему целиком, нужна для разрешения `$ref` вида "#/...".
    """
    if not is_dict(json_schema):
        raise TypeError(f"Ожидался словарь в {json_schema!r}; путь={path}")

    # --- 1. Рекурсивно обходим определения переиспользуемых типов ---
    # В pydantic v2 переиспользуемые под-схемы лежат в "$defs".
    # Ключ "definitions" — устаревший вариант из старых версий JSON Schema /
    # pydantic v1, но мы его тоже поддерживаем на случай, если кто-то
    # передаст схему, собранную вручную или сторонним инструментом.
    defs = json_schema.get("$defs")
    if is_dict(defs):
        for def_name, def_schema in defs.items():
            _ensure_strict_json_schema(def_schema, path=(*path, "$defs", def_name), root=root)

    definitions = json_schema.get("definitions")
    if is_dict(definitions):
        for definition_name, definition_schema in definitions.items():
            _ensure_strict_json_schema(
                definition_schema, path=(*path, "definitions", definition_name), root=root
            )

    # --- 2. object: запрещаем лишние поля ---
    typ = json_schema.get("type")
    if typ == "object" and "additionalProperties" not in json_schema:
        json_schema["additionalProperties"] = False

    # --- 3. object: все properties -> required, рекурсия внутрь каждого ---
    properties = json_schema.get("properties")
    if is_dict(properties):
        json_schema["required"] = list(properties.keys())
        json_schema["properties"] = {
            key: _ensure_strict_json_schema(
                prop_schema, path=(*path, "properties", key), root=root
            )
            for key, prop_schema in properties.items()
        }

    # --- 4. array: рекурсия в items (список произвольной длины) ---
    items = json_schema.get("items")
    if is_dict(items):
        json_schema["items"] = _ensure_strict_json_schema(items, path=(*path, "items"), root=root)

    # --- 4.1 УЛУЧШЕНИЕ: array-tuple: рекурсия в prefixItems ---
    # Оригинальный код из openai не обрабатывал "prefixItems" — это ключ
    # JSON Schema (draft 2020-12), который pydantic генерирует для
    # tuple[int, str] и подобных фиксированных по длине кортежей.
    # Без этой обработки вложенные объекты внутри tuple[...] не получали
    # бы additionalProperties/required и strict-режим мог бы их отклонить.
    prefix_items = json_schema.get("prefixItems")
    if is_list(prefix_items):
        json_schema["prefixItems"] = [
            _ensure_strict_json_schema(item, path=(*path, "prefixItems", str(i)), root=root)
            for i, item in enumerate(prefix_items)
        ]

    # --- 5. anyOf (Union / Optional) ---
    any_of = json_schema.get("anyOf")
    if is_list(any_of):
        json_schema["anyOf"] = [
            _ensure_strict_json_schema(variant, path=(*path, "anyOf", str(i)), root=root)
            for i, variant in enumerate(any_of)
        ]

    # --- 5.1 УЛУЧШЕНИЕ: oneOf, обрабатывается так же, как anyOf ---
    # pydantic обычно генерирует anyOf, но некоторые кастомные схемы
    # (например, через json_schema_extra) могут содержать oneOf.
    one_of = json_schema.get("oneOf")
    if is_list(one_of):
        json_schema["oneOf"] = [
            _ensure_strict_json_schema(variant, path=(*path, "oneOf", str(i)), root=root)
            for i, variant in enumerate(one_of)
        ]

    # --- 6. allOf (пересечение типов) ---
    all_of = json_schema.get("allOf")
    if is_list(all_of):
        if len(all_of) == 1:
            # allOf с единственным элементом — это просто "обёртка".
            # Разворачиваем её, чтобы не плодить лишнюю вложенность.
            json_schema.update(
                _ensure_strict_json_schema(all_of[0], path=(*path, "allOf", "0"), root=root)
            )
            json_schema.pop("allOf")
        else:
            json_schema["allOf"] = [
                _ensure_strict_json_schema(entry, path=(*path, "allOf", str(i)), root=root)
                for i, entry in enumerate(all_of)
            ]

    # --- 7. default: null убираем ---
    # Смысловой разницы нет: поле всё равно nullable через anyOf с "null",
    # а модель в strict-режиме не умеет опираться на "default".
    if json_schema.get("default", _SENTINEL) is None:
        json_schema.pop("default")

    # --- 8. Разворачиваем $ref, если рядом есть другие ключи ---
    # Пример проблемы: {"$ref": "#/$defs/Foo", "description": "моё описание"}
    # По спецификации JSON Schema "description" здесь просто игнорируется,
    # а strict-режим такого не прощает — поэтому мы "инлайним" содержимое
    # $ref прямо в текущий словарь.
    ref = json_schema.get("$ref")
    if ref and has_more_than_n_keys(json_schema, 1):
        assert isinstance(ref, str), f"$ref должен быть строкой, получено: {ref!r}"

        resolved = resolve_ref(root=root, ref=ref)
        if not is_dict(resolved):
            raise ValueError(
                f"$ref: {ref} должен разрешаться в словарь, но получено: {resolved!r}"
            )

        # Свойства, заданные явно рядом с $ref, имеют приоритет над теми,
        # что пришли из самого $ref.
        json_schema.update({**resolved, **json_schema})
        json_schema.pop("$ref")

        # Развёрнутая схема могла не пройти обработку (например,
        # additionalProperties ещё не проставлен) — обрабатываем повторно.
        return _ensure_strict_json_schema(json_schema, path=path, root=root)

    return json_schema


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------
def resolve_ref(*, root: dict[str, object], ref: str) -> object:
    """
    Разрешает локальную ссылку вида "#/$defs/SomeModel" в реальный
    под-словарь схемы `root`.
    """
    if not ref.startswith("#/"):
        raise ValueError(f"Неожиданный формат $ref: {ref!r}; ожидалось, что начинается с '#/'")

    path = ref[2:].split("/")
    resolved: object = root
    for key in path:
        if not is_dict(resolved):
            raise ValueError(
                f"Не удалось разрешить {ref!r}: промежуточный узел '{key}' не словарь"
            )
        resolved = resolved[key]

    return resolved


def is_basemodel_type(typ: type) -> TypeGuard[type[pydantic.BaseModel]]:
    """True, если `typ` — это именно класс (не экземпляр), унаследованный от BaseModel."""
    if not inspect.isclass(typ):
        return False
    return issubclass(typ, pydantic.BaseModel)


def is_dict(obj: object) -> TypeGuard[dict[str, object]]:
    """Простая проверка на dict (ключи считаем строковыми, отдельно не проверяем — ради скорости)."""
    return isinstance(obj, dict)


def is_list(obj: object) -> TypeGuard[list[Any]]:
    """Простая проверка на list."""
    return isinstance(obj, list)


def has_more_than_n_keys(obj: dict[str, object], n: int) -> bool:
    """
    Проверяет, что в словаре больше n ключей, не считая все ключи целиком
    (останавливается, как только порог превышен — важно для больших схем).
    """
    i = 0
    for _ in obj:
        i += 1  # ruff: ignore[enumerate-for-loop]
        if i > n:
            return True
    return False
