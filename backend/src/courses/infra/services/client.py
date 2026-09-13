from src.shared.infra.services import SrvBaseClient

from .config import SrvCourseConfig


class SrvCourseClient(SrvBaseClient):
    def __init__(self, config: SrvCourseConfig) -> None:
        super().__init__(config)


course_config = SrvCourseConfig()  # pyright: ignore[reportCallIssue]
course_client = SrvCourseClient(course_config)
