import logging
from pathlib import Path

from src.utils import convert_document_to_md

logging.basicConfig(level=logging.DEBUG)

file_path = Path(
    r"C:\Users\andre\TyuiuProjects\education-ai\telegram-bot\docs\Tekhnicheskoe_zadanie_II_agent.docx"
)

text = convert_document_to_md(file_path)

print(text)

Path("output.md").write_text(text, encoding="utf-8")
