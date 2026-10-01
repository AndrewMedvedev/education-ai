from enum import StrEnum


class UploadStatus(StrEnum):
    PENDING = "pending"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
