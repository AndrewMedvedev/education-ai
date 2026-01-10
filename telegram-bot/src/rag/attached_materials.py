from typing import Any

import logging
import time
from collections.abc import Iterable, Mapping
from pathlib import Path
from uuid import UUID

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from langchain_core.documents import Document
from langchain_elasticsearch import ElasticsearchRetriever
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..core import schemas
from ..database import crud, models
from ..settings import settings
from ..utils import convert_document_to_md

logger = logging.getLogger(__name__)

TEXT_FIELD = "page_content"
DENSE_VECTOR_FIELD = "embedding"
NUM_CHARACTERS_FIELD = "num_characters"
METADATA_FIELD = "metadata"
TOP_K = 10

es_client = Elasticsearch(hosts=[settings.elasticsearch.url])

embeddings = HuggingFaceEmbeddings(
    model_name="deepvk/USER-bge-m3",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": False}
)


def _create_index_if_not_exists(
        index_name: str,
        text_field: str = TEXT_FIELD,
        dense_vector_field: str = DENSE_VECTOR_FIELD,
        num_characters_field: str = NUM_CHARACTERS_FIELD,
        metadata_field: str = METADATA_FIELD,
) -> None:
    if es_client.indices.exists(index=index_name):
        return
    es_client.indices.create(
        index=index_name,
        mappings={
            "properties": {
                text_field: {"type": "text"},
                dense_vector_field: {"type": "dense_vector"},
                num_characters_field: {"type": "integer"},
                metadata_field: {"type": "object"},
            }
        }
    )


def _index_data(
        index_name: str,
        text_field: str,
        dense_vector_field: str,
        num_characters_field: str,
        texts: Iterable[str],
        metadata: dict[str, Any],
        refresh: bool = True,
) -> None:
    _create_index_if_not_exists(
        index_name=index_name,
        text_field=text_field,
        dense_vector_field=dense_vector_field,
        num_characters_field=num_characters_field
    )
    vectors = embeddings.embed_documents(list(texts))
    requests = [
        {
            "_op_type": "index",
            "_index": index_name,
            "_id": i,
            text_field: text,
            dense_vector_field: vector,
            num_characters_field: len(text),
            METADATA_FIELD: metadata,
        }
        for i, (text, vector) in enumerate(zip(texts, vectors, strict=False))
    ]
    bulk(es_client, requests)
    if refresh:
        es_client.indices.refresh(index=index_name)


def _hybrid_query(search_query: str) -> dict[str, Any]:
    vector = embeddings.embed_query(search_query)
    return {
        "retriever": {
            "rrf": {
                "retrievers": [
                    {
                        "standard": {
                            "query": {"match": {TEXT_FIELD: search_query}}
                        }
                    },
                    {
                        "knn":
                            {
                                "field": DENSE_VECTOR_FIELD,
                                "query_vector": vector,
                                "k": 5,
                                "num_candidates": 10,
                             }
                    }
                ]
            }
        }
    }


def _document_mapper(hit: Mapping[str, Any]) -> Document:
    metadata = hit["_source"][METADATA_FIELD]
    num_characters = hit["_source"][NUM_CHARACTERS_FIELD]
    metadata[NUM_CHARACTERS_FIELD] = num_characters
    return Document(page_content=hit["_source"][TEXT_FIELD], metadata=metadata)


async def index_attachments(course_id: UUID, attachment_ids: list[UUID]) -> None:
    index_name = f"attached-materials-{course_id}"
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=50,
        length_function=len
    )
    for i, attachment_id in enumerate(attachment_ids):
        start_time = time.time()
        logger.info(
            "Start `%s` file processing %s/%s, start time - %s",
            attachment_id, i, len(attachment_ids), start_time
        )
        attachment = await crud.read(
            attachment_id, model_class=models.Attachment, schema_class=schemas.Attachment
        )
        if attachment is None:
            logger.warning("File %s not attached or was removed, skip this", attachment_id)
            continue
        md_text = convert_document_to_md(Path(attachment.filepath))
        logger.info(
            "File %s loaded and converted to Markdown, characters length: %s",
            attachment.original_filename, len(md_text)
        )
        chunks = splitter.split_text(md_text)
        logger.info("Addition %s chunks to %s", len(chunks), index_name)
        _index_data(
            index_name=index_name,
            text_field=TEXT_FIELD,
            dense_vector_field=DENSE_VECTOR_FIELD,
            num_characters_field=NUM_CHARACTERS_FIELD,
            texts=chunks,
            metadata={
                "course_id": course_id,
                "attachment_id": attachment.id,
                "original_filename": attachment.original_filename,
            },
        )
        execution_time = time.time() - start_time
        logger.info(
            "Successfully processed `%s` file, processing duration - %s seconds",
            attachment.id, execution_time
        )


async def search_materials(course_id: UUID, query: str, top_k: int = 10) -> list[str]:
    index_name = f"attached-materials-{course_id}"
    hybrid_retriever = ElasticsearchRetriever(
        index_name=index_name,
        body_func=_hybrid_query,
        document_mapper=_document_mapper,
        es_url=settings.elasticsearch.url
    )
    documents = await hybrid_retriever.ainvoke(query, k=top_k)
    return [
        f"""**Attachment-ID:** {document.metadata.get("attachment_id")}
        **Filename:** {document.metadata.get("original_filename")}
        **Num characters:** {document.metadata.get("num_characters")}
        **Content:**
        {document.page_content}
        """
        for document in documents
    ]
