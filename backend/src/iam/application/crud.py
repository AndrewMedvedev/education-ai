from uuid import UUID

from src.iam.domain.entities import User
from src.iam.domain.vo import FullName, Username
from src.shared.application.repos import get_or_raise_404

from .dtos.users import UpdateUserDTO
from .repos import UserRepository


async def update_handler(user_id: UUID, dto: UpdateUserDTO, user_repo: UserRepository) -> User:

    user = await get_or_raise_404(user_repo.read, user_id, User)

    username = Username(dto.username) if dto.username is not None else None
    full_name = FullName(dto.full_name) if dto.full_name is not None else None

    user.update(username=username, full_name=full_name, avatar_url=dto.avatar_url)

    return user


async def delete_handler(user_id: UUID, user_repo: UserRepository) -> User:

    user = await get_or_raise_404(user_repo.read, user_id, User)

    user.deactivate()

    return user
