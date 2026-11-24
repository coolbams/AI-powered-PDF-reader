import json
import logging
import os
import asyncio

from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pathlib import Path
from applog import setup_logging
from applog.middleware import RequestLoggingMiddleware

try:
    from core import orchestrator
    from core.get_uploaded_files import get_file_list
    from core.doc_selector import set_document
    from core.staging_manager import list_incomplete_jobs
    from core.supabase_sync import sync_to_supabase
    from core.supabase_service import download_bytes
except ImportError:
    from backend.core import orchestrator
    from backend.core.get_uploaded_files import get_file_list
    from backend.core.doc_selector import set_document
    from backend.core.staging_manager import list_incomplete_jobs
    from backend.core.supabase_sync import sync_to_supabase
    from backend.core.supabase_service import download_bytes

setup_logging(level="INFO", log_dir="logs")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent


class AskRequest(BaseModel):
    query: str
    doc_name: str | None = None
    history: list[dict] | None = None


def _resume_incomplete_jobs() -> None:
    """
    Scans Staging/ for any interrupted jobs (e.g. from a server crash or network drop)
    and resumes Supabase sync for each one in a background thread.
    """
    pending = list_incomplete_jobs()
    if not pending:
        logger.info("[Startup] No interrupted staging jobs found.")
        return

    logger.info("[Startup] Found %d incomplete staging job(s). Resuming sync...", len(pending))
    for ctx in pending:
        try:
            logger.info("[Startup] Resuming sync for '%s' (%s)...", ctx.filename, ctx.doc_id)
            sync_to_supabase(ctx)
        except Exception as e:
            logger.warning(
                "[Startup] Could not resume sync for '%s': %s. Will retry on next restart.",
                ctx.filename, e
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs startup logic before the server begins accepting requests."""
    await asyncio.to_thread(_resume_incomplete_jobs)
    yield


app = FastAPI(debug=True, title="Bud's Rag Server", lifespan=lifespan)

origins_env = os.getenv("CORS_ORIGINS", "*")
allowed_origins = [o.strip() for o in origins_env.split(",") if o.strip()]

app.add_middleware(RequestLoggingMiddleware)
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
    """Streams the uploaded PDF to the staging directory, processes it, and syncs to Supabase."""
    ctx = await orchestrator.save(file)
    return await asyncio.to_thread(orchestrator.process, ctx)


@app.post("/ask")
async def query(body: AskRequest):
    """Receives a question, retrieves relevant chunks, and returns an LLM answer."""
    return await asyncio.to_thread(orchestrator.query, body.query, body.doc_name, body.history)


@app.post("/ask/stream")
async def query_stream(body: AskRequest):
    """Streams LLM tokens and sources back to the client using Server-Sent Events."""
    return StreamingResponse(
        orchestrator.stream_query(body.query, body.doc_name, body.history),
        media_type="text/event-stream",
    )


@app.get("/list_files")
async def get_uploaded_files():
    """Returns a JSON list of all PDF filenames from Supabase PostgreSQL."""
    try:
        file_list = get_file_list()
        return {"files": file_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/files/{filename}")
def get_selected_doc(filename: str):
    """Fetches and streams the named PDF from Supabase Storage."""
    return set_document(filename)


@app.get("/markdown/{filename}")
def get_extracted_markdown(filename: str):
    """Returns the parsed per-page markdown list from Supabase Storage."""
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename: path traversal characters are not permitted.")

    safe_name = Path(filename).name
    if safe_name.lower().endswith(".pdf"):
        safe_name = Path(safe_name).stem

    raw_json = download_bytes(f"extracts/{safe_name}.json")
    if raw_json:
        try:
            pages = json.loads(raw_json.decode("utf-8"))
            return {"filename": safe_name, "pages": pages}
        except Exception:
            pass

    raw_md = download_bytes(f"markdown/{safe_name}.md")
    if raw_md:
        try:
            text = raw_md.decode("utf-8")
            return {"filename": safe_name, "pages": [{"page_number": 1, "text": text}]}
        except Exception:
            pass

    raise HTTPException(status_code=404, detail=f"Markdown extract for '{filename}' not found.")
