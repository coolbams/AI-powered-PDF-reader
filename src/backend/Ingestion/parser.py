from pathlib import Path
import pymupdf4llm
import json

from .chunker import chunk_pages
from .embeddings import embed


BASE_DIR = Path(__file__).resolve().parent.parent

def parse_pdf(file_path: str | Path) -> dict[str, Path]:
    file_path = Path(file_path)
    extracts_dir = BASE_DIR / "Media" / "Extracts"
    extracts_dir.mkdir(parents=True, exist_ok=True)
        
    pages = pymupdf4llm.to_markdown(str(file_path), page_chunks=True)

    chunks_results = chunk_pages(pages)
    
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

    chunks_path = extracts_dir / f"{file_path.stem}_chunks.json"
    data = [
        {"text": c.page_content, "metadata": c.metadata}
        for c in chunks_results
    ]

    chunks_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    embed(str(chunks_path), file_path.stem)

    return {"markdown": markdown_path, "metadata": metadata_path, "chunks": chunks_path}

