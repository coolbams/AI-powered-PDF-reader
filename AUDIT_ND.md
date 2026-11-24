# Codebase Audit

What this repo does: Bud uploads PDFs, extracts and indexes their text, then answers questions with a language model. I assumed one backend instance serving several users; the repository does not show how it is deployed.

## Must fix

1. *- SKIP -* **Anyone who can reach the API can use it** (`backend/app.py:L34-L35`, `backend/app.py:L49-L71`)
   - **What this is:** The API accepts uploads, serves stored files, and makes paid model requests.
   - **Problem:** There is no authentication or rate limit, and cross-origin access defaults to `*`. If the server is reachable on a network, anyone can use those endpoints and consume your Groq quota.
   - **Fix:** Keep the service bound to localhost if it is only for local use. For shared or public use, add authentication and rate limits, and restrict allowed origins.
   - **If we skip it:** Unintended users can access stored documents or run up API usage.

2. **PDF text can become executable browser content** (`frontend/src/components/PDFFileReader.jsx:L412,L437`, `frontend/src/components/ChatbotPane.jsx:L174`)
   - **What this is:** The app renders parsed PDF text and model replies as HTML.
   - **Problem:** `marked.parse` output goes into `dangerouslySetInnerHTML` without sanitizing HTML. A PDF containing HTML markup can execute script in a viewer’s browser when its Markdown preview is opened.
   - **Fix:** Sanitize the rendered HTML with a maintained HTML sanitizer before inserting it, or disable raw HTML in Markdown.
   - **If we skip it:** Opening a malicious document can run unwanted code in the app.

3. **The upload limit is checked after the whole file is read** (`backend/core/orchestrator.py:L27-L30`)
   - **What this is:** Uploads have a stated 20 MB limit.
   - **Problem:** `file.read()` loads the complete upload before checking its size. Large or concurrent uploads can consume substantial server memory before they are rejected.
   - **Fix:** Read in bounded chunks and stop once the limit is exceeded.
   - **If we skip it:** Large uploads can exhaust memory and make the service unavailable.

4. **Debug mode can expose error details** (`backend/app.py:L32`)
   - **What this is:** FastAPI debug mode returns detailed tracebacks for unhandled errors.
   - **Problem:** If this app is deployed beyond a developer’s machine, a failing request can reveal internal paths and code details to its caller.
   - **Fix:** Disable debug mode for deployed environments.
   - **If we skip it:** Errors may disclose implementation details to users who should not see them.

## Should fix

5. **Re-uploading a shorter PDF leaves stale search results** (`backend/core/embeddings.py:L68-L70,L99-L103`)
   - **What this is:** Chunk IDs are based on the document name, page, and chunk index; embedding uses `upsert`.
   - **Problem:** If a replacement PDF has fewer chunks, `upsert` updates matching IDs but does not remove old trailing IDs. Queries can then return text from the previous version.
   - **Fix:** After successfully indexing the replacement, remove obsolete chunk IDs for that document.
   - **If we skip it:** Answers may cite content that is no longer in the uploaded PDF.

6. **A question can block other API requests** (`backend/app.py:L60-L63`)
   - **What this is:** The asynchronous `/ask` handler calls synchronous retrieval and model-generation code.
   - **Problem:** While those calls run, they block the server’s event loop—the part that schedules other requests. A slow model response can stall uploads and other users’ questions.
   - **Fix:** Make the route synchronous (`def`) so FastAPI runs it in its thread pool, or explicitly offload the blocking work.
   - **If we skip it:** Concurrent users can experience long stalls even when their requests do not need the model.

## Nice to have

7. **The configured model name is ignored** (`backend/.env.example:L3-L4`, `backend/core/generate.py:L44,L61`)
   - **What this is:** The example environment file exposes an `LLM` setting.
   - **Problem:** Both generation paths hardcode the model name, so changing `LLM` has no effect.
   - **Fix:** Read the setting from the environment, or remove it from the documented configuration.
   - **If we skip it:** Operators may believe they changed models when the app is still using the hardcoded one.

8. **The initial frontend bundle is large** (frontend production build)
   - **What this is:** The build produces a roughly 979 kB JavaScript chunk (about 302 kB compressed).
   - **Problem:** Every user downloads the PDF-viewer code even before opening a document.
   - **Fix:** Load the PDF viewer on demand.
   - **If we skip it:** Initial page loads remain heavier than needed.

**Verdict:** Fix API access controls and unsanitized HTML first; address upload memory use before exposing the service to multiple users.

**Not checked:** Live Groq, model-download, and ChromaDB behavior; deployment and network configuration. The backend’s 25 unit tests and frontend lint/build pass; the build reports the large-chunk warning above.
