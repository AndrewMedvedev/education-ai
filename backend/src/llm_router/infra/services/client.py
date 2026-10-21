from src.shared.infra.services import SrvBaseClient

from .config import SrvLLMRouterConfig


class SrvLLMRouterClient(SrvBaseClient):
    def __init__(self, config: SrvLLMRouterConfig) -> None:
        super().__init__(config)


llm_router_config = SrvLLMRouterConfig()  # pyright: ignore[reportCallIssue]
llm_router_client = SrvLLMRouterClient(llm_router_config)
