from typing import Protocol

import language_tool_python
from pydantic import BaseModel, Field, NonNegativeInt

MIN_TEXT_LENGTH = 3


class TextIssue(BaseModel):
    """Проблема с текстом (исправление)"""

    category: str = Field(..., description="Категория ошибки")
    original: str = Field(..., description="Оригинальный текст (там где допущена ошибка)")
    suggestion: str = Field(..., description="Предложение по исправлению")
    start: NonNegativeInt = Field(..., description="Где начинается ошибка (индекс)")
    end: NonNegativeInt = Field(..., description="Где заканчивается ошибка (индекс)")
    message: str = Field(..., description="Пояснение ошибки")


class TextCheckResult(BaseModel):
    """Результат проверки текста"""

    original_text: str = Field(..., description="Оригинальный текст")
    corrected_text: str = Field(..., description="Исправленный текст")
    has_issues: bool = Field(..., description="Есть ли замечания и исправления по тексту")
    suggestions: list[TextIssue] = Field(default_factory=list, description="Список исправлений")


class SpellChecker(Protocol):

    def check(self, text: str) -> TextCheckResult:
        """Проверка орфографии и пунктуации в тексте"""


class LanguageToolSpellChecker:
    def __init__(self, language: str, remote_server: str) -> None:
        self.tool = language_tool_python.LanguageTool(
            language=language, remote_server=remote_server
        )

    def check(self, text: str) -> TextCheckResult:

        # 1. Текст слишком короткий
        if not text.strip() or len(text.strip()) < MIN_TEXT_LENGTH:
            return TextCheckResult(
                original_text=text, corrected_text=text, has_issues=False, suggestions=[]
            )

        # 2. Получение ошибок
        matches = self.tool.check(text)

        # 3. Формирование списка исправлений
        suggestions: list[TextIssue] = []
        corrected_text = text

        for match in matches:
            issue = TextIssue(
                category=match.category,
                original=match.context[match.offset: match.offset + match.error_length],
                suggestion=match.replacements[0] if match.replacements else "",
                start=match.offset,
                end=match.offset + match.error_length,
                message=match.message,
            )
            suggestions.append(issue)

            # 4. Исправление ошибок в тексте
            if match.replacements:
                corrected_text = (
                    corrected_text[: match.offset]
                    + match.replacements[0]
                    + corrected_text[match.offset + match.error_length:]
                )

        return TextCheckResult(
            original_text=text,
            corrected_text=corrected_text,
            has_issues=len(suggestions) > 0,
            suggestions=suggestions,
        )
