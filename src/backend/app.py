from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path

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


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    return orchestrator.process(file_path)


@app.post("/ask")
async def query(body: AskRequest):
    """Receives a question, retrieves relevant chunks, and returns an LLM answer."""

    return orchestrator.query(body.query, body.doc_name, body.history)


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


