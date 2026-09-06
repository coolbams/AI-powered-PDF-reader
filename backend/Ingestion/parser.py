from pathlib import Path
import pymupdf4llm
import json

BASE_DIR = Path(__file__).resolve().parent.parent

def _parse_pdf(file_path):
    file_path = Path(file_path)
    extracts_dir = BASE_DIR / "Media" / "Extracts"
    extracts_dir.mkdir(parents=True, exist_ok=True)

    pages = pymupdf4llm.to_markdown(str(file_path), page_chunks=True)
    
    markdown_path = extracts_dir / f"{file_path.stem}.md"
    markdown_path.write_text("\n\n".join(p["text"] for p in pages), encoding="utf-8")

    metadata_path = extracts_dir / f"{file_path.stem}.json"
    metadata_path.write_text(
        json.dumps(
            [{"page_number": p["metadata"]["page_number"], "text": p["text"]} for p in pages],
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return {"markdown": markdown_path, "metadata": metadata_path}

