import json

from src.core.config import settings

RAW_TEXT = settings.chunks_dir.parent / "raw" / "rbi_recovery_agents_2022.txt"
OUT_PATH = settings.chunks_dir / "rbi_recovery_agents_2022_chunks.json"
ACT = "RBI Recovery Agents Circular, 2022"
ENACTMENT_DATE = "2022-08-12"


def build_chunks() -> list[dict[str, object]]:
    full_text: str = RAW_TEXT.read_text(encoding="utf-8")
    paragraph_two_start: int = full_text.index("2. In view")
    paragraph_five_start: int = full_text.index("5. This circular")
    paragraph_two: str = full_text[paragraph_two_start:paragraph_five_start].strip()
    applicability: str = full_text[paragraph_five_start:].strip()
    return [
        {
            "chunk_id": "rbi_recovery_agents_2022_p2",
            "act": ACT,
            "enactment_date": ENACTMENT_DATE,
            "section": "Paragraph 2",
            "subsection": None,
            "citation_string": "Paragraph 2, RBI/2022-23/108 (Recovery Agents)",
            "content": paragraph_two,
        },
        {
            "chunk_id": "rbi_recovery_agents_2022_p5_6",
            "act": ACT,
            "enactment_date": ENACTMENT_DATE,
            "section": "Paragraphs 5-6",
            "subsection": None,
            "citation_string": "Paragraphs 5-6, RBI/2022-23/108 (Applicability)",
            "content": applicability,
        },
    ]


def main() -> None:
    chunks: list[dict[str, object]] = build_chunks()
    settings.chunks_dir.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(chunks, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"wrote {len(chunks)} chunks to {OUT_PATH}")


if __name__ == "__main__":
    main()
