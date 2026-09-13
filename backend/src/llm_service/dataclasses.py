from __future__ import annotations

from typing import Any, Literal

import json
from collections.abc import Callable
from dataclasses import dataclass

from openai.types.responses import FunctionToolParam
from pydantic import BaseModel


@dataclass
class ParamGroup:
    """
    Описывает связь между одним параметром исходной функции
    и "плоскими" полями итоговой схемы инструмента.

    kind="flat"  -> параметр обычного типа (str, int, Literal, ...).
                    field_names содержит одно имя, совпадающее с именем параметра.
    kind="model" -> параметр был аннотирован как Pydantic BaseModel.
                    Его поля "расплющены" в top-level схему.
                    field_names — имена этих полей в плоской схеме,
                    model_cls — класс модели, который нужно пересобрать
                    из плоских данных перед вызовом исходной функции.
    """

    kind: Literal["flat", "model"]
    model_cls: type[BaseModel] | None
    field_names: list[str]


@dataclass
class StructuredTool:
    """Хранит структурированные данные `StructuredTool`, чтобы передавать их между слоями без словарей."""
    func: Callable
    name: str
    runtime: bool
    args_schema: dict
    args_model: type[BaseModel]
    param_groups: dict[str, ParamGroup]

    def to_tool_params(self) -> FunctionToolParam:
        """Преобразует данные в tool params, чтобы передать их в нужный слой приложения."""
        return FunctionToolParam(type="function", strict=True, **self.args_schema)

    @staticmethod
    def to_tool_result(call_id: str, result: Any) -> dict:
        """Преобразует данные в tool result, чтобы передать их в нужный слой приложения."""
        return {
            "type": "function_call_output",
            "call_id": call_id,
            "output": result
            if isinstance(result, str)
            else json.dumps(result, ensure_ascii=False),
        }

    def build_call_kwargs(self, validated: BaseModel, *, runtime: Any = None) -> dict[str, Any]:
        """
        Собирает kwargs для вызова исходной функции func:
        - для "flat" параметров берёт значение как есть;
        - для "model" параметров восстанавливает исходный BaseModel
          из соответствующих плоских полей;
        - добавляет runtime, если функция его ожидает.
        """
        flat = validated.model_dump()
        call_kwargs: dict[str, Any] = {}

        for param_name, group in self.param_groups.items():
            if group.kind == "flat":
                call_kwargs[param_name] = flat[group.field_names[0]]
            elif group.kind == "model":
                if group.model_cls is None:
                    raise ValueError(
                        f"ParamGroup для '{param_name}' имеет kind='model', "
                        f"но model_cls не задан — некорректная конфигурация param_groups"
                    )
                sub_data = {f: flat[f] for f in group.field_names}
                call_kwargs[param_name] = group.model_cls(**sub_data)
            else:
                raise ValueError(f"Неизвестный kind='{group.kind}' для параметра '{param_name}'")

        if self.runtime:
            call_kwargs["runtime"] = runtime

        return call_kwargs

    async def run_tool(self, raw_args: dict[str, Any], *, runtime: Any = None) -> Any:
        """Выполняет действие `run_tool`, чтобы поддержать основной сценарий модуля."""
        validated = self.args_model.model_validate(raw_args)
        if self.runtime:
            call_kwargs = self.build_call_kwargs(validated, runtime=runtime)
        else:
            call_kwargs = self.build_call_kwargs(validated)
        return await self.func(**call_kwargs)
