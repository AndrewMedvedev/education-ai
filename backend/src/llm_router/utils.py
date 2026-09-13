from typing import Any

import asyncio
import json
import logging
import re
import uuid

import openai
import orjson
from json_repair import repair_json
from langsmith import traceable
from openai.types.responses.response import Response
from tenacity import RetryCallState

from src.core.redis import redis_client
from src.llm_service.schemas import LLMTextResponse, ToolCallParsed
from src.shared.application.dtos import Page
from src.shared.domain.exceptions import NotFoundError

logger = logging.getLogger(__name__)


_JSON_FENCE_RE = re.compile(
    r"\A\s*```(?:json)?\s*\n(.*)\n```\s*\Z",
    re.DOTALL | re.IGNORECASE,
)


RETRYABLE_STATUS_CODES = {
    429,
    500,
    502,
    503,
    504,
}

NUMBER_RETRY_STATUS_CODES = 4

NUMBER_RETRY = 3


def get_status_code(exc: BaseException) -> int | None:

    if isinstance(exc, openai.APIStatusError):
        return exc.status_code

    return None


def is_retryable_error(exc: BaseException) -> bool:

    if isinstance(exc, (KeyboardInterrupt, SystemExit)):
        return False

    if isinstance(exc, openai.APIStatusError):
        return exc.status_code in RETRYABLE_STATUS_CODES
    if isinstance(exc, StructuredOutputError):
        return True
    return isinstance(exc, Exception)


def wait_strategy(retry_state: RetryCallState) -> float:
    outcome = retry_state.outcome

    if outcome is None:
        return 0.0
    exc = outcome.exception()

    if exc is None:
        return 0.0

    attempt = retry_state.attempt_number
    status_code = get_status_code(exc)

    if status_code == 429:
        response = getattr(exc, "response", None)

        if response is not None:
            retry_after = response.headers.get("retry-after")

            if retry_after:
                try:
                    return float(retry_after)
                except (TypeError, ValueError):
                    pass

        # 5, 10, 20, 40, 60, 60...
        return min(
            60.0,
            5.0 * (2 ** (attempt - 1)),
        )

    if status_code is not None and 500 <= status_code <= 599:
        # 3, 6, 12, 24, 30...
        return min(
            30.0,
            3.0 * (2 ** (attempt - 1)),
        )

    # Ошибка нашего кода:
    # 1, 2, 4...
    return min(
        5.0,
        1.0 * (2 ** (attempt - 1)),
    )


def stop_strategy(retry_state: RetryCallState) -> bool:
    outcome = retry_state.outcome

    if outcome is None:
        return False

    exc = outcome.exception()

    if exc is None:
        return True

    attempt = retry_state.attempt_number
    status_code = get_status_code(exc)

    if status_code in RETRYABLE_STATUS_CODES:
        return attempt >= NUMBER_RETRY_STATUS_CODES

    return attempt >= NUMBER_RETRY


class StructuredOutputError(ValueError):
    """Модель не смогла вернуть ожидаемый structured output."""


def extract_json(text: str) -> dict[str, Any]:
    """
    Извлекает из ответа LLM JSON-объект.

    Возвращает только dict.
    JSON-массивы, строки, числа и другие JSON-типы считаются
    некорректным structured output.

    Если модель вернула не JSON (например, свободный markdown-текст
    вместо structured output), метод сразу бросает StructuredOutputError,
    а не пытается "вытащить" JSON из произвольного места текста —
    это защищает от ложного восстановления мусорного dict из фигурных
    скобок LaTeX-формул, markdown-таблиц и т.п. внутри обычного текста.
    """
    if not text or not text.strip():
        raise StructuredOutputError("LLM returned empty structured output")

    text = text.strip()

    # Снимаем внешний markdown-фенс, только если он оборачивает
    # ВЕСЬ ответ целиком (заякорено к началу/концу строки).
    match = _JSON_FENCE_RE.match(text)
    if match:
        text = match.group(1).strip()

    # Если после снятия фенса текст даже не начинается с "{" — это
    # не JSON-объект, а произвольный текст (модель проигнорировала
    # structured output). Раньше здесь брался кандидат "между первой
    # { и последней } во всём тексте", что на свободном markdown-тексте
    # с LaTeX-формулами (\text{...}, \mathbf{...}) или таблицами
    # захватывало случайные фрагменты и repair_json собирал из них
    # мусорный, но валидный dict без нужных полей. Теперь просто
    # честно бросаем ошибку.
    if not text.startswith("{"):
        raise StructuredOutputError(
            "Model did not return a JSON object despite structured output "
            f"request. Response starts with: {text[:200]!r}"
        )

    try:
        repaired = repair_json(text, return_objects=False)
        parsed = orjson.loads(repaired)

        if isinstance(parsed, dict):
            return parsed

    except Exception:  # ruff: ignore[blind-except, try-except-pass]
        pass

    raise StructuredOutputError(
        f"LLM response does not contain a valid JSON object. Response: {text[:500]!r}"
    )


def _expects_structured_output(
    text_format: dict[str, Any] | None,
) -> bool:
    """Проверяет, ожидает ли текущий запрос JSON Schema response."""

    if text_format is None:
        return False

    format_data = text_format.get("format")

    if not isinstance(format_data, dict):
        return False

    return format_data.get("type") == "json_schema"


def _normalize_input_messages(
    input_messages: list[dict[str, Any]] | str,
) -> list[dict[str, Any]]:
    """Приводит вход LLM к единому формату истории сообщений."""

    if isinstance(input_messages, str):
        return [
            {
                "role": "user",
                "content": input_messages,
            }
        ]

    if isinstance(input_messages, list):
        return list(input_messages)

    return []


def _response_item_to_dict(item: Any) -> dict[str, Any]:
    """

    Lossless-преобразование output item Responses API в dict.

    Критически важно НЕ фильтровать reasoning/function_call/message.

    Например reasoning-модель может вернуть:

        reasoning

        message

        function_call

    Все эти элементы должны попасть в следующий input Responses API.

    Если удалить reasoning, API может вернуть:

        Item 'msg_...' of type 'message' was provided

        without its required 'reasoning' item: 'rs_...'

    """

    if hasattr(item, "model_dump"):
        return item.model_dump(
            mode="json",
            exclude_none=True,
            exclude_unset=True,
        )

    if isinstance(item, dict):
        return dict(item)

    try:
        return dict(item)

    except (TypeError, ValueError) as exc:
        raise TypeError(f"Unsupported Responses API output item: {type(item)!r}") from exc


@traceable(run_type="parser", name="ParseLLMResponse")
def parse_llm_response(  # ruff: ignore[complex-structure]
    response: Response,
    input_messages: list[dict[str, Any]] | str,
    text_format: dict[str, Any] | None = None,
) -> LLMTextResponse:
    """
    Парсит один ответ Responses API.

    messages:
        Полная история текущего LLM-loop:
        предыдущий input + новые сообщения/function_call модели.

    output:
        dict только если запрос использовал json_schema.

    raw_text:
        Сырой текст ответа модели.
        Для обычного текстового запроса это основной результат.

    Если json_schema передана, но модель вернула пустой, невалидный JSON
    или JSON не типа object, выбрасывается StructuredOutputError.
    """
    if response.error:
        raise ValueError(response.error)
    if getattr(response, "status", None) == "incomplete":
        reason = getattr(getattr(response, "incomplete_details", None), "reason", None)
        raise StructuredOutputError(
            f"LLM response incomplete (reason={reason}); cannot parse structured output"
        )

    messages = _normalize_input_messages(input_messages)

    tool_calls: list[ToolCallParsed] = []
    output_parts: list[str] = []

    for item in getattr(response, "output", None) or []:
        item_type = getattr(item, "type", None)

        item_dict = _response_item_to_dict(item)

        messages.append(item_dict)

        if item_type == "message":
            for content in getattr(item, "content", None) or []:
                if getattr(content, "type", None) != "output_text":
                    continue

                text = getattr(content, "text", "")

                if text:
                    output_parts.append(text)
        elif item_type == "function_call":
            raw_arguments = getattr(item, "arguments", "{}") or "{}"

            try:
                arguments = json.loads(raw_arguments)
            except (json.JSONDecodeError, TypeError):
                logger.warning(
                    "Model returned invalid tool arguments for %s: %r",
                    getattr(item, "name", None),
                    raw_arguments,
                )
                arguments = {}

            tool_calls.append(
                ToolCallParsed(
                    call_id=item.call_id,
                    name=item.name,
                    arguments=arguments,
                )
            )

    output_buffer = "".join(output_parts)

    # Иногда SDK уже предоставляет агрегированный output_text.
    if not output_buffer:
        response_output_text = getattr(
            response,
            "output_text",
            None,
        )

        if response_output_text:
            output_buffer = response_output_text

    structured_output = _expects_structured_output(text_format)

    output: dict[str, Any] | None = None

    if structured_output and not tool_calls:
        if not output_buffer:
            raise StructuredOutputError(
                "Structured output was requested, but the model returned no output_text"
            )

        output = extract_json(output_buffer)

    return LLMTextResponse(
        messages=messages,
        output=output,
        raw_text=output_buffer or None,
        tool_calls=tool_calls,
        total_tokens=(response.usage.total_tokens if response.usage is not None else 0),
    )


async def cache_ai_models(
    func,
    ttl: int = 60 * 60,
    key: str = "ai_models",
    *args,
    **kwargs,
) -> Page:
    """Кэширует AI-модели, чтобы уменьшить число обращений к источнику."""

    cached = await redis_client.get(key)

    if cached is not None:
        return Page.model_validate_json(cached)

    lock_key = f"lock:{key}"
    lock_id = str(uuid.uuid4())

    got_lock = await redis_client.set(
        lock_key,
        lock_id,
        nx=True,
        ex=10,
    )

    if got_lock:
        try:
            result: Page = await func(
                *args,
                **kwargs,
            )

            if result is None:
                raise NotFoundError("Модели не найдены")

            await redis_client.set(
                key,
                result.model_dump_json(),
                ex=ttl,
            )

            return result

        finally:
            current = await redis_client.get(lock_key)

            if current == lock_id:
                await redis_client.delete(lock_key)

    # Другой процесс уже заполняет кэш.
    for _ in range(50):
        await asyncio.sleep(0.1)

        cached = await redis_client.get(key)

        if cached is not None:
            return Page.model_validate_json(cached)

    # Не дождались — вычисляем самостоятельно.
    result = await func(
        *args,
        **kwargs,
    )

    if result is None:
        raise NotFoundError("Модели не найдены")

    await redis_client.set(
        key,
        result.model_dump_json(),
        ex=ttl,
    )

    return result


def to_langsmith_llm_output(result: LLMTextResponse | None) -> dict[str, Any]:
    if result is None:
        return {
            "output": None,
            "usage_metadata": {"input_tokens": None, "output_tokens": None, "total_tokens": None},
        }
    return {
        "output": result,
        "usage_metadata": {
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": result.total_tokens,
        },
    }
