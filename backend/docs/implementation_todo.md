# Implementation To-Do: Staged Scratch Buffer & Resilient Supabase Sync

> [!IMPORTANT]
> All 10 steps have been executed and verified. The full test suite passes with 62/62 tests OK.

---

## Progress: 10 / 10 Steps Complete ✅

---

- [x] **Step 1 — Create the Staging Directory & `.gitignore` Entry**
  - Created `backend/Staging/` directory (tracked via `.gitkeep`).
  - Added `Staging/*/` to `.gitignore` so uploaded files and extracts are never committed.

---

- [x] **Step 2 — Add `tenacity` Retry Dependency**
  - Added `tenacity` to `pyproject.toml` for exponential backoff & retry logic on network failures.
  - Ran `uv sync` to update `uv.lock`.

---

- [x] **Step 3 — Build `core/staging_manager.py`**
  - `create_staging_area(filename: str) -> StagingContext`: Creates `Staging/<doc_id>/` with a unique UUID, writes `state.json`.
  - `update_state(staging_ctx, key, value)`: Atomically updates `state.json` checkpoints.
  - `cleanup_staging_area(staging_ctx)`: Deletes the entire `Staging/<doc_id>/` folder.
  - `list_incomplete_jobs() -> list[StagingContext]`: Scans `Staging/` for any interrupted jobs (for boot-time recovery).

---

- [x] **Step 4 — Build `core/supabase_sync.py`**
  - `sync_to_supabase(staging_ctx)`: Reads each file from disk and uploads to Supabase Storage sequentially.
  - Implements **exponential backoff retries** per asset (PDF, Markdown, Extracts, Chunks).
  - Checks `state.json` before each upload — skips already-confirmed assets.
  - Commits document record to Supabase PostgreSQL after all storage uploads succeed.
  - Calls `cleanup_staging_area(staging_ctx)` only after full confirmation.

---

- [x] **Step 5 — Rewrite `core/parser.py`**
  - Accepts `staging_ctx: StagingContext` instead of raw `file_path`.
  - Parses PDF with `pymupdf4llm.to_markdown(doc, page_chunks=True)`.
  - Explicitly closes the PyMuPDF document handle (`doc.close()`) immediately after extraction to free C heap memory.
  - Writes `.md`, `pages.json`, `chunks.json` to `staging_ctx.dir` on disk (not in-memory).
  - Calls `embed(chunks_data, name)` for ChromaDB directly from loaded data.
  - Returns `page_count`.

---

- [x] **Step 6 — Rewrite `core/orchestrator.py`**
  - `save(file: UploadFile)`: Streams PDF chunks to `staging_ctx.pdf_path` on disk. Updates `state.json` as staging begins.
  - `process(staging_ctx)`: Runs `parse_pdf(staging_ctx)` → `sync_to_supabase(staging_ctx)`.
  - On Supabase failure, leaves staging files on disk for auto-resume on restart.
  - Removes all references to `tempfile.NamedTemporaryFile` for staging.

---

- [x] **Step 7 — Update `app.py` Upload Route**
  - Removed `UPLOAD_DIR` and all `Media/Uploads` references from `app.py`.
  - Updated `/upload` to pass the new `StagingContext` through `orchestrator.save()` and `orchestrator.process()`.
  - Modernized application lifecycle management with FastAPI `lifespan`.

---

- [x] **Step 8 — Add Boot-Time Resume Worker**
  - In `app.py`, configured FastAPI `lifespan` context manager.
  - On startup, calls `staging_manager.list_incomplete_jobs()`.
  - For any incomplete jobs found (from dropped connections or crashes), triggers `sync_to_supabase(staging_ctx)` in a background worker thread.

---

- [x] **Step 9 — Update Test Suite**
  - Updated `tests/test_api.py` to match the `save(file) -> StagingContext` signature and patched Supabase storage mocks.
  - Added `tests/test_staging.py` (13 tests verifying folder creation, state checkpointing, load, and cleanup).
  - Added `tests/test_supabase_sync.py` (5 tests verifying asset upload sequence, checkpoint skipping, error preservation, and tenacity retries).

---

- [x] **Step 10 — End-to-End Verification & Cleanup**
  - Full test suite passing: `Ran 62 tests in 0.154s OK`.
  - Verified `Staging/` directory remains clean post-completion (`.gitkeep` preserved).
  - Verified failed sync leaves staging assets intact on disk for resume.
