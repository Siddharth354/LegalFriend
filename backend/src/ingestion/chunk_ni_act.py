import json
import re

from src.core.config import settings
from src.ingestion.pdf_text import extract_full_text

RAW_PDF = settings.chunks_dir.parent / "raw" / "negotiable_instruments_act_1881.pdf"
OUT_PATH = settings.chunks_dir / "negotiable_instruments_act_1881_chunks.json"
ENACTMENT_DATE = "1881-12-09"

TARGET_SECTIONS = [138, 139, 140]


def find_section_body(full_text: str, section_number: int) -> str | None:
    pattern = re.compile(rf"\n{section_number}\.\s+[A-Z]")
    matches = list(pattern.finditer(full_text))
    if len(matches) < 2:
        return None
    start = matches[-1].start()
    next_pattern = re.compile(rf"\n{section_number + 1}\.\s+[A-Z]")
    next_match = next_pattern.search(full_text, start + 1)
    end = next_match.start() if next_match else start + 3000
    return full_text[start:end].strip()


def build_chunks() -> list[dict]:
    full_text = extract_full_text(RAW_PDF)
    chunks: list[dict] = []

    for section_number in TARGET_SECTIONS:
        body = find_section_body(full_text, section_number)
        if body is None:
            continue
        chunks.append(
            {
                "chunk_id": f"ni_act_1881_s{section_number}",
                "act": "Negotiable Instruments Act, 1881",
                "enactment_date": ENACTMENT_DATE,
                "section": str(section_number),
                "subsection": None,
                "citation_string": f"Section {section_number}, Negotiable Instruments Act, 1881",
                "content": body,
            }
        )

    return chunks


def main() -> None:
    chunks = build_chunks()
    settings.chunks_dir.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(chunks, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"wrote {len(chunks)} chunks to {OUT_PATH}")


if __name__ == "__main__":
    main()
