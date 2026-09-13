from .domain.entities import Attachment
from .schemas import AttachmentResponse


def map_attachment_to_response(attachment: Attachment) -> AttachmentResponse:
    """
    Преобразование доменной модели к API схеме ответа
    (с получением preview URL для изображений).
    """

    return AttachmentResponse(
        id=attachment.id,
        original_filename=attachment.original_filename,
        mime_type=attachment.mime_type,
        size_bytes=attachment.size_bytes,
        storage_key=attachment.storage_key,
        owner_id=attachment.owner_id,
        uploaded_at=attachment.uploaded_at,
        uploaded_by=attachment.uploaded_by,
    )
