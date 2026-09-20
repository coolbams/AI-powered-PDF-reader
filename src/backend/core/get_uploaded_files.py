from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "Media" / "Uploads"


UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def get_file_list():
    """Scans the Uploads directory and returns a list of all stored PDF filenames."""
    
    file_names = [f.name for f in UPLOAD_DIR.iterdir() if f.is_file()]

    return file_names



