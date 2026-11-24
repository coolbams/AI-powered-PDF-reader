from pathlib import Path
from fastapi import HTTPException, Response
import logging

from .supabase_service import download_bytes

log = logging.getLogger(__name__)


def set_document(selected_file: str) -> Response:
    """Validates the requested PDF, guards against path traversal, downloads from Supabase Storage, and streams it back."""
    
    # Guard against directory traversal attempts
    if ".." in selected_file or "/" in selected_file or "\\" in selected_file:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename: path traversal characters are not permitted.",
        )

    safe_name = Path(selected_file).name
    if not safe_name.lower().endswith(".pdf"):
        safe_name = f"{safe_name}.pdf"

    pdf_bytes = download_bytes(f"pdfs/{safe_name}")
    if not pdf_bytes:
        log.warning('File "%s" not found in Supabase Storage', selected_file)
        raise HTTPException(
            status_code=404, detail=f"File '{selected_file}' not found."
        )

    return Response(content=pdf_bytes, media_type="application/pdf")
