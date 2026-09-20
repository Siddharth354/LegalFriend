from pathlib import Path

import pypdf


def extract_pages(pdf_path: Path) -> list[str]:
    reader = pypdf.PdfReader(str(pdf_path))
    return [page.extract_text() for page in reader.pages]


def extract_full_text(pdf_path: Path) -> str:
    return "\n".join(extract_pages(pdf_path))
