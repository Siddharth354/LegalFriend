import json

from src.core.config import settings

RAW_TEXT = settings.chunks_dir.parent / "raw" / "usurious_loans_act_1918.txt"
OUT_PATH = settings.chunks_dir / "usurious_loans_act_1918_chunks.json"
ACT = "Usurious Loans Act, 1918"
ENACTMENT_DATE = "1918-03-22"


def build_chunks() -> list[dict[str, object]]:
    full_text: str = RAW_TEXT.read_text(encoding="utf-8")
    section_three_start: int = full_text.index("3. Re-opening")
    scope_and_definitions: str = full_text[:section_three_start].strip()
    section_three: str = full_text[section_three_start:].strip()
    return [
        {
            "chunk_id": "usurious_loans_act_1918_s1_2",
            "act": ACT,
            "enactment_date": ENACTMENT_DATE,
            "section": "Sections 1-2",
            "subsection": None,
            "citation_string": "Sections 1-2, Usurious Loans Act, 1918",
            "content": scope_and_definitions,
        },
        {
            "chunk_id": "usurious_loans_act_1918_s3",
            "act": ACT,
            "enactment_date": ENACTMENT_DATE,
            "section": "Section 3",
            "subsection": None,
            "citation_string": "Section 3, Usurious Loans Act, 1918",
            "content": section_three,
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
