"""
supabase_sync.py
Handles resilient, checkpointed uploads from the on-disk staging area to Supabase Storage
and PostgreSQL. Retries on network failures using exponential backoff (tenacity).
Only deletes staging files after confirmed end-to-end receipt.
"""

import logging
from pathlib import Path

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from .staging_manager import StagingContext, update_state, cleanup_staging_area, read_state
from .supabase_service import upload_bytes, record_document

logger = logging.getLogger(__name__)

# Retry up to 5 times with exponential backoff: 2s, 4s, 8s, 16s, 32s
_RETRY_POLICY = dict(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=32),
    retry=retry_if_exception_type(Exception),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)


@retry(**_RETRY_POLICY)
def _upload_asset(storage_path: str, local_path: Path, content_type: str) -> None:
    """Uploads a single file from disk to Supabase Storage, retrying on failure."""
    with open(local_path, "rb") as f:
        data = f.read()
    upload_bytes(storage_path, data, content_type=content_type)


def sync_to_supabase(
    ctx: StagingContext,
    file_size: int = 0,
    page_count: int = 0,
) -> None:
    """
    Uploads all staged assets to Supabase Storage in order, checking checkpoints
    before each upload to skip already-confirmed assets. Commits PostgreSQL metadata
    record last. Cleans up staging directory only on full success.

    If any step fails, staging files remain on disk for retry.
    """
    state = read_state(ctx)
    synced = state.get("synced_assets", {})
    stem = Path(ctx.filename).stem

    # 1. Upload PDF
    if not synced.get("pdf") and ctx.pdf_path.is_file():
        logger.info("[Sync] Uploading PDF for '%s'...", ctx.filename)
        _upload_asset(f"pdfs/{ctx.filename}", ctx.pdf_path, "application/pdf")
        update_state(ctx, {"synced_assets": {"pdf": True}})
        logger.info("[Sync] ✓ PDF uploaded for '%s'", ctx.filename)

    # 2. Upload Markdown
    if not synced.get("markdown") and ctx.md_path.is_file():
        logger.info("[Sync] Uploading Markdown for '%s'...", ctx.filename)
        _upload_asset(f"markdown/{stem}.md", ctx.md_path, "text/markdown")
        update_state(ctx, {"synced_assets": {"markdown": True}})
        logger.info("[Sync] ✓ Markdown uploaded for '%s'", ctx.filename)

    # 3. Upload page JSON extracts
    if not synced.get("extracts") and ctx.pages_path.is_file():
        logger.info("[Sync] Uploading page extracts for '%s'...", ctx.filename)
        _upload_asset(f"extracts/{stem}.json", ctx.pages_path, "application/json")
        update_state(ctx, {"synced_assets": {"extracts": True}})
        logger.info("[Sync] ✓ Extracts uploaded for '%s'", ctx.filename)

    # 4. Upload chunks JSON
    if not synced.get("chunks") and ctx.chunks_path.is_file():
        logger.info("[Sync] Uploading chunks for '%s'...", ctx.filename)
        _upload_asset(f"chunks/{stem}_chunks.json", ctx.chunks_path, "application/json")
        update_state(ctx, {"synced_assets": {"chunks": True}})
        logger.info("[Sync] ✓ Chunks uploaded for '%s'", ctx.filename)

    # 5. Commit metadata to Supabase PostgreSQL (last — acts as final confirmation)
    state = read_state(ctx)
    if not state.get("db_committed"):
        logger.info("[Sync] Committing document record to Supabase DB for '%s'...", ctx.filename)
        record_document(
            filename=ctx.filename,
            file_path=f"pdfs/{ctx.filename}",
            markdown_path=f"markdown/{stem}.md",
            json_extract_path=f"extracts/{stem}.json",
            chunks_path=f"chunks/{stem}_chunks.json",
            file_size_bytes=file_size,
            page_count=page_count,
            status="processed",
        )
        update_state(ctx, {"db_committed": True, "status": "completed"})
        logger.info("[Sync] ✓ DB record committed for '%s'", ctx.filename)

    # 6. All confirmed — clean up local staging files
    cleanup_staging_area(ctx)
    logger.info("[Sync] ✓ Staging cleanup complete for '%s'", ctx.filename)
