from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from .core import orchestrator

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


