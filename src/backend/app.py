from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from backend.core import orchestrator
from backend.core.get_uploaded_files import get_file_list
from backend.core.doc_selector import set_document


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
    return " Bud's Backend is 200 "
    

@app.post("/upload")
async def upload(file: UploadFile = File(...)):

    file_path = await orchestrator.save(file, UPLOAD_DIR)
    return orchestrator.process(file_path)


@app.post("/ask")
async def query(request: str):
    return orchestrator.query(request)


@app.get("/list_files")
async def get_uploaded_files():
    try:
        file_list = get_file_list()
        return {"files": file_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/files/{filename}")
def get_selcted_doc( filename: str ):

    return set_document(filename)


