import asyncio

from faststream.rabbit import RabbitQueue

from src.core.rabbit import events_exchange as exchange
from src.core.rabbit import router as rabbit_router
from src.shared.dependencies.database import DBSession

from ..dependencies import LLMInvocationRepoDep, MediaClientDep
from ..domain.dataclass import LLMInvocation
from ..domain.events import LLMInvocationCreated

MAX_CONCURRENT_INVOCATION_LOGS = 5

invocation_queue = RabbitQueue(
    "llm_invocation_created",
    durable=True,
    routing_key=LLMInvocationCreated.event_type,
)
invocation_semaphore = asyncio.Semaphore(MAX_CONCURRENT_INVOCATION_LOGS)


@rabbit_router.subscriber(invocation_queue, exchange)
async def on_llm_invocation_created(
    event: LLMInvocationCreated,
    repository: LLMInvocationRepoDep,
    session: DBSession,
    media_client: MediaClientDep,
) -> None:
    """Сохраняет события мониторинга в PostgreSQL не более чем по пять одновременно."""
    async with invocation_semaphore:
        request = event.request.copy()
        if images := request.get("image"):
            request["image"] = [
                await media_client.save_image(image, folder="llm-inputs") for image in images
            ]
        invocation = LLMInvocation(
            id=event.event_id,
            request_id=event.request_id,
            model=event.model,
            total_tokens=event.total_tokens,
            request=request,
            response=event.response,
            duration_ms=event.duration_ms,
            status=event.status,
            error=event.error,
        )
        await repository.create(invocation)
        await session.commit()
