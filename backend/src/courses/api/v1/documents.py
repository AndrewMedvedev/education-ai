import logging
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from src.iam.application.policies import authorize
from src.iam.dependencies.identity import CurrentIdentity

from ...dependencies.services import DocumentServiceDep
from ...domain.permissions.courses import CREATE
from ...utils.docs_processing import (
    convert_document_to_md_async,
    document_pipeline,
    read_upload_with_limit,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".md", ".html", ".txt", ".json"}


@router.post(
    "/to/markdown",
    status_code=status.HTTP_200_OK,
    description="Принимает файл и возвращает его данные в формате markdown",
)
async def document_to_markdown(
    identity: CurrentIdentity,
    file: UploadFile = File(...),
) -> str:
    authorize(identity, CREATE)
    ext = Path(file.filename).suffix.lower()  # pyright: ignore[reportArgumentType]
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимое расширение файла: '{ext or 'не указано'}'. "
            f"Разрешены: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content = await read_upload_with_limit(file)

    if not content:
        raise HTTPException(status_code=400, detail="Файл пустой")

    return await convert_document_to_md_async(file=content, file_extension=ext)


@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
    description="Загружает файл в иерархическую таблицу пользователя",
)
async def upload_document(
    identity: CurrentIdentity,
    service: DocumentServiceDep,
    file: UploadFile = File(...),
) -> dict[str, str]:
    authorize(identity, CREATE)
    """Загружает document, чтобы сохранить пользовательский файл во внешнем хранилище."""
    ext = Path(file.filename).suffix.lower()  # pyright: ignore[reportArgumentType]
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимое расширение файла: '{ext or 'не указано'}'. "
            f"Разрешены: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content = await read_upload_with_limit(file)

    if not content:
        raise HTTPException(status_code=400, detail="Файл пустой")
    docs = await document_pipeline(file=content, file_extension=ext)
    await service.save_document(  # pyright: ignore[reportReturnType]
        docs=docs,
        user_id=identity.id,
        file_name=file.filename,  # pyright: ignore[reportArgumentType]
    )
    return {"message": "Файл загружен"}
