"""
orchestrator.py
Coordinates the full upload & ingestion pipeline:
  1. Stream incoming file to Staging/<doc_id>/ scratch directory (not OS tempfile).
  2. Run PDF text extraction writing extracts to staging.
  3. Sync all staged files to Supabase Storage + PostgreSQL with retry on failure.
  4. Staging directory is only deleted once Supabase fully confirms receipt.
"""

import json
import logging
from pathlib import Path

from fastapi import HTTPException, UploadFile
from groq import APIConnectionError, AuthenticationError, RateLimitError

from .staging_manager import StagingContext, create_staging_area, update_state
from .supabase_sync import sync_to_supabase
from .parser import parse_pdf
from .retrieval import Retrieval
from .exceptions import EmptyCollectionError, DocumentNotFoundError
from .prompt_builder import build_prompt
from .generate import generate_response, stream_response
from .reranker import rerank

logger = logging.getLogger(__name__)
retrieval = Retrieval()

MAX_UPLOAD_SIZE = 50 * 1024 * 1024   # 50 MB
UPLOAD_READ_SIZE = 1 * 1024 * 1024   # 1 MB per read chunk


def validate(file: UploadFile) -> None:
    """Raises 400 if the uploaded file is not a PDF."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")


async def save(file: UploadFile) -> StagingContext:
    """
    Validates the upload, creates a staging area on disk, and streams the
    incoming PDF into Staging/<doc_id>/<filename> in bounded chunks.
    Returns the StagingContext. The staging directory is NOT deleted here —
    it persists until Supabase confirms receipt.
    """
    validate(file)
    safe_name = Path(file.filename).name
    ctx = create_staging_area(safe_name)

    try:
        size = 0
        with open(ctx.pdf_path, "wb") as out:
            while chunk := await file.read(min(UPLOAD_READ_SIZE, MAX_UPLOAD_SIZE - size + 1)):
                size += len(chunk)
                if size > MAX_UPLOAD_SIZE:
                    raise HTTPException(status_code=413, detail="File too large (max 50MB)")
                out.write(chunk)

        if size == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        update_state(ctx, {"file_size": size, "status": "saved"})
        logger.info("[Orchestrator] Streamed '%s' (%d bytes) to staging.", safe_name, size)
        return ctx

    except HTTPException:
        # Clean up staging dir on validation/size errors
        import shutil
        if ctx.dir.exists():
            shutil.rmtree(ctx.dir)
        raise


def process(ctx: StagingContext) -> dict:
    """
    Runs the full ingestion pipeline on the staged PDF:
    1. Extracts text, chunks, and writes to staging disk.
    2. Embeds chunks into ChromaDB.
    3. Syncs all staged files to Supabase Storage + DB (with retry).
    4. Staging dir is auto-deleted by sync_to_supabase on success.

    If Supabase sync fails, staging files remain on disk for auto-resume on restart.
    """
    state_data = {}
    try:
        from .staging_manager import read_state
        state_data = read_state(ctx)
    except Exception:
        pass

    file_size = state_data.get("file_size", 0)

    try:
        page_count = parse_pdf(ctx)
    except Exception as e:
        logger.exception("[Orchestrator] PDF parsing failed for '%s': %s", ctx.filename, e)
        update_state(ctx, {"status": "parse_failed", "last_error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {e}")

    try:
        sync_to_supabase(ctx, file_size=file_size, page_count=page_count)
    except Exception as e:
        logger.exception(
            "[Orchestrator] Supabase sync failed for '%s': %s. Staging files preserved for retry.",
            ctx.filename, e
        )
        update_state(ctx, {"status": "sync_failed", "last_error": str(e)})
        raise HTTPException(
            status_code=502,
            detail="PDF processed but could not sync to storage. Will retry automatically on restart."
        )

    return {
        "filename": ctx.filename,
        "page_count": page_count,
        "status": "processed",
    }


def query(request: str, doc_name: str | None = None, history: list[dict] | None = None) -> dict:
    """Searches for relevant chunks and generates an LLM answer for the given question."""
    try:
        candidates = retrieval.search(request, doc_name=doc_name)
        chunks = rerank(request, candidates, top_k=3)
    except EmptyCollectionError:
        raise HTTPException(
            status_code=404,
            detail="No documents have been uploaded yet. Please upload a PDF first."
        )
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Retrieval failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to search documents. Are any PDFs embedded?")

    if not chunks:
        raise HTTPException(status_code=404, detail="No relevant content found in the documents.")

    prompt = build_prompt(request, chunks)

    try:
        response = generate_response(prompt, history=history)
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid GROQ_API_KEY. Check your .env file.")
    except RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limited by Groq. Try again later.")
    except APIConnectionError:
        raise HTTPException(status_code=502, detail="Could not connect to Groq API. Check your network.")
    except Exception:
        raise HTTPException(status_code=502, detail="LLM service unavailable. Try again later.")

    sources = [{"page": c["metadata"]["page_number"]} for c in chunks]
    return {"query": request, "results": response, "sources": sources}


def stream_query(request: str, doc_name: str | None = None, history: list[dict] | None = None):
    """Performs retrieval and yields SSE events: sources, token chunks, and done."""
    try:
        candidates = retrieval.search(request, doc_name=doc_name)
        chunks = rerank(request, candidates, top_k=3)
    except EmptyCollectionError:
        yield f"data: {json.dumps({'type': 'error', 'detail': 'No documents have been uploaded yet. Please upload a PDF first.'})}\n\n"
        return
    except DocumentNotFoundError as e:
        yield f"data: {json.dumps({'type': 'error', 'detail': str(e)})}\n\n"
        return
    except Exception as e:
        logger.exception("Retrieval failed: %s", e)
        yield f"data: {json.dumps({'type': 'error', 'detail': 'Failed to search documents. Are any PDFs embedded?'})}\n\n"
        return

    if not chunks:
        yield f"data: {json.dumps({'type': 'error', 'detail': 'No relevant content found in the documents.'})}\n\n"
        return

    sources = [{"page": c["metadata"]["page_number"]} for c in chunks]
    yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

    prompt = build_prompt(request, chunks)

    try:
        for token in stream_response(prompt, history=history):
            yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"
    except Exception as e:
        logger.exception("Streaming generation failed: %s", e)
        yield f"data: {json.dumps({'type': 'error', 'detail': 'LLM streaming failed.'})}\n\n"
        return

    yield f"data: {json.dumps({'type': 'done'})}\n\n"
