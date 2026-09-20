from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "Media" / "Uploads"

session_state = {"active_doc": None}


def set_document( selected_file ):
    """Validates the requested PDF exists, records it as the active document, and streams it back."""
    
    file_path = UPLOAD_DIR / selected_file

    if not file_path.is_file():
        raise HTTPException(
            status_code=404, detail=f"File '{selected_file}' not found."
        )
    # return selected_file
    
    # Set as active document on the backend
    session_state["active_doc"] = selected_file

    return FileResponse(file_path, media_type="application/pdf")    