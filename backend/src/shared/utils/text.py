import re

from unidecode import unidecode


def get_latin_slug(ru_str: str, upper: bool = True) -> str:
    """
    Возвращает латинизированную версию российской строки.

    Пример: 'ПРОЕКТ' -> 'PROEKT'
    """

    latin = unidecode(ru_str)
    cleaned = re.sub(r"[^A-Za-z0-9]", "", latin)
    return cleaned.upper() if upper else cleaned
