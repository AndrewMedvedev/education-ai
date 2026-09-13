from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from ..schemas import RuntimeContext


async def invoke_or_resume(
    graph: CompiledStateGraph[Any, RuntimeContext, Any, Any],
    *,
    input_data: dict[str, Any],
    config: RunnableConfig,
    context: RuntimeContext,
) -> dict[str, Any]:
    snapshot = await graph.aget_state(config)

    if snapshot.next:
        return await graph.ainvoke(
            None,
            config=config,
            context=context,
            durability="sync",
        )

    if snapshot.values:
        return dict(snapshot.values)

    return await graph.ainvoke(
        input_data,
        config=config,
        context=context,
        durability="sync",
    )
