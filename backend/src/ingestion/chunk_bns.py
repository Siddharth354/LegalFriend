import json
import re

from src.core.config import settings
from src.ingestion.pdf_text import extract_full_text

RAW_PDF = settings.chunks_dir.parent / "raw" / "bns_2023.pdf"
OUT_PATH = settings.chunks_dir / "bns_2023_chunks.json"
ENACTMENT_DATE = "2023-12-25"

TARGET_SECTIONS = [111, 308, 318, 319, 335, 336, 338, 356]

SUBCLAUSE_RE = re.compile(r"(?:^|—)\((\d{1,2})\)\s", re.MULTILINE)
FALLBACK_CHUNK_CHARS = 1200


def find_section_body(full_text: str, section_number: int) -> str | None:
    pattern = re.compile(rf"\n{section_number}\.\s+[^\n]*?\.—", re.DOTALL)
    matches = list(pattern.finditer(full_text))
    if not matches:
        return None
    start = matches[0].start()
    next_pattern = re.compile(rf"\n{section_number + 1}\.\s+")
    next_match = next_pattern.search(full_text, matches[0].end())
    end = next_match.start() if next_match else start + 6000
    return full_text[start:end].strip()


def split_subclauses(body: str) -> list[tuple[str, str]]:
    positions = [(m.start(), m.group(1)) for m in SUBCLAUSE_RE.finditer(body)]
    if not positions:
        return []
    chunks = []
    for i, (pos, num) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(body)
        text = body[pos:end].strip().lstrip("—").strip()
        chunks.append((num, text))
    return chunks


def paragraph_fallback_split(body: str) -> list[tuple[str, str]]:
    units = [u.strip() for u in re.split(r"\n\s*\n", body) if u.strip()]
    if len(units) <= 1:
        units = [s.strip() for s in re.split(r"(?<=[.;])\s+", body) if s.strip()]

    chunks: list[tuple[str, str]] = []
    buffer = ""
    part = 1
    for unit in units:
        if buffer and len(buffer) + len(unit) > FALLBACK_CHUNK_CHARS:
            chunks.append((f"part{part}", buffer.strip()))
            part += 1
            buffer = ""
        buffer += " " + unit
    if buffer.strip():
        chunks.append((f"part{part}", buffer.strip()))
    return chunks


def build_chunks() -> list[dict]:
    full_text = extract_full_text(RAW_PDF)
    chunks: list[dict] = []

    for section_number in TARGET_SECTIONS:
        body = find_section_body(full_text, section_number)
        if body is None:
            continue

        subclauses = split_subclauses(body)
        if not subclauses and len(body) > FALLBACK_CHUNK_CHARS:
            subclauses = paragraph_fallback_split(body)

        if not subclauses:
            chunks.append(
                {
                    "chunk_id": f"bns_2023_s{section_number}",
                    "act": "Bharatiya Nyaya Sanhita, 2023",
                    "enactment_date": ENACTMENT_DATE,
                    "section": str(section_number),
                    "subsection": None,
                    "citation_string": f"Section {section_number}, BNS 2023",
                    "content": body,
                }
            )
            continue

        for subsection, text in subclauses:
            if len(text) <= FALLBACK_CHUNK_CHARS:
                chunks.append(
                    {
                        "chunk_id": f"bns_2023_s{section_number}_{subsection}",
                        "act": "Bharatiya Nyaya Sanhita, 2023",
                        "enactment_date": ENACTMENT_DATE,
                        "section": str(section_number),
                        "subsection": subsection,
                        "citation_string": f"Section {section_number}({subsection}), BNS 2023",
                        "content": text,
                    }
                )
                continue

            for part_label, part_text in paragraph_fallback_split(text):
                chunks.append(
                    {
                        "chunk_id": f"bns_2023_s{section_number}_{subsection}_{part_label}",
                        "act": "Bharatiya Nyaya Sanhita, 2023",
                        "enactment_date": ENACTMENT_DATE,
                        "section": str(section_number),
                        "subsection": subsection,
                        "citation_string": f"Section {section_number}({subsection}), BNS 2023",
                        "content": part_text,
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
