# pyright: reportArgumentType=false


from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.domain.exceptions import NotFoundError

from ..repos import (
    BasicInfoProtocol,
)


class BaseCourseService[RepoT: BasicInfoProtocol]:
    def __init__(self, repo: RepoT, session: AsyncSession) -> None:
        """Инициализирует объект и сохраняет зависимости, необходимые для дальнейшей работы."""
        self.repo = repo
        self.session = session

    async def get_basic_info(self, uid: UUID):
        """Получает basic info, чтобы вызывающий код работал через единый интерфейс."""
        result = await self.repo.get_by_id_basic_info(uid)
        if result is not None:
            return result
        raise NotFoundError
