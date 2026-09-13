import operator

from aiohttp import ClientSession
from openai import AsyncOpenAI

from .config import embeddings_config, rerankers_config

embeddings = AsyncOpenAI(base_url=embeddings_config.base_url, api_key="dummy")


async def embed(
    inputs: list[str],
) -> list[list[float]]:
    """Создаёт векторное представление текста"""

    response = await embeddings.embeddings.create(
        model=embeddings_config.model_name,
        input=inputs,
        dimensions=embeddings_config.dimensions,
    )

    # Сохранение порядка как при передаче текста
    sorted_data = sorted(response.data, key=lambda x: x.index)

    return [item.embedding for item in sorted_data]


async def rerank(
    query: str,
    documents: list[str],
    top_n: int | None = None,
) -> list[dict]:
    """Переранжирует документы по релевантности к запросу.

    Возвращает список словарей с ключами:
      - index: исходный индекс документа
      - relevance_score: релевантность от 0 до 1
      - document: текст документа
    """

    async with (
        ClientSession(base_url=rerankers_config.base_url) as session,
        session.post(
            "/rerank",
            json={
                "model": rerankers_config.model_name,
                "query": query,
                "documents": documents,
                "top_n": top_n or len(documents),
            },
        ) as response,
    ):
        response.raise_for_status()
        data = await response.json()

    return sorted(
        data["results"],
        key=operator.itemgetter("relevance_score"),
        reverse=True,
    )
