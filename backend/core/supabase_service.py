import os
import io
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

from .exceptions import ConfigurationError

load_dotenv()

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
SUPABASE_KEY = SUPABASE_SERVICE_ROLE_KEY
SUPABASE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET") or "pdf-reader"

_supabase_client = None


def is_supabase_enabled() -> bool:
    """Returns True if Supabase URL and Key are set and not placeholder values."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    if "your-project-ref" in SUPABASE_URL or "your-supabase" in SUPABASE_KEY:
        return False
    return True


def require_supabase():
    """Validates that Supabase credentials are configured, raising ConfigurationError otherwise."""
    if not is_supabase_enabled():
        raise ConfigurationError(
            "Supabase is required as the primary storage engine. "
            "Please configure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in your .env file."
        )


def get_supabase_client():
    """Initializes and returns the singleton Supabase client. Raises ConfigurationError if unconfigured."""
    global _supabase_client
    require_supabase()

    if _supabase_client is None:
        try:
            from supabase import create_client
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Connected to Supabase client successfully.")
        except Exception as e:
            logger.exception("Failed to initialize Supabase client: %s", e)
            raise

    return _supabase_client


def ensure_bucket_exists(bucket_name: str | None = None) -> bool:
    """Ensures the target storage bucket exists; creates it if permissions allow."""
    client = get_supabase_client()
    bucket = bucket_name or SUPABASE_BUCKET
    try:
        buckets = client.storage.list_buckets()
        existing = [b.name for b in buckets if hasattr(b, "name")] if buckets else []
        if bucket not in existing:
            client.storage.create_bucket(bucket, options={"public": True})
            logger.info("Created Supabase storage bucket '%s'", bucket)
        return True
    except Exception as e:
        logger.warning("Could not auto-create bucket '%s' (it may already exist): %s", bucket, e)
        return False


def upload_bytes(
    storage_path: str,
    data: bytes,
    content_type: str = "application/octet-stream",
    bucket_name: str | None = None,
) -> str:
    """Uploads bytes directly to Supabase Storage at the specified path (upsert enabled)."""
    client = get_supabase_client()
    bucket = bucket_name or SUPABASE_BUCKET
    normalized_path = storage_path.lstrip("/")

    client.storage.from_(bucket).upload(
        path=normalized_path,
        file=data,
        file_options={"content-type": content_type, "upsert": "true"},
    )
    logger.info("Uploaded %s to Supabase bucket '%s'", normalized_path, bucket)
    return normalized_path


def download_bytes(storage_path: str, bucket_name: str | None = None) -> bytes | None:
    """Downloads file bytes from Supabase Storage. Returns None if not found."""
    client = get_supabase_client()
    bucket = bucket_name or SUPABASE_BUCKET
    try:
        normalized_path = storage_path.lstrip("/")
        return client.storage.from_(bucket).download(normalized_path)
    except Exception as e:
        logger.warning("Failed to download %s from Supabase Storage: %s", storage_path, e)
        return None


def get_signed_url(storage_path: str, expires_in: int = 3600, bucket_name: str | None = None) -> str | None:
    """Generates a temporary signed download URL for the file."""
    client = get_supabase_client()
    bucket = bucket_name or SUPABASE_BUCKET
    try:
        normalized_path = storage_path.lstrip("/")
        res = client.storage.from_(bucket).create_signed_url(normalized_path, expires_in)
        if isinstance(res, dict) and "signedURL" in res:
            return res["signedURL"]
        return getattr(res, "signed_url", None) or str(res)
    except Exception as e:
        logger.warning("Failed to generate signed URL for %s: %s", storage_path, e)
        return None


def delete_storage_files(storage_paths: list[str], bucket_name: str | None = None) -> bool:
    """Deletes files from Supabase Storage."""
    client = get_supabase_client()
    if not storage_paths:
        return False

    bucket = bucket_name or SUPABASE_BUCKET
    try:
        paths = [p.lstrip("/") for p in storage_paths]
        client.storage.from_(bucket).remove(paths)
        return True
    except Exception as e:
        logger.warning("Failed to delete files %s from Supabase Storage: %s", storage_paths, e)
        return False


def record_document(
    filename: str,
    file_path: str,
    markdown_path: str | None = None,
    json_extract_path: str | None = None,
    chunks_path: str | None = None,
    file_size_bytes: int = 0,
    page_count: int = 0,
    status: str = "processed",
) -> dict:
    """Upserts document metadata into the Supabase 'documents' table."""
    client = get_supabase_client()
    payload = {
        "filename": filename,
        "title": Path(filename).stem,
        "file_path": file_path.lstrip("/"),
        "markdown_path": markdown_path.lstrip("/") if markdown_path else None,
        "json_extract_path": json_extract_path.lstrip("/") if json_extract_path else None,
        "chunks_path": chunks_path.lstrip("/") if chunks_path else None,
        "file_size_bytes": file_size_bytes,
        "page_count": page_count,
        "status": status,
    }

    res = client.table("documents").upsert(payload, on_conflict="filename").execute()
    return res.data[0] if (res.data and len(res.data) > 0) else payload


def get_document_record(filename: str) -> dict | None:
    """Fetches document metadata from the 'documents' table."""
    client = get_supabase_client()
    try:
        safe_name = Path(filename).name
        stem_name = Path(safe_name).stem

        res = client.table("documents").select("*").or_(f"filename.eq.{safe_name},filename.eq.{stem_name}").limit(1).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except Exception as e:
        logger.warning("Failed to fetch document record for '%s': %s", filename, e)
        return None


def list_document_filenames() -> list[str]:
    """Retrieves list of all document filenames from the 'documents' table in Supabase."""
    client = get_supabase_client()
    try:
        res = client.table("documents").select("filename").order("created_at", desc=True).execute()
        if res.data:
            return [Path(item["filename"]).stem for item in res.data if "filename" in item]
        return []
    except Exception as e:
        logger.warning("Failed to list documents from Supabase: %s", e)
        return []


def delete_document_record(filename: str) -> bool:
    """Deletes document row from Supabase database and associated bucket assets."""
    client = get_supabase_client()
    try:
        doc = get_document_record(filename)
        if doc:
            storage_paths = [
                doc.get("file_path"),
                doc.get("markdown_path"),
                doc.get("json_extract_path"),
                doc.get("chunks_path"),
            ]
            valid_paths = [p for p in storage_paths if p]
            if valid_paths:
                delete_storage_files(valid_paths)

        client.table("documents").delete().eq("filename", filename).execute()
        return True
    except Exception as e:
        logger.warning("Failed to delete document '%s' from Supabase: %s", filename, e)
        return False
