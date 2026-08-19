import argparse
import json
from datetime import datetime, UTC
from pathlib import Path

from pypdf import PdfReader


def convert_pdf_to_json(pdf_path: Path, source_dir: Path) -> dict:
    reader = PdfReader(str(pdf_path))
    pages = []
    full_text_parts = []
    for idx, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(
            {
                "page_number": idx,
                "text": text,
                "text_length": len(text),
            }
        )
        full_text_parts.append(text)

    return {
        "source": {
            "relative_path": str(pdf_path.relative_to(source_dir)),
            "filename": pdf_path.name,
            "size_bytes": pdf_path.stat().st_size,
            "modified_at": datetime.fromtimestamp(pdf_path.stat().st_mtime, UTC).isoformat(),
        },
        "document": {
            "page_count": len(reader.pages),
            "metadata": {k: str(v) for k, v in (reader.metadata or {}).items()},
            "full_text": "\n\n".join(full_text_parts),
        },
        "pages": pages,
        "extracted_at": datetime.now(UTC).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description="Convert all FIPI PDFs to JSON files.")
    parser.add_argument(
        "--source",
        default="fipi",
        help="Directory with PDF files",
    )
    parser.add_argument(
        "--output",
        default="data/fipi_json",
        help="Directory where JSON files will be written",
    )
    args = parser.parse_args()

    source_dir = Path(args.source).resolve()
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted([p for p in source_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"])
    if not pdf_files:
        raise SystemExit(f"No PDF files found in: {source_dir}")

    for i, pdf_path in enumerate(pdf_files, start=1):
        payload = convert_pdf_to_json(pdf_path, source_dir)
        output_path = output_dir / f"fipi_2026_{i:02d}.json"
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[{i}/{len(pdf_files)}] {pdf_path.name} -> {output_path.name}")

    print(f"Done. Converted {len(pdf_files)} file(s) to: {output_dir}")


if __name__ == "__main__":
    main()
