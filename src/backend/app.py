from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from .Ingestion import parser

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

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    content = await file.read()
    if len(content) == 0: 
         raise HTTPException(status_code=400, detail="File is empty")
    if len(content)  > 10 * 1024 * 1024:
         raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    safe_name = Path(file.filename).name #

    input_file = UPLOAD_DIR / safe_name
    input_file.write_bytes(content)
    
    try:
        result = parser.parse_pdf(input_file)
    except Exception as e:
         input_file.unlink(missing_ok=True)
         raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")
    
    return{
        "filename": safe_name,
        "content_type": file.content_type,
        "saved_to": str(input_file),
        "markdown": result["markdown"],
        "metadata": result["metadata"], 
        "chunks": result["chunks"],
    }


