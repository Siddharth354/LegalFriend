import json
import re

from src.core.config import settings
from src.ingestion.pdf_text import extract_full_text

RAW_PDF = settings.chunks_dir.parent / "raw" / "rbi_digital_lending_directions_2025.pdf"
OUT_PATH = settings.chunks_dir / "rbi_digital_lending_directions_2025_chunks.json"
ENACTMENT_DATE = "2025-05-08"

TARGET_PARAGRAPHS = [4, 5, 8, 9, 10, 12, 17]
FALLBACK_CHUNK_CHARS = 1200


def find_paragraph_body(full_text: str, para_number: int) -> str | None:
    pattern = re.compile(rf"\n{para_number}\.\s+[A-Z]")
    matches = list(pattern.finditer(full_text))
    if len(matches) < 2:
        return None
    start = matches[-1].start()
    next_pattern = re.compile(rf"\n{para_number + 1}\.\s+[A-Z]")
    next_match = next_pattern.search(full_text, start + 1)
    end = next_match.start() if next_match else start + 6000
    return full_text[start:end].strip()


def split_roman_sub_items(body: str) -> list[tuple[str, str]]:
    positions = [
        (m.start(), m.group(1))
        for m in re.finditer(r"\n(i{1,3}v?|vi{0,3}|ix|x)\.\s+", body)
    ]
    if not positions:
        return []
    chunks = []
    for idx, (pos, label) in enumerate(positions):
        end = positions[idx + 1][0] if idx + 1 < len(positions) else len(body)
        chunks.append((label, body[pos:end].strip()))
    return chunks


def build_chunks() -> list[dict]:
    full_text = extract_full_text(RAW_PDF)
    chunks: list[dict] = []

    for para_number in TARGET_PARAGRAPHS:
        body = find_paragraph_body(full_text, para_number)
        if body is None:
            continue

        sub_items = split_roman_sub_items(body)
        if not sub_items or len(body) <= FALLBACK_CHUNK_CHARS:
            chunks.append(
                {
                    "chunk_id": f"rbi_dld_2025_p{para_number}",
                    "act": "Reserve Bank of India (Digital Lending) Directions, 2025",
                    "enactment_date": ENACTMENT_DATE,
                    "section": f"Para {para_number}",
                    "subsection": None,
                    "citation_string": f"Para {para_number}, RBI (Digital Lending) Directions, 2025",
                    "content": body,
                }
            )
            continue

        for label, text in sub_items:
            chunks.append(
                {
                    "chunk_id": f"rbi_dld_2025_p{para_number}_{label}",
                    "act": "Reserve Bank of India (Digital Lending) Directions, 2025",
                    "enactment_date": ENACTMENT_DATE,
                    "section": f"Para {para_number}",
                    "subsection": label,
                    "citation_string": f"Para {para_number}({label}), RBI (Digital Lending) Directions, 2025",
                    "content": text,
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
