import base64


def image_to_uri(image_content: bytes, mime_type: str = "image/png") -> str:
    """
    Преобразование изображения к URI адресу.
    Для передачи по HTTP.
    """

    encoded = base64.b64encode(image_content).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"
