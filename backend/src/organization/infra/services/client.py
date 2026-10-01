from src.shared.infra.services import SrvBaseClient

from .config import SrvOrganizationConfig


class SrvOrganizationClient(SrvBaseClient):
    def __init__(self, config: SrvOrganizationConfig) -> None:
        super().__init__(config)


organization_config = SrvOrganizationConfig()  # pyright: ignore[reportCallIssue]
organization_client = SrvOrganizationClient(organization_config)
