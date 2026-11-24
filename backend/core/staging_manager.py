"""
staging_manager.py
Manages on-disk scratch areas for uploaded PDFs and their extracted assets.
Files live in Staging/<doc_id>/ until Supabase confirms receipt, then are deleted.
"""

import json
import logging
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
STAGING_DIR = BASE_DIR / "Staging"
STAGING_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class StagingContext:
    """Represents a single document's staging workspace on disk."""
    doc_id: str
    filename: str
    dir: Path
    state_path: Path
    pdf_path: Path
    md_path: Path
    pages_path: Path
    chunks_path: Path


def _default_state(doc_id: str, filename: str) -> dict:
    return {
        "doc_id": doc_id,
        "filename": filename,
        "file_size": 0,
        "page_count": 0,
        "status": "staging",
        "synced_assets": {
            "pdf": False,
            "markdown": False,
            "extracts": False,
            "chunks": False,
        },
        "db_committed": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def create_staging_area(filename: str) -> StagingContext:
    """Creates a unique staging directory for the document and writes an initial state.json."""
    doc_id = str(uuid.uuid4())
    staging_dir = STAGING_DIR / doc_id
    staging_dir.mkdir(parents=True, exist_ok=True)

    stem = Path(filename).stem
    ctx = StagingContext(
        doc_id=doc_id,
        filename=filename,
        dir=staging_dir,
        state_path=staging_dir / "state.json",
        pdf_path=staging_dir / filename,
        md_path=staging_dir / f"{stem}.md",
        pages_path=staging_dir / f"{stem}.pages.json",
        chunks_path=staging_dir / f"{stem}.chunks.json",
    )

    state = _default_state(doc_id, filename)
    ctx.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    logger.info("Created staging area for '%s' at %s", filename, staging_dir)
    return ctx


def load_staging_context(staging_dir: Path) -> StagingContext | None:
    """Loads a StagingContext from an existing staging directory."""
    state_path = staging_dir / "state.json"
    if not state_path.is_file():
        return None
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        filename = state["filename"]
        stem = Path(filename).stem
        return StagingContext(
            doc_id=state["doc_id"],
            filename=filename,
            dir=staging_dir,
            state_path=state_path,
            pdf_path=staging_dir / filename,
            md_path=staging_dir / f"{stem}.md",
            pages_path=staging_dir / f"{stem}.pages.json",
            chunks_path=staging_dir / f"{stem}.chunks.json",
        )
    except Exception as e:
        logger.warning("Could not load staging context from %s: %s", staging_dir, e)
        return None


def read_state(ctx: StagingContext) -> dict:
    """Reads and parses the current state.json for a staging area."""
    return json.loads(ctx.state_path.read_text(encoding="utf-8"))


def update_state(ctx: StagingContext, updates: dict) -> None:
    """Atomically updates fields in the staging area's state.json."""
    state = read_state(ctx)
    # Support nested updates for synced_assets
    for key, value in updates.items():
        if key == "synced_assets" and isinstance(value, dict):
            state["synced_assets"].update(value)
        else:
            state[key] = value
    ctx.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def cleanup_staging_area(ctx: StagingContext) -> None:
    """Deletes the entire staging directory once Supabase confirms full receipt."""
    if ctx.dir.exists():
        shutil.rmtree(ctx.dir)
        logger.info("Cleaned up staging area for '%s' (%s)", ctx.filename, ctx.doc_id)


def list_incomplete_jobs() -> list[StagingContext]:
    """Scans the Staging/ directory for any interrupted jobs not yet fully synced to Supabase."""
    incomplete = []
    for staging_dir in STAGING_DIR.iterdir():
        if not staging_dir.is_dir():
            continue
        ctx = load_staging_context(staging_dir)
        if not ctx:
            continue
        try:
            state = read_state(ctx)
            if not state.get("db_committed", False):
                incomplete.append(ctx)
        except Exception as e:
            logger.warning("Skipping unreadable staging dir %s: %s", staging_dir, e)
    return incomplete
