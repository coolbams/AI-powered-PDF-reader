from pathlib import Path
import logging
from fastapi import HTTPException, UploadFile
from groq import APIConnectionError, AuthenticationError, RateLimitError

from .parser import parse_pdf
from .retrieval import Retrieval
from .exceptions import EmptyCollectionError, DocumentNotFoundError
from .prompt_builder import build_prompt
from .generate import generate_response

logger = logging.getLogger(__name__)
retrieval = Retrieval()

def validate(file: UploadFile):
    """Raises a 400 HTTP error if the uploaded file is not a PDF."""

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

async def save(file: UploadFile, upload_dir: Path) -> Path:
    """Validates, reads, and writes the uploaded file to disk; returns its saved path."""

    validate(file)
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 20MB)")

    safe_name = Path(file.filename).name
    file_path = upload_dir / safe_name
    file_path.write_bytes(content)

    return file_path

def process(file_path: Path) -> dict:
    """Parses the PDF at file_path and triggers embedding; returns the output file paths."""

    return parse_pdf(file_path)

def query(request: str, doc_name: str | None = None, history: list[dict] | None = None) -> dict:
    """Searches for relevant chunks and generates an LLM answer for the given question."""

    try:
        chunks = retrieval.search(request, doc_name=doc_name)
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

    sources = [
        {
            "text": c["text"][:200] + "..." if len(c["text"]) > 200 else c["text"],
            "page": c["metadata"]["page_number"],
            "doc_name": c["metadata"].get("doc_name"),
        }
        for c in chunks
    ]

    return {"query": request, "results": response, "sources": sources}

    