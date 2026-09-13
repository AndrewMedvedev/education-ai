from .entities import (
    AnyContentBlock,
    ChemicalBlock,
    CodeBlock,
    # ImageBlock,
    MathBlock,
    MermaidBlock,
    MusicalBlock,
    QuizBlock,
    TextBlock,
    VideoBlock,
)
from .vo import ExtendedContentType

_BLOCK_REGISTRY: dict[str, type[AnyContentBlock]] = {
    ExtendedContentType.TEXT: TextBlock,
    # ExtendedContentType.IMAGE: ImageBlock,
    ExtendedContentType.VIDEO: VideoBlock,
    ExtendedContentType.PROGRAM_CODE: CodeBlock,
    ExtendedContentType.QUIZ: QuizBlock,
    ExtendedContentType.MERMAID: MermaidBlock,
    ExtendedContentType.MATH_FORMULA: MathBlock,
    ExtendedContentType.CHEMICAL_FORMULA: ChemicalBlock,
    ExtendedContentType.MUSICAL_NOTATION: MusicalBlock,
}
