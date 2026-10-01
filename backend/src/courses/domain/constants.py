from .vo import (
    AnyContentBlock,
    ChemicalBlock,
    CodeBlock,
    ExtendedContentType,
    # ImageBlock,
    MathBlock,
    MermaidBlock,
    MusicalBlock,
    QuizBlock,
    TextBlock,
    VideoBlock,
)

INVITATION_EXPIRES_IN_DAYS = 7

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
