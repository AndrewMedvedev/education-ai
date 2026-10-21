from src.llm_router.domain.vo import LLMInvocationStatus


def test_llm_invocation_status_values() -> None:
    assert LLMInvocationStatus.COMPLETED == "completed"
    assert LLMInvocationStatus.FAILED == "failed"