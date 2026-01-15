from typing import Any

import logging
import time
from collections.abc import Iterable, Mapping
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
METADATA_FIELD = "metadata"
TOP_K = 10

es_client = Elasticsearch(hosts=[settings.elasticsearch.url])

embeddings = HuggingFaceEmbeddings(
    model_name="deepvk/USER-bge-m3",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": False}
)


def _create_index_if_not_exists(index_name: str) -> None:
    if es_client.indices.exists(index=index_name):
        return
    es_client.indices.create(
        index=index_name,
        mappings={
            "properties": {
                TEXT_FIELD: {"type": "text"},
                DENSE_VECTOR_FIELD: {"type": "dense_vector"},
                METADATA_FIELD: {"type": "object"},
            }
        }
    )


def _index_data(
        index_name: str,
        texts: Iterable[str],
        metadata: dict[str, Any],
        refresh: bool = True,
) -> None:
    _create_index_if_not_exists(index_name)
    vectors = embeddings.embed_documents(list(texts))
    requests = [
        {
            "_op_type": "index",
            "_index": index_name,
            "_id": i,
            TEXT_FIELD: text,
            DENSE_VECTOR_FIELD: vector,
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
    return Document(
        page_content=hit["_source"][TEXT_FIELD], metadata=hit["_source"][METADATA_FIELD]
    )


async def index_attachments(teacher_id: int, attachment_ids: list[UUID]) -> None:
    index_name = f"education-materials:{teacher_id}"
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
        md_text = convert_document_to_md(attachment.filepath)
        logger.info(
            "File %s loaded and converted to Markdown, characters length: %s",
            attachment.original_filename, len(md_text)
        )
        chunks = splitter.split_text(md_text)
        logger.info("Addition %s chunks to %s", len(chunks), index_name)
        _index_data(
            index_name=index_name,
            texts=chunks,
            metadata={
                "attachment_id": attachment.id,
                "original_filename": attachment.original_filename,
            },
        )
        execution_time = time.time() - start_time
        logger.info(
            "Successfully processed `%s` file, processing duration - %s seconds",
            attachment.id, execution_time
        )


def _enrich_document_content(document: Document) -> str:
    return f"""**Attachment-ID:** {document.metadata.get("attachment_id")}
    **Filename:** {document.metadata.get("original_filename")}
    **Page content:**
    {document.page_content}
    """


async def retrieve_education_materials(teacher_id: int, query: str, top_k: int = 10) -> list[str]:
    index_name = f"education-materials:{teacher_id}"
    hybrid_retriever = ElasticsearchRetriever(
        index_name=index_name,
        body_func=_hybrid_query,
        document_mapper=_document_mapper,
        es_url=settings.elasticsearch.url
    )
    documents = await hybrid_retriever.ainvoke(query, k=top_k)
    return [_enrich_document_content(document) for document in documents]
