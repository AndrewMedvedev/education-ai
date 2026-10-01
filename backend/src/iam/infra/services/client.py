from src.shared.infra.services import SrvBaseClient

from .config import SrvIAMConfig


class SrvIAMClient(SrvBaseClient):
    def __init__(self, config: SrvIAMConfig) -> None:
        super().__init__(config)


iam_config = SrvIAMConfig()  # pyright: ignore[reportCallIssue]
iam_client = SrvIAMClient(iam_config)
