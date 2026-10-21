import asyncio
from uuid import UUID

from qdrant_client import models

from src.core.qdrant import qdrant_client
from src.core.retrieval import embeddings_config
from src.core.tkq import taskiq_broker
from src.courses.infra.tasks import index_lesson  # регистрирует задачу в брокере

COURSE_ID = UUID("693e6c1a-44a5-46f1-a7b3-d94345a670ee")  # замените на UUID курса
LESSON_ID = UUID("7e821688-a970-45b8-951a-649a7319295f")  # замените на UUID урока


async def main() -> None:
    exists = await qdrant_client.collection_exists("MAIN_COLLECTION")
    if not exists:
        await qdrant_client.create_collection(
            collection_name="MAIN_COLLECTION",
            vectors_config={
                "dense": models.VectorParams(
                    size=embeddings_config.dimensions,
                    distance=models.Distance.COSINE,
                )
            },
            sparse_vectors_config={"bm25": models.SparseVectorParams()},
        )
    await taskiq_broker.startup()
    try:
        result = await index_lesson.kiq(
            course_id=COURSE_ID,
            lesson_id=LESSON_ID,
        )
        print(f"Задача отправлена: task_id={result.task_id}")
    finally:
        await taskiq_broker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
