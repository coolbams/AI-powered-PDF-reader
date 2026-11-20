import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, PlainTextResponse
from pydantic import BaseModel
from pathlib import Path

import asyncio

try:
    from core import orchestrator
    from core.get_uploaded_files import get_file_list
    from core.doc_selector import set_document
except ImportError:
    from backend.core import orchestrator
    from backend.core.get_uploaded_files import get_file_list
    from backend.core.doc_selector import set_document



class AskRequest(BaseModel):
    query: str
    doc_name: str | None = None
    history: list[dict] | None = None


BASE_DIR = Path(__file__).resolve().parent

UPLOAD_DIR = BASE_DIR / "Media" / "Uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(debug=True, title= "Bud's Rag Server")

origins_env = os.getenv("CORS_ORIGINS", "*")
allowed_origins = [o.strip() for o in origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    """Returns a simple health-check string to confirm the server is running."""

    return " Bud's Backend is 200 "
    

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    """Saves the uploaded PDF to disk, parses it, and stores its embeddings."""
    file_path = await orchestrator.save(file, UPLOAD_DIR)
    return await asyncio.to_thread(orchestrator.process, file_path) # Threadpool Worker via asyncio.to_thread


@app.post("/ask")
async def query(body: AskRequest):
    """Receives a question, retrieves relevant chunks, and returns an LLM answer."""

    return orchestrator.query(body.query, body.doc_name, body.history)


@app.post("/ask/stream")
async def query_stream(body:AskRequest):
    """Streams LLM tokens and sources back to the client using Server-Sent Events."""

    return StreamingResponse(
        orchestrator.stream_query(body.query, body.doc_name, body.history),
        media_type="text/event-stream",
    )


@app.get("/list_files")
async def get_uploaded_files():
    """Returns a JSON list of all PDF filenames stored on the server."""

    try:
        file_list = get_file_list()
        return {"files": file_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/files/{filename}")
def get_selcted_doc( filename: str ):
    """Marks the named PDF as the active document and streams it back to the client."""

    return set_document(filename)


@app.get("/markdown/{filename}")
def get_extracted_markdown(filename: str):
    """Returns the parsed per-page markdown list for an uploaded document."""
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename: path traversal characters are not permitted.")
    safe_name = Path(filename).name
    if safe_name.lower().endswith(".pdf"):
        safe_name = Path(safe_name).stem
    extracts_dir = (BASE_DIR / "Media" / "Extracts").resolve()
    json_path = (extracts_dir / f"{safe_name}.json").resolve()
    md_path = (extracts_dir / f"{safe_name}.md").resolve()

    if not json_path.is_relative_to(extracts_dir):
        raise HTTPException(status_code=400, detail="Access outside extracts directory is forbidden.")

    import json
    if json_path.is_file():
        pages = json.loads(json_path.read_text(encoding="utf-8"))
        return {"filename": safe_name, "pages": pages}

    if md_path.is_file():
        return {"filename": safe_name, "pages": [{"page_number": 1, "text": md_path.read_text(encoding="utf-8")}]}

    raise HTTPException(status_code=404, detail=f"Markdown extract for '{filename}' not found.")



