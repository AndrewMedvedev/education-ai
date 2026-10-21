from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from langchain_core.documents import Document

from src.courses.application.services.document import DocumentService
from src.courses.domain.enums import DocumentNodeType


@pytest.fixture
def repository():
    """Создаёт мок репозитория документов."""
    return AsyncMock()


@pytest.fixture
def session():
    """Создаёт мок сессии базы данных."""
    return AsyncMock()


@pytest.fixture
def service(repository, session):
    """Создаёт сервис документов с изолированными зависимостями."""
    return DocumentService(repo=repository, session=session)


class TestDocumentService:
    @pytest.mark.asyncio
    async def test_save_document_creates_root_and_text_without_headings(
        self,
        service,
        repository,
        session,
        monkeypatch,
    ):
        """Сохраняет корневой узел и текст, если в документе нет заголовков."""
        user_id = uuid4()
        repository.create.side_effect = lambda document: document
        monkeypatch.setattr(
            "src.courses.application.services.document.get_heading_chain",
            lambda *_: [],
        )
        monkeypatch.setattr(
            "src.courses.application.services.document.is_heading_only",
            lambda _: False,
        )

        await service.save_document([Document(page_content="Document text")], "guide.md", user_id)

        root, text = [call.args[0] for call in repository.create.await_args_list]
        assert root.owner_id == user_id
        assert root.node_type == DocumentNodeType.TOC
        assert root.title == "guide.md"
        assert text.node_type == DocumentNodeType.TEXT
        assert text.parent_node_id == root.id
        assert text.content == "Document text"
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_save_document_reuses_heading_nodes(
        self,
        service,
        repository,
        session,
        monkeypatch,
    ):
        """Не создаёт повторно узлы одинаковой цепочки заголовков."""
        repository.create.side_effect = lambda document: document
        monkeypatch.setattr(
            "src.courses.application.services.document.get_heading_chain",
            lambda *_: ["Chapter", "Section"],
        )
        monkeypatch.setattr(
            "src.courses.application.services.document.is_heading_only",
            lambda _: False,
        )

        await service.save_document(
            [Document(page_content="First"), Document(page_content="Second")],
            "guide.md",
            uuid4(),
        )

        created_documents = [call.args[0] for call in repository.create.await_args_list]
        assert [document.node_type for document in created_documents] == [
            DocumentNodeType.TOC,
            DocumentNodeType.HEADING,
            DocumentNodeType.TEXT,
            DocumentNodeType.TEXT,
        ]
        assert [document.content for document in created_documents[-2:]] == ["First", "Second"]
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_save_document_skips_heading_only_content(
        self,
        service,
        repository,
        session,
        monkeypatch,
    ):
        """Не сохраняет блок, состоящий только из заголовка."""
        monkeypatch.setattr(
            "src.courses.application.services.document.get_heading_chain",
            lambda *_: ["Chapter"],
        )
        monkeypatch.setattr(
            "src.courses.application.services.document.is_heading_only",
            lambda _: True,
        )

        await service.save_document([Document(page_content="# Chapter")], "guide.md", uuid4())

        repository.create.assert_not_awaited()
        session.commit.assert_awaited_once()
