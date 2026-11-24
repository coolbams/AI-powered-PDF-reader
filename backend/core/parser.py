"""
parser.py
Extracts text from a PDF using pymupdf4llm, writing all outputs to the staging
directory on disk (never held long in memory). Explicitly closes the PyMuPDF
document handle to immediately reclaim C-heap memory (~200–350 MB for large PDFs).
"""

import fitz  # PyMuPDF
import json
import logging
import pymupdf4llm
from pathlib import Path

from .chunker import chunk_pages
from .embeddings import embed
from .staging_manager import StagingContext, update_state

logger = logging.getLogger(__name__)


def parse_pdf(ctx: StagingContext) -> int:
    """
    Parses the PDF at ctx.pdf_path, writes extracts to the staging directory,
    embeds chunks into ChromaDB, and returns the page count.

    Memory Strategy:
    - pymupdf4llm produces one page dict at a time.
    - The PyMuPDF document handle is explicitly closed immediately after extraction
      to free the C-heap allocations (~200–350 MB for a 400-page PDF).
    - Markdown, JSON pages, and chunk JSON are written to disk immediately,
      leaving only small working sets in RAM during each stage.
    """
    stem = Path(ctx.filename).stem

    # --- Step A: Extract text ---
    logger.info("[Parser] Extracting text from '%s'...", ctx.filename)
    doc = fitz.open(str(ctx.pdf_path))
    try:
        pages = pymupdf4llm.to_markdown(doc, page_chunks=True)
    finally:
        doc.close()  # Immediately release C-heap memory (~200–350 MB)
        logger.info("[Parser] PyMuPDF document closed, C-heap released.")

    page_count = len(pages)
    logger.info("[Parser] Extracted %d pages from '%s'", page_count, ctx.filename)

    # --- Step B: Write Markdown to staging disk ---
    markdown_text = "\n\n".join(p["text"] for p in pages)
    ctx.md_path.write_text(markdown_text, encoding="utf-8")
    logger.info("[Parser] Markdown written to staging: %s", ctx.md_path.name)

    # --- Step C: Write per-page JSON to staging disk ---
    pages_metadata = [
        {"page_number": p["metadata"]["page_number"], "text": p["text"]}
        for p in pages
    ]
    ctx.pages_path.write_text(
        json.dumps(pages_metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("[Parser] Pages JSON written to staging: %s", ctx.pages_path.name)

    # --- Step D: Chunk pages and write chunks JSON to staging disk ---
    chunks_results = chunk_pages(pages, stem)
    chunks_data = [
        {"text": c.page_content, "metadata": c.metadata}
        for c in chunks_results
    ]
    ctx.chunks_path.write_text(
        json.dumps(chunks_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info(
        "[Parser] %d chunks written to staging: %s",
        len(chunks_data),
        ctx.chunks_path.name,
    )

    # --- Step E: Embed chunks into ChromaDB (from memory, not re-read from disk) ---
    logger.info("[Parser] Embedding %d chunks into ChromaDB...", len(chunks_data))
    embed(chunks_data, stem)
    logger.info("[Parser] ChromaDB embedding complete for '%s'", ctx.filename)

    # --- Step F: Update staging state ---
    update_state(ctx, {"page_count": page_count, "status": "parsed"})

    return page_count
