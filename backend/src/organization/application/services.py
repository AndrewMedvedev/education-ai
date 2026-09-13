from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.domain.exceptions import AlreadyExistsError, NotFoundError

from ..domain.entities import Organization
from .dtos import OrganizationCreate, OrganizationEdit
from .repos import OrganizationRepository


class OrganizationService:
    def __init__(self, session: AsyncSession, repository: OrganizationRepository) -> None:
        self.session = session
        self.repository = repository

    async def create(self, data: OrganizationCreate) -> Organization:
        """Создание нового контрагента (по умолчанию головной)"""
        # 1. Проверка на уникальность (ИНН + email)
        exists_organization = await self.repository.get_by_email(email=data.email)
        if exists_organization is not None:
            raise AlreadyExistsError(f"Organization with email {data.email} already exists")

        # 4. Создание доменной сущности
        organization = Organization(
            name=data.name,
            email=data.email,
            description=data.description,
        )

        # 5. Запись в базу данных
        await self.repository.create(organization)
        await self.session.commit()

        return organization

    async def read(self, organization_id: UUID) -> Organization:
        """
        Чтение информации о организации
        """
        organization_exists = await self.repository.read(organization_id)
        if organization_exists is None:
            raise NotFoundError(f"Organization with ID {organization_id} not found")
        return await self.repository.read(organization_id)  # pyright: ignore[reportReturnType]

    async def edit(
        self,
        organization_id: UUID,
        data: OrganizationEdit,
    ) -> Organization:
        """
        Редактирование информации о организации
        """
        # 1. Проверка на существование
        organization = await self.repository.read(organization_id)
        if organization is None:
            raise NotFoundError(f"Organization with ID {organization_id} not found")

        # 2. Редактирование и обновление сущности
        organization.edit(
            name=data.name,
            email=data.email,
            description=data.description,
        )
        await self.repository.upsert(organization)
        await self.session.commit()

        return organization
