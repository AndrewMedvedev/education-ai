from uuid import uuid4

from src.llm_router.domain.dataclass import AIModel, LLMInvocation
from src.llm_router.domain.vo import LLMInvocationStatus


def test_ai_model_creates_with_all_fields() -> None:
    model = AIModel(
        name="gpt-5-mini",
        description="Small model",
        context=128000,
    )

    assert model.name == "gpt-5-mini"
    assert model.description == "Small model"
    assert model.context == 128000


def test_llm_invocation_creates_with_default_values() -> None:
    request_id = uuid4()

    invocation = LLMInvocation(
        request_id=request_id,
        model="gpt-5-mini",
        request={"input": "test"},
        response={"output": "result"},
        status=LLMInvocationStatus.COMPLETED,
    )

    assert invocation.request_id == request_id
    assert invocation.model == "gpt-5-mini"
    assert invocation.total_tokens == 0
    assert invocation.request == {"input": "test"}
    assert invocation.response == {"output": "result"}
    assert invocation.duration_ms == 0
    assert invocation.status is LLMInvocationStatus.COMPLETED
    assert invocation.error is None