# add_models.py
import asyncio

from sqlalchemy import select

from src.core.database import session_factory

from ..llm_router.domain.dataclass import AIModel
from ..llm_router.infra.models import AIModelOrm

# Импорты из вашего проекта (пути могут отличаться – подставьте свои)
from ..llm_router.infra.repository import SqlAIModelRepository

# ========== ИСХОДНЫЙ СПИСОК МОДЕЛЕЙ ==========
proxy_api_models = [
    {
        "name": "gpt-5-nano",
        "description": (
            "TYPE: TEXT. "
            "TIER: LIGHT. COST: ULTRA_LOW. LATENCY: LOW. "
            "SPECIALIZATION: classification, extraction, routing, metadata, simple-transformations. "
            "REASONING: LOW. "
            "CODING: LOW. "
            "TOOL_CALLING: LOW — подходит для отсутствия tools или одного очевидного вызова; "
            "не использовать для зависимых многошаговых agent workflows. "
            "STRUCTURED_OUTPUT: LOW — подходит для плоских JSON/Pydantic, Enum/Literal/Optional, "
            "list[str], небольших объектов и простой вложенности; "
            "не выбирать для глубоких nested models, больших list[Model], Union/discriminator "
            "или schemas, заполнение которых требует reasoning. "
            "OUTPUT_RELIABILITY: MEDIUM — надёжна для небольших строго определённых outputs. "
            "USE: classification, intent detection, routing, tagging, metadata, extraction, "
            "summary, formatting и массовые дешёвые преобразования. "
            "ESCALATE: если REASONING, CODING или TOOL_CALLING требуют MEDIUM, "
            "либо STRUCTURED_OUTPUT превышает LOW."
        ),
        "context": 400000,
    },
    # {
    #     "name": "gpt-5.6-luna",
    #     "description": (
    #         "TYPE: TEXT. "
    #         "TIER: STANDARD. COST: VERY_LOW. LATENCY: LOW-MEDIUM. "
    #         "SPECIALIZATION: general, long-context, structured-output, coding, agentic. "
    #         "REASONING: MEDIUM. "
    #         "CODING: MEDIUM. "
    #         "TOOL_CALLING: MEDIUM — уверенно выполняет короткие последовательные или параллельные "
    #         "tool workflows, анализирует несколько результатов и выполняет обычный replanning; "
    #         "не предназначена для длинных сложных agent loops с множеством содержательных failures. "
    #         "STRUCTURED_OUTPUT: MEDIUM — подходит для nested Pydantic/JSON Schema, list[Model], "
    #         "нескольких уровней объектов и массивов, Enum/Literal/Optional и schemas среднего размера. "
    #         "Может использоваться как основная модель для обычного production structured output. "
    #         "Для глубокой структуры с множеством типов, сложных Union/discriminator или schema, "
    #         "заполнение которой требует HIGH reasoning, использовать STRONG. "
    #         "OUTPUT_RELIABILITY: HIGH — надёжна для большинства обычных production outputs. "
    #         "USE: основная модель для генерации, планирования контента, RAG, анализа документов, "
    #         "обычного backend/frontend coding, structured generation и умеренных agent workflows. "
    #         "ESCALATE: только если REASONING, CODING, TOOL_CALLING или STRUCTURED_OUTPUT реально HIGH."
    #     ),
    #     "context": 1050000,
    # },
    {
        "name": "gpt-5.4-mini",
        "description": (
            "TYPE: TEXT. "
            "TIER: STRONG. COST: MEDIUM. LATENCY: MEDIUM. "
            "SPECIALIZATION: reasoning, coding, architecture, agentic, structured-output. "
            "REASONING: HIGH. "
            "CODING: HIGH. "
            "TOOL_CALLING: HIGH — подходит для длинных зависимых tool workflows, "
            "анализа больших tool outputs, содержательных failures, recovery и replanning. "
            "STRUCTURED_OUTPUT: HIGH — подходит для глубоких nested JSON/Pydantic schemas, "
            "многоуровневых list[Model], большого количества типов и полей, "
            "Union/discriminator и крупных structured outputs; "
            "особенно полезна, когда корректное заполнение структуры требует сложного reasoning. "
            "OUTPUT_RELIABILITY: HIGH — основной STRONG-вариант для сложных structured outputs. "
            "USE: сложный debugging, архитектура, сложный coding, многошаговый reasoning, "
            "длинные agent workflows и сложные schemas. "
            "DO_NOT_USE: для LOW/MEDIUM задач, которые уверенно выполняет LIGHT или STANDARD. "
            "ESCALATE: на EXPERT только при нескольких критических HIGH-требованиях "
            "или содержательной неудаче STRONG."
        ),
        "context": 1050000,
    },
    {
        "name": "gpt-5.6-terra",
        "description": (
            "TYPE: TEXT. "
            "TIER: EXPERT. COST: HIGH. LATENCY: HIGH. "
            "SPECIALIZATION: advanced-reasoning, advanced-coding, architecture, agentic. "
            "REASONING: HIGH — предназначена для наиболее сложных HIGH reasoning workloads. "
            "CODING: HIGH — предназначена для сложной архитектуры, глубокого debugging, "
            "concurrency, distributed systems и крупных изменений. "
            "TOOL_CALLING: HIGH — подходит для наиболее сложных agent loops, нескольких tools, "
            "больших результатов, recovery, replanning и длинной accumulated history. "
            "STRUCTURED_OUTPUT: HIGH — подходит для глубоких и крупных JSON/Pydantic schemas, "
            "Union/discriminator, множества связанных nested models и outputs, "
            "где заполнение структуры одновременно требует сложного reasoning. "
            "OUTPUT_RELIABILITY: HIGH. "
            "USE: экстремально сложный reasoning, архитектура, debugging, coding "
            "и agent orchestration с несколькими HIGH-требованиями одновременно. "
            "SELECT_ONLY_IF: несколько критических требований имеют HIGH, "
            "либо gpt-5.4-mini уже содержательно не справилась. "
            "DO_NOT_USE: только ради большого context, обычного JSON, обычного coding "
            "или одного MEDIUM-требования."
        ),
        "context": 1050000,
    },
    {
        "name": "gpt-image-2",
        "description": (
            "TYPE: IMAGE. "
            "TIER: STRONG. COST: HIGH. LATENCY: MEDIUM-HIGH. "
            "SPECIALIZATION: image-generation, image-editing, reference-images, high-quality-images. "
            "IMAGE_QUALITY: HIGH. "
            "PROMPT_FOLLOWING: HIGH. "
            "TEXT_RENDERING: HIGH. "
            "EDITING: HIGH. "
            "STRUCTURED_OUTPUT: NOT_APPLICABLE. "
            "USE: сложные финальные иллюстрации, высокая детализация, точная композиция, "
            "фотореализм, reference images, editing и изображения с повышенными требованиями. "
            "SELECT_ONLY_IF: дешёвая IMAGE-модель недостаточна по качеству, композиции, "
            "prompt following, text rendering или editing. "
            "DO_NOT_USE: для обычной массовой генерации простых образовательных изображений."
        ),
        "context": 100000,
    },
]

ai_tunnel_models = [
    {
        "name": "gpt-5-nano",
        "description": (
            "TIER: LIGHT. COST: LOW. "
            "SPECIALIZATION: simple, routing, extraction, structured-output. "
            "REASONING: LOW-MEDIUM — простой диалог, classification, extraction, summary "
            "и выбор следующего очевидного действия. "
            "CODING: LOW. "
            "TOOL_CALLING: LOW-MEDIUM — 1-3 простых calls без сложного recovery/replanning. "
            "STRUCTURED_OUTPUT: HIGH — strict JSON/Pydantic простой и средней вложенности. "
            "TOOLS_WITH_STRUCTURED_OUTPUT: MEDIUM-HIGH — простые tool workflows со strict response. "
            "USE: routing, extraction, transformations, простой диалог, короткие tools и structured output. "
            "DO_NOT_ESCALATE: только из-за длинного prompt, множества правил, доступных tools "
            "или strict schema tool arguments. "
            "ESCALATE: при сложном reasoning/coding, зависимых tools, replanning "
            "или содержательной ошибке."
        ),
        "context": 400000,
    },
    {
        "name": "qwen3.7-flash",
        "description": (
            "TIER: STANDARD. COST: VERY_LOW. "
            "SPECIALIZATION: general, long-context, RAG, generation. "
            "REASONING: MEDIUM. CODING: MEDIUM. "
            "TOOL_CALLING: MEDIUM — хорошо ведёт несколько последовательных или простых параллельных tools, "
            "анализирует outputs и выбирает следующий очевидный шаг. "
            "STRUCTURED_OUTPUT: LOW-MEDIUM — обычный JSON подходит, но strict JSON Schema "
            "нельзя считать гарантированно надёжным. "
            "TOOLS_WITH_STRUCTURED_OUTPUT: LOW — НЕ ВЫБИРАТЬ, если после tool workflow обязательно "
            "нужен strict JSON/Pydantic response. "
            "USE: основной дешёвый worker для RAG, документов, long-context, генерации контента, "
            "анализа, обычных tools, свободного текста и задач средней сложности. "
            "DO_NOT_USE: когда корректный strict structured output является обязательным контрактом. "
            "ESCALATE: при StructuredOutputError, сложном agent workflow, HIGH reasoning/coding "
            "или одновременном требовании tools + strict schema."
        ),
        "context": 1000000,
    },
    {
        "name": "gemini-3.1-flash-lite",
        "description": (
            "TIER: LIGHT. COST: LOW-MEDIUM. "
            "SPECIALIZATION: multimodal, extraction, long-context, structured-output. "
            "REASONING: MEDIUM. CODING: LOW-MEDIUM. "
            "TOOL_CALLING: MEDIUM — подходит для коротких и умеренных chains с понятной логикой действий. "
            "STRUCTURED_OUTPUT: HIGH — поддерживает Structured Outputs и хорошо возвращает вложенные объекты, "
            "arrays, Enum/Literal/Optional и schemas умеренной сложности. "
            "TOOLS_WITH_STRUCTURED_OUTPUT: MEDIUM-HIGH — хороший вариант для коротких agent workflows, "
            "где одновременно нужны tools и валидный structured response. "
            "MULTIMODAL: HIGH — особенно полезна для изображений, PDF, аудио и видео при большом контексте. "
            "USE: extraction, structuring, summary, документы, multimodal-анализ и большой "
            "концептуально несложный контекст. "
            "ESCALATE: при сложном reasoning/coding, длинном autonomous workflow, глубокой schema "
            "с сильными межполевыми зависимостями или повторной содержательной ошибке."
        ),
        "context": 1048576,
    },
    {
        "name": "qwen3-coder-30b-a3b-instruct",
        "description": (
            "TIER: STANDARD. COST: LOW. "
            "SPECIALIZATION: coding, debugging, developer-agents. "
            "REASONING: MEDIUM. CODING: HIGH. "
            "TOOL_CALLING: MEDIUM-HIGH — особенно хороша в developer workflows: чтение файлов, "
            "поиск по repository, правки, tests/linters, анализ ошибок и несколько итераций исправления. "
            "STRUCTURED_OUTPUT: HIGH — поддерживает Structured Outputs и хорошо возвращает "
            "технические JSON/Pydantic, tool arguments, планы изменений и AST-подобные структуры. "
            "TOOLS_WITH_STRUCTURED_OUTPUT: HIGH — предпочтительный дешёвый STANDARD-вариант "
            "для coding agents с обязательным структурированным результатом. "
            "USE: coding, debugging, refactoring, tests, stack traces, API, repository workflows "
            "и генерация большого объёма кода. "
            "ESCALATE: при сложной архитектуре, concurrency, distributed systems, security-critical code, "
            "глубоком repo-wide reasoning или содержательной неудаче."
        ),
        "context": 262144,
    },
    {
        "name": "claude-haiku-4.5",
        "description": (
            "TIER: STANDARD. COST: MEDIUM-HIGH. "
            "SPECIALIZATION: instruction-following, structured-output, text, coding. "
            "REASONING: MEDIUM. CODING: MEDIUM. "
            "TOOL_CALLING: MEDIUM-HIGH — несколько зависимых calls и анализ outputs. "
            "STRUCTURED_OUTPUT: HIGH — сложные вложенные schemas и точное соблюдение формата. "
            "TOOLS_WITH_STRUCTURED_OUTPUT: HIGH — MEDIUM tool workflows со strict response. "
            "USE: STANDARD-задачи со сложными инструкциями, schemas или зависимыми tools. "
            "DO_NOT_USE: простой диалог, classification, extraction, summary, один очевидный tool call "
            "или только из-за большого количества инструкций. "
            "PREFER_LIGHT: если LIGHT-модель явно покрывает текущую работу. "
            "ESCALATE: при HIGH reasoning/coding, сложном agent workflow или содержательной ошибке."
        ),
        "context": 200000,
    },
    {
        "name": "gpt-5-mini",
        "description": (
            "TIER: STRONG. COST: MEDIUM. "
            "SPECIALIZATION: reasoning, coding, agentic, structured-output. "
            "REASONING: HIGH. CODING: HIGH. "
            "TOOL_CALLING: HIGH — хорошо управляет многошаговыми tool chains, анализирует failures, "
            "делает retries и меняет план выполнения. "
            "STRUCTURED_OUTPUT: HIGH — поддерживает Structured Outputs и хорошо справляется "
            "с глубокими Pydantic/JSON schemas, крупными list[Model], Union и связанными полями. "
            "TOOLS_WITH_STRUCTURED_OUTPUT: HIGH — надёжный STRONG-вариант для задач, где одновременно "
            "нужны развитые tools и строгий финальный формат. "
            "MULTIMODAL: HIGH — принимает текст, изображения и документы/PDF. "
            "USE: сложный debugging, архитектурный анализ, неоднозначный код, reasoning "
            "и сложные agent workflows. "
            "DO_NOT_USE: для LIGHT/STANDARD-задач, если более дешёвая модель уверенно справляется. "
            "ESCALATE: при очень длинном workflow, экстремально сложном reasoning "
            "или повторной содержательной неудаче."
        ),
        "context": 400000,
    },
    {
        "name": "gpt-5.6-luna-pro",
        "description": (
            "TIER: STRONG. COST: LOW-MEDIUM. "
            "SPECIALIZATION: reasoning, coding, agentic, long-context, structured-output. "
            "REASONING: HIGH. CODING: HIGH. "
            "TOOL_CALLING: HIGH — уверенно ведёт длинные sequential/parallel workflows, "
            "учитывает большие tool outputs, failures, retries и replanning. "
            "STRUCTURED_OUTPUT: VERY_HIGH — предпочтительный вариант для сложных JSON/Pydantic schemas, "
            "глубокой вложенности, крупных list[Model], Union/discriminator "
            "и логически связанных обязательных полей. "
            "TOOLS_WITH_STRUCTURED_OUTPUT: VERY_HIGH — основной STRONG fallback, когда одновременно "
            "требуются сложные tools и обязательный strict structured response. "
            "MULTIMODAL: HIGH — принимает текст, изображения и документы/PDF. "
            "LONG_CONTEXT: VERY_HIGH — подходит для очень длинной истории, документов и больших tool outputs. "
            "USE: сложные agents, архитектура, debugging, reasoning, long-context "
            "и schema-critical workflows. "
            "DO_NOT_USE: для простых задач, если LIGHT/STANDARD-модель уверенно справляется. "
            "ESCALATE: только при экстремальной сложности или повторной содержательной неудаче STRONG."
        ),
        "context": 1050000,
    },
    {
        "name": "gemini-3.7-flash",
        "description": (
            "TIER: STANDARD. COST: MEDIUM-HIGH. "
            "SPECIALIZATION: multimodal, reasoning, coding, agentic, long-context. "
            "REASONING: MEDIUM-HIGH. CODING: MEDIUM-HIGH. "
            "TOOL_CALLING: HIGH — хорошо ведёт sequential/parallel tools, search/read/analyze workflows "
            "и умеренный replanning. "
            "STRUCTURED_OUTPUT: HIGH — подходит для вложенных JSON/Pydantic, крупных list[Model], "
            "Enum/Literal/Optional и сложных многоуровневых структур. "
            "TOOLS_WITH_STRUCTURED_OUTPUT: HIGH — хороший верхний STANDARD-вариант, когда одновременно "
            "нужны развитые tools и строгий structured response. "
            "MULTIMODAL: VERY_HIGH — особенно сильный вариант для текста, изображений, PDF, аудио и видео. "
            "LONG_CONTEXT: VERY_HIGH — подходит для анализа больших документов и multimodal-контекста. "
            "USE: сложный STANDARD-анализ, multimodal, код, большие документы и развитые agent workflows. "
            "DO_NOT_USE: для обычного текста или простых structured задач, если более дешёвая модель достаточна. "
            "ESCALATE: когда reasoning/coding действительно HIGH, workflow становится очень длинным "
            "или произошла повторная содержательная/форматная неудача."
        ),
        "context": 1048576,
    },
    {
        "name": "gpt-image-2",
        "description": (
            "TYPE: IMAGE. "
            "TIER: STRONG. COST: MEDIUM. LATENCY: MEDIUM-HIGH. "
            "SPECIALIZATION: image-generation, image-editing, reference-images, high-quality-images. "
            "IMAGE_QUALITY: HIGH. "
            "PROMPT_FOLLOWING: HIGH. "
            "TEXT_RENDERING: HIGH. "
            "EDITING: HIGH. "
            "STRUCTURED_OUTPUT: NOT_APPLICABLE. "
            "USE: качественные образовательные иллюстрации, сложная композиция, высокая детализация, "
            "фотореализм, изображения с текстом, reference images и editing. "
            "SELECT_ONLY_IF: задача действительно требует генерации или редактирования изображения. "
            "DO_NOT_USE: для задач без визуального результата."
        ),
        "context": 100000,
    },
]


# ========== ЛОГИКА ДОБАВЛЕНИЯ ==========
async def add_models_to_db(session, models_data):
    """
    Добавляет или обновляет модели в БД.
    Если модель с таким name уже существует – обновляет description и context.
    Иначе создаёт новую запись.
    """
    repo = SqlAIModelRepository(session)

    for data in models_data:
        # Проверяем существование по уникальному полю name
        stmt = select(AIModelOrm).where(AIModelOrm.name == data["name"])
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Обновляем существующую запись (updated_at обновится автоматически)
            await repo.update(
                existing.id,
                description=data["description"],
                context=data["context"],
            )
        else:
            # Создаём новую доменную сущность (id генерируется автоматически)
            new_entity = AIModel(
                name=data["name"],
                description=data["description"],
                context=data["context"],
            )
            await repo.create(new_entity)

    # Фиксируем все изменения
    await session.commit()


# ========== ТОЧКА ВХОДА ==========
async def main():
    # ЗАМЕНИТЕ СТРОКУ ПОДКЛЮЧЕНИЯ НА ВАШУ

    """Запускает сценарий модуля и связывает подготовку данных с основным действием."""
    async with session_factory() as session:
        await add_models_to_db(session, ai_tunnel_models)

    print("✅ Все модели успешно добавлены/обновлены.")


if __name__ == "__main__":
    asyncio.run(main())
