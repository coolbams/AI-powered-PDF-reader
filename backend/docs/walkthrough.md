# Walkthrough: Staged Scratch Buffer & Resilient Supabase Sync

## 1. What was accomplished

We completed the 10-step implementation of the **Staged Scratch Buffer & Resilient Supabase Sync** architecture. This solves both memory pressure and network resilience:
- Instead of keeping large files and extracts in memory during uploads, assets are written to a managed, temporary on-disk workspace (`Staging/<doc_id>/`).
- Text extraction uses PyMuPDF with an explicit `doc.close()` in a `finally` block to immediately reclaim C-heap memory.
- Assets are synced to Supabase Storage with exponential backoff retry via `tenacity`.
- Upload state is checkpointed in `state.json` — if a connection drops, retries pick up only missing assets without restarting from zero.
- The PostgreSQL document record is committed last as confirmation; only then is the staging directory deleted.
- If the server restarts with interrupted uploads, a FastAPI `lifespan` worker automatically scans `Staging/` and resumes syncing in the background.

---

## 2. Key Changes Made

### 1. Staging Area Management ([`core/staging_manager.py`](file:///home/duke-cre/Programs/AI-powered-PDF-reader/backend/core/staging_manager.py))
- `create_staging_area(filename)`: Allocates `Staging/<uuid>/`, initializes `state.json` with checkpoint tracking.
- `update_state(ctx, updates)`: Atomically merges updates into `state.json`, including nested `synced_assets` flags.
- `cleanup_staging_area(ctx)`: Recursively removes `Staging/<uuid>/` on confirmed completion.
- `list_incomplete_jobs()`: Scans `Staging/` for workspaces where `db_committed == False`.
- `load_staging_context(dir)`: Reconstructs a `StagingContext` from an existing staging directory on disk.

### 2. Resilient Cloud Sync with Retry ([`core/supabase_sync.py`](file:///home/duke-cre/Programs/AI-powered-PDF-reader/backend/core/supabase_sync.py))
- `sync_to_supabase(ctx, file_size, page_count)`: Sequential asset upload (`pdf` → `markdown` → `extracts` → `chunks` → `db_record`).
- Decorated `_upload_asset()` with `@retry`: up to 5 attempts with exponential backoff (2s → 32s) handling transient network drops.
- Checks `state.json` checkpoints before each upload; already-uploaded assets are skipped on retry.
- Only calls `cleanup_staging_area(ctx)` after the database record is successfully committed.

### 3. Memory-Optimized PDF Parsing ([`core/parser.py`](file:///home/duke-cre/Programs/AI-powered-PDF-reader/backend/core/parser.py))
- Reads the PDF from `ctx.pdf_path` on disk.
- Runs `pymupdf4llm.to_markdown(doc, page_chunks=True)`.
- **Explicitly calls `doc.close()`** in a `finally` block to free PyMuPDF C-heap allocations immediately.
- Writes markdown (`.md`), page extracts (`.pages.json`), and chunk data (`.chunks.json`) directly to disk in the staging area.
- Embeds chunks into ChromaDB from memory.

### 4. Ephemeral Orchestrator Stream ([`core/orchestrator.py`](file:///home/duke-cre/Programs/AI-powered-PDF-reader/backend/core/orchestrator.py))
- `save(file: UploadFile) -> StagingContext`: Streams file in 1 MB chunks to `ctx.pdf_path` with a 50 MB bound. Cleans up staging dir immediately if validation fails (oversized or non-PDF).
- `process(ctx: StagingContext)`: Orchestrates parsing and Supabase sync. Leaves staging directory intact on network/sync failure so it can be resumed.

### 5. Application Lifecycle & Startup Recovery ([`app.py`](file:///home/duke-cre/Programs/AI-powered-PDF-reader/backend/app.py))
- Added modern FastAPI `lifespan` context manager.
- Scans `list_incomplete_jobs()` at startup and dispatches background resume syncs via `asyncio.to_thread`.

### 6. Comprehensive Test Suite ([`tests/`](file:///home/duke-cre/Programs/AI-powered-PDF-reader/backend/tests))
- [`tests/test_staging.py`](file:///home/duke-cre/Programs/AI-powered-PDF-reader/backend/tests/test_staging.py): 13 unit tests covering folder creation, pathing, checkpoint updates, cleanup, and crash-resume listing.
- [`tests/test_supabase_sync.py`](file:///home/duke-cre/Programs/AI-powered-PDF-reader/backend/tests/test_supabase_sync.py): 5 unit tests covering sequential sync, checkpoint skipping, failure preservation, and `tenacity` retry backoff.
- [`tests/test_api.py`](file:///home/duke-cre/Programs/AI-powered-PDF-reader/backend/tests/test_api.py): Updated upload route and markdown mock assertions.

---

## 3. Verification Results

```bash
$ uv run python -m unittest discover tests
..............................................................
----------------------------------------------------------------------
Ran 62 tests in 0.154s

OK
```

- **All 62 tests passed** (including all original 39 API/retrieval/doc tests + 23 new staging/sync tests).
- Confirmed `Staging/` remains clean (`.gitkeep` intact) after upload completion.
- Verified staging directory preservation when sync encounters simulated failures.
