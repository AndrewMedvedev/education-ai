# pyright: reportCallIssue=false, reportArgumentType=false

from __future__ import annotations

from typing import Annotated, Any, get_args, get_origin, get_type_hints

import copy
import inspect
from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field, create_model
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from .dataclasses import ParamGroup, StructuredTool
from .strict_schema import to_strict_json_schema


class InjectedToolArg:
    """Маркер для injected-параметров."""


def _is_injected(annotation: Any) -> bool:
    """Выполняет внутренний шаг `_is_injected`, чтобы скрыть детали реализации от публичного API."""
    return get_origin(annotation) is Annotated and any(
        isinstance(x, InjectedToolArg) for x in get_args(annotation)[1:]
    )


def _unwrap_annotated(annotation: Any) -> Any:
    """Выполняет внутренний шаг `_unwrap_annotated`, чтобы скрыть детали реализации от публичного API."""
    return get_args(annotation)[0] if get_origin(annotation) is Annotated else annotation


def _build_args_model_and_groups(
    func: Callable,
    model_name: str,
) -> tuple[type[BaseModel], dict[str, ParamGroup]]:
    """Выполняет внутренний шаг `_build_args_model_and_groups`, чтобы скрыть детали реализации от публичного API."""
    sig = inspect.signature(func)
    hints = get_type_hints(func, include_extras=True)

    fields: dict[str, tuple[Any, Any]] = {}
    param_groups: dict[str, ParamGroup] = {}
    used_names: set[str] = set()

    for name, param in sig.parameters.items():
        if name in {"self", "cls"} or param.kind in {
            param.VAR_POSITIONAL,
            param.VAR_KEYWORD,
        }:
            continue

        annotation = hints.get(name, Any)

        if name == "runtime" or _is_injected(annotation):
            continue

        real_type = _unwrap_annotated(annotation)

        if inspect.isclass(real_type) and issubclass(real_type, BaseModel):
            field_names: list[str] = []

            for field_name, field in real_type.model_fields.items():
                if field_name in used_names:
                    raise ValueError(
                        f"Конфликт имени '{field_name}' в инструменте '{model_name}'."
                    )

                used_names.add(field_name)
                field_names.append(field_name)

                fields[field_name] = (
                    field.annotation,
                    copy.deepcopy(field),
                )

            param_groups[name] = ParamGroup(
                kind="model",
                model_cls=real_type,
                field_names=field_names,
            )
            continue

        if name in used_names:
            raise ValueError(f"Дублирующееся имя параметра '{name}' в инструменте '{model_name}'.")

        used_names.add(name)

        field_info = (
            param.default
            if isinstance(param.default, FieldInfo)
            else Field(
                default=(param.default if param.default is not param.empty else PydanticUndefined)
            )
        )

        fields[name] = (real_type, field_info)

        param_groups[name] = ParamGroup(
            kind="flat",
            model_cls=None,
            field_names=[name],
        )

    args_model = create_model(
        model_name,
        __config__=ConfigDict(
            extra="forbid",
            arbitrary_types_allowed=True,
        ),
        **fields,
    )

    return args_model, param_groups


def tool(
    name: str | None = None,
    description: str | None = None,
) -> Callable[[Callable], StructuredTool]:
    """Выполняет действие `tool`, чтобы поддержать основной сценарий модуля."""

    def decorator(func: Callable) -> StructuredTool:
        """Выполняет действие `decorator`, чтобы поддержать основной сценарий модуля."""
        tool_name = name or (func.__name__)

        args_model, param_groups = _build_args_model_and_groups(
            func,
            tool_name,
        )

        tool_schema = {
            "name": tool_name,
            "description": (description or inspect.getdoc(func) or "No description provided."),
            "parameters": to_strict_json_schema(args_model),
        }

        return StructuredTool(
            func=func,
            name=tool_name,
            runtime="runtime" in inspect.signature(func).parameters,
            args_schema=tool_schema,
            args_model=args_model,
            param_groups=param_groups,
        )

    return decorator
