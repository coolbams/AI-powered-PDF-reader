# Codebase Quality Audit: Bud (AI-Powered PDF Reader)

## What this repo does
Bud is a retrieval-augmented generation (RAG) web app. It lets users upload PDF documents, parses and splits them into vector embeddings stored in ChromaDB, and generates grounded answers with source citations using Groq's LLM. It includes a FastAPI Python backend and a React (Vite + Tailwind CSS) frontend.

**Assumed operational load:** A single user or small interactive team uploading PDFs (up to 20MB) and querying them concurrently via the web interface.

---

## Must fix

1. **Server crashes on startup when following README instructions** (`backend/app.py:L7-16`)
   - **What this is:** The top-level import statement in the backend application entrypoint.
   - **Problem:** Both the `try` and `except` blocks use `from backend.core import orchestrator`. Running `uvicorn app:app` from `backend/` crashes immediately with `ModuleNotFoundError: No module named 'backend'`.
   - **Fix:** Change the import in `backend/app.py` to `from core import orchestrator, get_file_list, set_document`.
   - **If we skip it:** The backend cannot start using standard commands without setting custom Python path environment variables.

2. **Arbitrary file read via path traversal in file download route** (`backend/core/doc_selector.py:L14-25`)
   - **What this is:** The `/files/{filename}` endpoint serves stored PDF files back to the frontend viewer.
   - **Problem:** It appends `.pdf` to user-supplied input without sanitizing path separators. A requester can send directory traversal sequences (e.g. `../../some_file`) to read files outside the uploads directory.
   - **Fix:** Sanitize with `Path(selected_file).name` and verify `file_path.resolve().is_relative_to(UPLOAD_DIR.resolve())`.
   - **If we skip it:** Any client can read arbitrary system or application files accessible by the server process.

3. **Re-uploading an existing PDF silently drops new content** (`backend/core/embeddings.py:L79-84`)
   - **What this is:** The vector storage step that persists text chunks to ChromaDB.
   - **Problem:** It uses `collection.add()`, which ignores duplicate chunk IDs. If a user uploads an edited or updated version of an existing file, the new chunks are silently ignored.
   - **Fix:** Replace `collection.add(...)` with `collection.upsert(...)`.
   - **If we skip it:** Updated documents remain stuck on their original vector embeddings.

4. **Synchronous embedding and parsing freezes the entire web server** (`backend/app.py:L47-51`, `backend/core/parser.py:L19-47`)
   - **What this is:** The `POST /upload` route handles document ingestion.
   - **Problem:** It runs heavy CPU PDF extraction and deep learning model encoding synchronously inside an async route handler. Generating embeddings for a multi-page PDF locks the main event loop for 10–60+ seconds, freezing all other HTTP requests.
   - **Fix:** Offload `orchestrator.process` to a worker thread using `asyncio.to_thread` or FastAPI's `run_in_threadpool`.
   - **If we skip it:** The entire API stops responding to queries and health checks whenever any user uploads a document.

---

## Should fix

5. **Zero automated tests and empty CI workflow** (`.github/workflow/test.yml:L1-11`)
   - **What this is:** Continuous integration and regression testing for the project.
   - **Problem:** There are zero unit or integration tests in the entire repository, and the GitHub Actions workflow file has an empty `jobs:` block.
   - **Fix:** Add basic pytest test coverage for endpoints and retrieval, and fill in the CI workflow.
   - **If we skip it:** Bugs and regressions will only be detected manually after deployment.

6. **Unused heavy dependencies bloat the environment** (`backend/pyproject.toml:L20-22`)
   - **What this is:** The project dependency specifications in `pyproject.toml`.
   - **Problem:** `streamlit`, `streamlit-pdf`, and `requests` are listed as core dependencies but are never imported or used. Streamlit brings dozens of heavy transitive packages (pyarrow, altair, tornado).
   - **Fix:** Remove `streamlit`, `streamlit-pdf`, and `requests` from `backend/pyproject.toml` and run `uv lock`.
   - **If we skip it:** Installs waste hundreds of megabytes of disk space and download bandwidth.

7. **Broken CLI entrypoint in package configuration** (`backend/pyproject.toml:L25-26`, `backend/src/bud/__init__.py`)
   - **What this is:** A console script definition `bud = "bud:main"`.
   - **Problem:** `src/bud/__init__.py` is completely empty. Installing the package and running `bud` crashes with `AttributeError`.
   - **Fix:** Delete the `[project.scripts]` section from `pyproject.toml` until a real CLI is implemented.
   - **If we skip it:** Package builds expose a broken executable command.

8. **Heavy ML models loaded at import time** (`backend/core/retrieval.py:L5`, `backend/core/reranker.py:L3`)
   - **What this is:** Global instantiation of `EmbeddingModel` and `CrossEncoder`.
   - **Problem:** Importing `retrieval` or `reranker` immediately loads multi-gigabyte models into memory and downloads weights if missing.
   - **Fix:** Instantiate models lazily on first query or during FastAPI's lifespan startup handler.
   - **If we skip it:** Running tests, linters, or utility scripts takes 10+ seconds and consumes several gigabytes of RAM.

9. **Dead in-memory state in document selector** (`backend/core/doc_selector.py:L8, L23`)
   - **What this is:** A module-level `session_state = {"active_doc": None}` updated on file fetch.
   - **Problem:** This state is never read anywhere in the application. In a multi-user server, writing to a global dict creates thread-safety hazards and false expectations of session tracking.
   - **Fix:** Delete `session_state`.
   - **If we skip it:** Misleading global state accumulates without purpose.

10. **Redundant disk round-trip during file ingestion** (`backend/core/parser.py:L36-47`, `backend/core/embeddings.py:L69-70`)
    - **What this is:** Passing data from the PDF parser to the embedding generator.
    - **Problem:** `parse_pdf` writes chunks to disk as JSON, and then `embed()` immediately opens and re-parses the exact same JSON from disk.
    - **Fix:** Pass the chunk list directly to `embed()` in memory.
    - **If we skip it:** Wasted CPU time and unnecessary disk I/O on every document upload.

11. **Hardcoded backend URLs in frontend components** (`frontend/src/components/UploadSidebar.jsx:L29`, `frontend/src/components/ChatbotPane.jsx:L56`)
    - **What this is:** API request URLs in frontend React components.
    - **Problem:** `http://localhost:8000` is hardcoded across multiple files. The frontend cannot be deployed or pointed to an alternate port without code changes.
    - **Fix:** Centralize API base URL using `import.meta.env.VITE_API_URL || ""` or configure a Vite proxy.
    - **If we skip it:** The frontend breaks when deployed to any production or custom environment.

12. **Missing file validation causes crashes on upload** (`backend/core/orchestrator.py:L20-21`)
    - **What this is:** Validation check in `validate(file)`.
    - **Problem:** If `file.filename` is `None`, calling `.endswith()` raises an unhandled `AttributeError`. Uppercase extensions like `.PDF` are rejected as invalid.
    - **Fix:** Check `if not file.filename or not file.filename.lower().endswith(".pdf"):`.
    - **If we skip it:** Valid files with uppercase extensions fail to upload, and headless clients without a filename trigger 500 errors.

13. **Duplicate configuration files at project root** (`pyproject.toml`, `uv.lock`)
    - **What this is:** Python configuration files in both root and `backend/`.
    - **Problem:** Exact duplicate copies of `pyproject.toml` and `uv.lock` exist in both locations, leading to drift when dependencies are updated.
    - **Fix:** Remove the root copies or configure the root as a monorepo workspace pointing to `backend`.
    - **If we skip it:** Developers updating dependencies in one file will leave the other outdated.

---

## Nice to have

14. **Unimplemented Markdown view in UI** (`frontend/src/components/PDFFileReader.jsx:L201-207`)
    - **What this is:** The "Markdown" toggle option in the document viewer pane.
    - **Problem:** The toggle displays a static placeholder because no backend endpoint serves the extracted `.md` file.
    - **Fix:** Add `GET /files/{filename}/markdown` to return the stored markdown extract, or hide the toggle until built.
    - **If we skip it:** Users clicking "Markdown" see an empty placeholder.

15. **Typo in prompt template** (`backend/core/prompt_builder.py:L13`)
    - **What this is:** The context-grounding system prompt template.
    - **Problem:** Line 13 has an unclosed quotation mark: `say "the document doesn't specify this.`.
    - **Fix:** Close the quote: `say "the document doesn't specify this."`.
    - **If we skip it:** The LLM receives an unbalanced quote string.

16. **Permissive CORS configuration** (`backend/app.py:L33-38`)
    - **What this is:** Cross-Origin Resource Sharing middleware setup.
    - **Problem:** All origins, methods, and headers are set to wildcard `["*"]`.
    - **Fix:** Restrict `allow_origins` to known frontend hosts via an environment variable.
    - **If we skip it:** Any external site can issue cross-origin requests to the local server.

---

**Verdict:** The backend is currently blocked from running with `uvicorn app:app` due to finding 1, and has a path traversal vulnerability (finding 2) and an event loop blocking bug (finding 4). Fix 1, 2, 3, and 4 first.

**Lean:** -3 dependencies (`streamlit`, `streamlit-pdf`, `requests`), -2 duplicate root files, and ~40 lines of dead code/redundant round-trips possible.

**Not checked:** External Groq API authentication and rate-limiting behaviors with live production keys.
