"""
Протоколы (Protocol) для репозиториев.

Общий CRUD-набор вынесен в `RepositoryProtocol` — под него подходит базовый
`SqlAlchemyRepository`. Специфичные репозитории (Lesson/Module/Course/Document)
расширяют его дополнительными методами через структурное наследование протоколов.

`ChatRepositoryProtocol` и `PracticeRepositoryProtocol` формально наследуют
`RepositoryProtocol`, но переопределяют `read`/`update` несовместимыми
сигнатурами (составной ключ вместо одного uid). Это нарушение принципа
подстановки Лисков: код, типизированный через `RepositoryProtocol[Chat]`
или `RepositoryProtocol[Practice]`, может упасть в рантайме при вызове
`read(uid)`/`update(uid, **kwargs)` на объекте одного из этих протоколов.
См. подробное предупреждение в докстринге каждого из них.
"""

from __future__ import annotations

from typing import Any, Protocol

from uuid import UUID

from src.courses.domain.entities import (
    AnyContentBlock,
    Chat,
    Course,
    CourseProgress,
    Document,
    Entity,
    Invitation,
    Lesson,
    LessonProgress,
    Member,
    Module,
    ModuleProgress,
    Practice,
)
from src.courses.domain.events import LessonProgressUpdated
from src.courses.domain.vo import MemberRole
from src.courses.infra.services.client import SrvCourseClient
from src.iam.application.dtos import InvitationCreate as IAMInvitationCreate
from src.iam.application.dtos import UserResponse
from src.iam.domain.entities import Invitation as IAMInvitation
from src.iam.domain.entities import Membership
from src.organization.application.dtos import InvitationCreate as OrganizationInvitationCreate
from src.organization.domain.entities import Invitation as OrganizationInvitation
from src.shared.application.dtos import Page, Pagination
from src.shared.application.repos import Repository
from src.shared.domain.vo import Email

from .dtos import BasicInfo, CourseBasicInfo, LessonBasicInfo, ModuleBasicInfo


class BasicInfoProtocol[EntityT: Entity, BasicInfoT](Repository[EntityT]):
    """
    Промежуточный протокол: базовый CRUD + получение "базовой информации" по id.

    Добавляет один метод сверх `RepositoryProtocol` — `get_by_id_basic_info`,
    сигнатура которого (`uid -> BasicInfoT | None`) одинакова для Lesson,
    Module и Course, различается только конкретный тип `BasicInfoT`.
    Сам протокол напрямую не используется репозиториями — служит общим
    предком для `LessonRepositoryProtocol`, `ModuleRepositoryProtocol`
    и `CourseRepositoryProtocol`.
    """

    async def get_by_id_basic_info(self, uid: UUID) -> BasicInfoT | None:
        """Возвращает краткую информацию о сущности без загрузки всех данных."""

    async def read_course_ownership(
        self,
        uid: UUID,
    ) -> tuple[UUID, UUID] | None: ...


class LessonRepository(BasicInfoProtocol[Lesson, LessonBasicInfo]):
    """
    Контракт репозитория уроков.

    Наследует полный CRUD и `get_by_id_basic_info` от `BasicInfoProtocol`
    без переопределения — сигнатуры совместимы. Добавляет операции,
    специфичные только для уроков: работу с блоками контента
    (`get_content_blocks_by_id`, `replace_content_block`) и привязку
    списка уроков к модулю (`assign_module`).
    """

    async def create_at(self, lesson: Lesson) -> Lesson: ...

    async def delete_and_compact(self, lesson_id: UUID) -> None: ...

    async def get_content_blocks_by_id(self, lesson_id: UUID) -> list[AnyContentBlock] | None:
        """Получает контент-блоки урока для отображения или редактирования."""

    async def replace_content_block(
        self,
        lesson_id: UUID,
        block_index: int,
        new_block: dict[str, Any],
    ) -> None:
        """Заменяет контент-блок урока, чтобы сохранить результат редактирования."""

    async def assign_module(self, lesson_id: UUID, module_id: UUID) -> None:
        """Привязывает один урок к модулю и фиксирует его принадлежность."""

    async def read_course_id(self, lesson_id: UUID) -> UUID | None: ...


class ModuleRepository(BasicInfoProtocol[Module, ModuleBasicInfo]):
    """
    Контракт репозитория модулей.

    Наследует полный CRUD и `get_by_id_basic_info` от `BasicInfoProtocol`
    без переопределения. Добавляет привязку модулей к курсу
    (`assign_course`) и выборку "базовой информации" по урокам,
    принадлежащим модулю (`select_lessons_by_id_module`).
    """

    async def create_at(self, module: Module) -> Module: ...

    async def delete_and_compact(self, module_id: UUID) -> None: ...

    async def assign_course(self, module_id: UUID, course_id: UUID) -> None:
        """Привязывает модуль к курсу и сохраняет структуру курса."""

    async def select_lessons_by_id_module(self, module_id: UUID) -> list[BasicInfo]:
        """Выбирает краткие данные уроков, входящих в указанный модуль."""
        ...

    async def read_course_id(self, module_id: UUID) -> UUID | None: ...


class CourseRepository(BasicInfoProtocol[Course, CourseBasicInfo]):
    """
    Контракт репозитория курсов.

    Наследует полный CRUD и `get_by_id_basic_info` от `BasicInfoProtocol`
    без переопределения. Добавляет единственный специфичный метод —
    выборку "базовой информации" по модулям, принадлежащим курсу
    (`select_modules_by_id_course`).
    """

    async def find(
        self,
        pagination: Pagination,
    ) -> Page[Course]: ...

    async def find_member_courses(
        self,
        user_id: UUID,
        pagination: Pagination,
    ) -> Page[Course]: ...
    async def select_modules_by_id_course(self, course_id: UUID) -> list[BasicInfo]:
        """Выбирает краткие данные модулей, входящих в указанный курс."""
        ...

    async def find_members(
        self,
        user_id: UUID,
        pagination: Pagination,
    ) -> Page[Course]: ...

    async def read_creator_id(self, course_id: UUID) -> UUID | None: ...


class DocumentRepository(Repository[Document]):
    """
    Контракт репозитория документов (TOC / HEADING / TEXT).

    Наследует полный CRUD от `RepositoryProtocol` без переопределения
    сигнатур — совместимость по Лисков сохранена. Добавляет три метода
    для навигации по иерархии документа: `get_tocs` (оглавления владельца),
    `get_headings` (заголовки внутри оглавления) и `get_texts`
    (текстовое содержимое под заголовком).
    """

    async def get_tocs(self, owner_id: UUID) -> list[Document]:
        """Получает оглавления документов владельца для навигации по материалам."""
        ...

    async def get_headings(self, toc_id: UUID) -> list[Document]:
        """Получает заголовки внутри оглавления, чтобы раскрыть структуру документа."""
        ...

    async def get_texts(self, heading_id: UUID) -> Document | None:
        """Получает текстовый раздел документа по выбранному заголовку."""


class ChatRepository(Repository[Chat]):
    """
    Контракт репозитория чатов.

    ⚠️ Внимание, нарушение совместимости по Лисков: класс наследует
    `RepositoryProtocol[Chat]`, но переопределяет `read` и `update`
    несовместимыми сигнатурами — вместо одиночного `uid` требуется
    составной ключ (`user_id`, `course_id`, `chat_id`), потому что
    записи чата не идентифицируются одним UUID.

    Практическое следствие: любой код, типизированный через
    `RepositoryProtocol[Chat]` (например, обобщённая CRUD-функция),
    формально пройдёт статическую проверку типов при передаче объекта
    `ChatRepositoryProtocol`, но упадёт в рантайме при вызове
    `read(uid)` или `update(uid, **kwargs)`, поскольку реальная
    реализация ожидает три обязательных позиционных аргумента, а не один.

    Если потребуется устранить это нарушение, варианты:
      1) не наследовать `RepositoryProtocol` и продублировать методы,
         не требующие составного ключа (create/paginate/upsert/delete/
         exists/get_by_ids), явно;
      2) переименовать `read`/`update` в `read_by_keys`/`update_by_keys`
         и оставить унаследованные `read`/`update` с сигнатурой по uid
         нетронутыми.
    """

    async def read(self, user_id: UUID, course_id: UUID, chat_id: UUID) -> Chat | None:
        """Получает чат по составному ключу пользователя, курса и диалога."""

    async def update(
        self,
        chat_id: UUID,
        user_id: UUID,
        course_id: UUID,
        **kwargs: Any,
    ) -> Chat | None:
        """Обновляет чат пользователя внутри курса и возвращает актуальное состояние."""


class PracticeRepository(Repository[Practice]):
    """
    Контракт репозитория практик.

    ⚠️ Внимание, то же нарушение совместимости по Лисков, что и в
    `ChatRepositoryProtocol`: класс наследует `RepositoryProtocol[Practice]`,
    но переопределяет `read` и `update` составным ключом
    (`user_id`, `module_id`, `lesson_id`) вместо одиночного `uid`.
    Практика идентифицируется комбинацией пользователя, модуля и урока,
    а не отдельным UUID-идентификатором записи.

    Последствия и варианты устранения — см. докстринг
    `ChatRepositoryProtocol`, ситуация полностью аналогична.
    """

    async def read(self, user_id: UUID, module_id: UUID, lesson_id: UUID) -> Practice | None:
        """Получает практику по составному ключу пользователя, модуля и урока."""

    async def read_by_module(self, user_id: UUID, module_id: UUID) -> list[dict[str, Any]]:
        """Получает практики пользователя внутри модуля без служебных полей."""
        ...


class ProgressRepository[ProgressT: Entity](Repository[ProgressT]):
    async def get_by_user(self, user_id: UUID, resource_id: UUID) -> ProgressT | None: ...

    async def exist_by_user(self, user_id: UUID, resource_id: UUID) -> bool: ...


class LessonProgressRepository(ProgressRepository[LessonProgress]):
    async def update_from_event(self, event: LessonProgressUpdated) -> None: ...


class ModuleProgressRepository(ProgressRepository[ModuleProgress]): ...


class CourseProgressRepository(ProgressRepository[CourseProgress]):
    async def count_completed_lessons(self, course_progress_id: UUID) -> int: ...

    async def find_by_course(
        self, course_id: UUID, pagination: Pagination
    ) -> Page[CourseProgress]: ...


class MemberRepository(Repository[Member]):
    async def read(self, user_id: UUID, course_id: UUID) -> Member | None: ...

    async def exists(self, user_id: UUID, course_id: UUID) -> bool: ...

    async def read_role(self, user_id: UUID, course_id: UUID) -> MemberRole | None: ...


class InvitationRepository(Repository[Invitation]):
    async def get_by_token(self, token: str) -> Invitation | None: ...

    async def find_by_course(
        self,
        course_id: UUID,
        pagination: Pagination,
    ) -> Page[Invitation]: ...

    async def get_active(
        self,
        email: Email,
        course_id: UUID,
    ) -> Invitation | None: ...


class VectorRepository(Protocol):
    async def create(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
        document_id: str | None = None,
    ) -> None: ...

    async def read(
        self,
        query: str,
        limit: int = 5,
        prefetch_limit: int = 25,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[str]: ...


class IAMRepository(Protocol):
    async def get_user_by_email(
        self,
        email: str,
    ) -> UserResponse | None: ...

    async def invite_user_in_system(
        self,
        dto: IAMInvitationCreate,
    ) -> IAMInvitation | None: ...

    async def get_user_membership(
        self,
        organization_id: UUID,
        user_id: UUID,
    ) -> Membership | None: ...


class OrganizationRepository(Protocol):
    async def __call__(
        self,
        client: SrvCourseClient,
        dto: OrganizationInvitationCreate,
    ) -> OrganizationInvitation | None: ...
