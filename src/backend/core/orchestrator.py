from pathlib import Path
from fastapi import HTTPException, UploadFile

from .parser import parse_pdf
from .retrieval import Retrieval
from .prompt_builder import build_prompt
from .generate import generate_response

retrieval = Retrieval()

def validate(file: UploadFile):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

async def save(file: UploadFile, upload_dir: Path) -> Path:
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
    return parse_pdf(file_path)

def query(request: str) -> dict:
    chunks = retrieval.search(request)
    prompt = build_prompt(request, chunks)
    response = generate_response(prompt)
    return {"query": request, "results": response}

    