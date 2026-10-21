from uuid import uuid4

import pytest

from src.courses.domain.enums import DocumentNodeType
from src.courses.infra.database.repos.document import SqlDocumentRepository
from src.courses.infra.models import DocumentOrm


@pytest.mark.asyncio
async def test_get_tocs_returns_only_document_roots_of_owner(session):
    """Возвращает только оглавления документов указанного пользователя."""
    owner_id = uuid4()
    toc = DocumentOrm(
        id=uuid4(),
        owner_id=owner_id,
        node_type=DocumentNodeType.TOC,
        title="Guide",
    )
    heading = DocumentOrm(
        id=uuid4(),
        owner_id=owner_id,
        parent_node_id=toc.id,
        node_type=DocumentNodeType.HEADING,
        title="Chapter",
    )
    other_owner_toc = DocumentOrm(
        id=uuid4(),
        owner_id=uuid4(),
        node_type=DocumentNodeType.TOC,
        title="Other guide",
    )
    session.add_all([toc, heading, other_owner_toc])
    await session.flush()
    repository = SqlDocumentRepository(session)

    documents = await repository.get_tocs(owner_id)

    assert [document.id for document in documents] == [toc.id]


@pytest.mark.asyncio
async def test_get_headings_returns_only_headings_of_owner_toc(session):
    """Возвращает заголовки только указанного оглавления владельца."""
    owner_id = uuid4()
    toc = DocumentOrm(
        id=uuid4(),
        owner_id=owner_id,
        node_type=DocumentNodeType.TOC,
        title="Guide",
    )
    heading = DocumentOrm(
        id=uuid4(),
        owner_id=owner_id,
        parent_node_id=toc.id,
        node_type=DocumentNodeType.HEADING,
        title="Chapter",
    )
    other_toc = DocumentOrm(
        id=uuid4(),
        owner_id=owner_id,
        node_type=DocumentNodeType.TOC,
        title="Other guide",
    )
    other_toc_heading = DocumentOrm(
        id=uuid4(),
        owner_id=owner_id,
        parent_node_id=other_toc.id,
        node_type=DocumentNodeType.HEADING,
        title="Other chapter",
    )
    other_owner_heading = DocumentOrm(
        id=uuid4(),
        owner_id=uuid4(),
        parent_node_id=toc.id,
        node_type=DocumentNodeType.HEADING,
        title="Private chapter",
    )
    session.add_all([toc, heading, other_toc, other_toc_heading, other_owner_heading])
    await session.flush()
    repository = SqlDocumentRepository(session)

    documents = await repository.get_headings(owner_id, toc.id)

    assert [document.id for document in documents] == [heading.id]


@pytest.mark.asyncio
async def test_get_text_returns_content_of_heading(session):
    """Возвращает текст, связанный с указанным заголовком документа."""
    owner_id = uuid4()
    heading_id = uuid4()
    heading = DocumentOrm(
        id=heading_id,
        owner_id=owner_id,
        node_type=DocumentNodeType.HEADING,
        title="Chapter",
    )
    text = DocumentOrm(
        id=uuid4(),
        owner_id=owner_id,
        parent_node_id=heading_id,
        node_type=DocumentNodeType.TEXT,
        content="Chapter content",
    )
    session.add_all([heading, text])
    await session.flush()
    repository = SqlDocumentRepository(session)

    document = await repository.get_text(owner_id, heading_id)

    assert document is not None
    assert document.content == "Chapter content"


@pytest.mark.asyncio
async def test_get_text_does_not_return_content_to_other_owner(session):
    """Не возвращает текст документа пользователю, который им не владеет."""
    owner_id = uuid4()
    heading = DocumentOrm(
        id=uuid4(),
        owner_id=owner_id,
        node_type=DocumentNodeType.HEADING,
        title="Chapter",
    )
    text = DocumentOrm(
        id=uuid4(),
        owner_id=owner_id,
        parent_node_id=heading.id,
        node_type=DocumentNodeType.TEXT,
        content="Private content",
    )
    session.add_all([heading, text])
    await session.flush()
    repository = SqlDocumentRepository(session)

    document = await repository.get_text(uuid4(), heading.id)

    assert document is None
