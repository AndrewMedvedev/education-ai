from dataclasses import dataclass

from pydantic import EmailStr

from src.shared.domain.entities import AggregateRoot
from src.shared.utils.time import current_datetime


@dataclass(kw_only=True)
class Organization(AggregateRoot):
    name: str
    email: EmailStr
    description: str
    is_active: bool = True

    def edit(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        email: EmailStr | None = None,
    ) -> None:
        """
        Редактирование основных данных организации.
        """

        is_edited = False

        if name is not None and name.strip() and name.strip() != self.name:
            self.name = name.strip()
            is_edited = True

        if email is not None and email != self.email:
            self.email = email
            is_edited = True

        if (
            description is not None
            and description.strip()
            and description.strip() != self.description
        ):
            self.description = description.strip()
            is_edited = True

        if is_edited:
            self.updated_at = current_datetime()
