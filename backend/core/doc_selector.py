from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "Media" / "Uploads"



def set_document( selected_file ):
    """Validates the requested PDF exists, guards against path traversal, and streams it back."""
    
    # Guard against directory traversal attempts
    if ".." in selected_file or "/" in selected_file or "\\" in selected_file:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename: path traversal characters are not permitted.",
        )

    # 1. Strip directory components (e.g. "../../sample.pdf" -> "sample.pdf")
    safe_name = Path(selected_file).name
    
    # 2. Ensure it ends with .pdf
    if not safe_name.lower().endswith(".pdf"):
        safe_name = f"{safe_name}.pdf"
        
    # 3. Build and resolve the full path
    file_path = (UPLOAD_DIR / safe_name).resolve()
    
    # 4. Security check: verify the resolved path is inside UPLOAD_DIR
    if not file_path.is_relative_to(UPLOAD_DIR.resolve()):
        raise HTTPException(
            status_code=400,
            detail="Invalid filename: access outside upload directory is forbidden."
        )

    if not file_path.is_file():
        raise HTTPException(
            status_code=404, detail=f"File '{selected_file}' not found."
        )


    return FileResponse(file_path, media_type="application/pdf")    