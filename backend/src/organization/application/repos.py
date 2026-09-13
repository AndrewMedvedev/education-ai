from src.shared.application.repos import Repository

from ..domain.entities import Organization


class OrganizationRepository(Repository[Organization]):
    async def get_by_email(self, email: str) -> Organization | None: ...
