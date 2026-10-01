# Временной промежуток после которого истекает подписанный URL (30 минут)
PRESIGNED_URL_EXPIRES_IN = 1800
# Максимальная длина для имени файла
MAX_FILENAME_LENGTH = 255
# Разрешённые типы владельцев файлов (те к кому можно прикрепить вложение)
# Mime типы для документов (не включать application/octet-stream - не безопасно)
DOCUMENT_MIME_TYPES = {
    # PDF
    "application/pdf",
    # Microsoft Office
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-outlook",
    # LibreOffice
    "application/vnd.oasis.opendocument.text",
    "application/vnd.oasis.opendocument.spreadsheet",
    "application/vnd.oasis.opendocument.presentation",
    # Тестовые файлы
    "text/plain",
    "text/csv",
    "application/rtf",
    "text/html",
    "text/markdown",
    # JSON/XML файлы
    "application/json",
    "application/xml",
    "text/xml",
}
