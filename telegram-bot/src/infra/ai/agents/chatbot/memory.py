# Модуль реализует инструменты для работы с персональной долгосрочной памятью о пользователе

from typing import Any, Literal

import logging

from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field, NonNegativeFloat

from ... import rag
from ..schemas import UserContext

INDEX_NAME = "memory-index"

MemoryType = Literal["facts", "episodic", "semantic"]

logger = logging.getLogger(__name__)


class RememberInput(BaseModel):
    """Входные аргументы для запоминания информации"""

    text: str = Field(
        min_length=3,
        description="""\
        Чёткий, сжатый и самодостаточный факт / событие / предпочтение / знание о пользователе.
        Записывай его как нейтральное утверждение от третьего лица или как прямую цитату,
        если уместно.
        """
    )
    confidence: NonNegativeFloat = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="""\
        Твоя субъективная уверенность (0.0–1.0) в том, что эта информация верна,
        актуальна и не вырвана из контекста. Используй меньшие значения
        для неоднозначных / устаревших / полученных из вторых рук данных.
        """
    )
    memory_type: MemoryType = Field(
        description="""\
        Категория воспоминания:"
         - 'facts' — устойчивые, проверяемые факты (возраст, профессия,
            предпочтения, аллергии и т.п.)
         - 'episodic' — конкретные события, разговоры, переживания, привязанные ко времени/месту"
         - 'semantic' — обобщённые знания/предпочтения/отношения,
            извлечённые из множества взаимодействий
        """
    )


@tool(
    "remember",
    description=(
        "Сохраняет новую важную информацию о текущем пользователе"
        "в постоянном индексе семантической памяти.\n"
        "Используй этот инструмент всякий раз, когда узнаёшь или подтверждаешь любой личный факт,"
        "предпочтение, событие, неприязнь, аллергию, цель, привычку или другую деталь,"
        "которая может пригодиться в будущих разговорах.\n\n"
        "Рекомендации:\n"
        " - Извлекай только одну чёткую атомарную единицу информации за вызов\n"
        " - Будь максимально фактологичен и избегай интерпретаций\n"
        " - Устанавливай реалистичный уровень уверенности\n"
        " - Выбирай наиболее подходящий тип памяти (memory_type)\n"
        " - НЕ сохраняй мимолётную болтовню, шутки, текущую дату/время"
        "или очевидно временные состояния"
    ),
    args_schema=RememberInput,
)
async def remember(
        runtime: ToolRuntime[UserContext], text: str, confidence: float, memory_type: MemoryType
) -> None:
    logger.info(
        "Remembering [%s] information (conf=%.2f): '%s ...'",
        memory_type, confidence, text[:100]
    )
    await rag.index_document(
        index_name=INDEX_NAME,
        text=text,
        metadata={
            "user_id": runtime.context.user_id,
            "memory_type": memory_type,
            "confidence": confidence,
        }
    )


class SearchMemoryInput(BaseModel):
    """Входные аргументы для поиска релевантной памяти"""

    query: str = Field(
        description="""\
        Естественно-языковой запрос или информационная потребность.
        Чем точнее и контекстно-богаче запрос — тем лучше результаты.
        """
    )
    memory_type: MemoryType = Field(
        description="""\
        В какой категории памяти искать. Выбери только одну:
         - 'facts' — для стабильных личных фактов и предпочтений
         - 'episodic' — когда нужен контекст конкретных прошлых событий/разговоров
         - 'semantic' — при поиске обобщённых знаний или отношений
        """
    )


def format_result(document: str, metadata: dict[str, Any], distance: float | None = None) -> str:
    return (
        f"**Relevance score:** {round(distance, 2)}\n"
        f"**Memory type:** {metadata.get('memory_type', '')}\n"
        f"**Confidence:** {metadata.get('confidence', 0.0)}\n"
        "**Document:**\n"
        f"{document}"
    )


@tool(
    "search_memory",
    description="""\
    Ищет в долговременной памяти пользователя релевантные прошлые факты, события или предпочтения.
    Используй этот инструмент перед ответом на вопросы,
    которые могут зависеть от личного контекста, истории, предпочтений, аллергий,
    предыдущих договорённостей, целей и т.д.

    Лучшие сценарии применения:
     - Когда пользователь спрашивает о своих собственных предпочтениях / истории / ранее сказанном
     - Для поддержания согласованности в длинных разговорах
     - Чтобы не переспрашивать уже известную информацию
     - Для персонализации ответов на основе более раннего контекста
    """,
    args_schema=SearchMemoryInput,
)
async def search_memory(
        runtime: ToolRuntime[UserContext], query: str, memory_type: MemoryType
) -> str:
    logger.info("Searching [%s] memory for query: '%s ...'", memory_type, query[:100])
    docs = await rag.retrieve_documents(
        index_name=INDEX_NAME,
        query=query,
        metadata_filter={
            "$and": [{"user_id": runtime.context.user_id}, {"memory_type": memory_type}]
        },
        format_result_func=format_result,
    )
    return "\n\n".join(docs)
