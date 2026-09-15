# Bud

A lightweight RAG (Retrieval-Augmented Generation) app that ingests PDFs, embeds them into a vector database, and generates answers to questions using an LLM. Includes a Streamlit frontend for interacting with the system.

## Architecture

```
                               INGESTION
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌───────────┐     ┌──────────┐
│  Upload   │────▶│  Parse   │────▶│  Chunk   │────▶│   Embed   │────▶│  Store   │
│  (PDF)    │     │ (Markdown)│     │ (Splits) │     │ (Vectors) │     │ (ChromaDB)│
└──────────┘     └──────────┘     └──────────┘     └───────────┘     └──────────┘
                                                                   │
                              RETRIEVAL & GENERATION               │
┌──────────┐     ┌──────────────┐     ┌───────────┐               │
│  Query   │────▶│   Retrieve   │◀────│  Search   │◀──────────────┘
│ (user)   │     │   (Chunks)   │     │ (Embed)   │
└──────────┘     └──────┬───────┘     └───────────┘
                        │
                        ▼
               ┌──────────────┐     ┌───────────┐
               │ Build Prompt │────▶│ Generate  │────▶ Response (LLM)
               │              │     │  (Groq)   │
               └──────────────┘     └───────────┘
```

## Project Structure

```
Bud/
├── .env                        # API keys (gitignored)
├── .env.example                # Example environment config
├── src/
│   ├── bud/
│   │   └── __init__.py         # Package entry point
│   ├── backend/
│   │   ├── __init__.py
│   │   ├── app.py              # FastAPI server & routes
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py # Centralizes upload, process, query logic
│   │   │   ├── parser.py       # PDF → Markdown + metadata + chunks
│   │   │   ├── chunker.py      # Text splitting into chunks
│   │   │   ├── embeddings.py   # ChromaDB vector store + embeddings
│   │   │   ├── retrieval.py    # Semantic search over embedded chunks
│   │   │   ├── prompt_builder.py # Builds prompts from retrieved chunks
│   │   │   └── generate.py     # LLM response generation via Groq
│   │   └── Media/
│   │       ├── Uploads/        # Stored PDFs
│   │       └── Extracts/       # Generated .md, .json, and _chunks.json files
│   └── frontend/
│       ├── __init__.py
│       ├── ui.py               # Streamlit app entry point
│       ├── sidebar.py          # File uploader
│       ├── leftpanel.py        # PDF preview
│       └── rightpanel.py       # Chat/query input
├── pyproject.toml              # Project config & dependencies
├── uv.lock                     # Dependency lock file
└── README.md
```

## How It Works

### Ingestion Pipeline

1. **Upload** — Send a PDF file to `POST /upload` (or via the frontend sidebar)
2. **Parse** — The PDF is converted to Markdown page-by-page using `pymupdf4llm`
3. **Chunk** — Text is split into overlapping chunks using `RecursiveCharacterTextSplitter`
4. **Embed** — Chunks are embedded using `sentence-transformers` (nomic-embed-text-v1.5)
5. **Store** — Vectors are stored in ChromaDB for semantic search
6. **Save** — Extracted content is saved to `src/backend/Media/Extracts/` as:
   - `<filename>.md` — full Markdown of the document
   - `<filename>.json` — per-page text with page numbers
   - `<filename>_chunks.json` — text chunks with page metadata

### Query Pipeline

1. **Query** — User sends a question to `POST /ask` (or via the frontend chat)
2. **Embed Query** — The question is embedded using the same model
3. **Search** — ChromaDB finds the most relevant chunks (top 5 by default)
4. **Build Prompt** — Retrieved chunks are formatted into a context-aware prompt
5. **Generate** — The prompt is sent to Groq's LLM for response generation
6. **Respond** — Returns the generated answer

## Output Formats

### `<filename>.json` — Page metadata

```json
[
  {
    "page_number": 1,
    "text": "Atomic Habits by James Clear..."
  },
  {
    "page_number": 2,
    "text": "The habits that..."
  }
]
```

### `<filename>_chunks.json` — Text chunks

```json
[
  {
    "text": "An atomic habit is a regular practice or routine that is small and easy to do...",
    "metadata": {
      "page_number": 1
    }
  },
  {
    "text": "The Four Laws of Behavior Change provide a simple set of rules...",
    "metadata": {
      "page_number": 5
    }
  }
]
```

## API Reference

| Method | Endpoint   | Description                                          |
|--------|------------|------------------------------------------------------|
| GET    | `/`        | Health check — returns `"Bud's Backend is 200"`      |
| POST   | `/upload`  | Upload a PDF for parsing and embedding               |
| POST   | `/ask`     | Ask a question about uploaded documents              |

### Error Responses

| Status | Cause |
|--------|-------|
| 400    | File is not a PDF |
| 400    | File is empty |
| 413    | File exceeds 20 MB limit |
| 500    | PDF parsing/embedding failed |

## Setup

### Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager
- A [Groq API key](https://console.groq.com/)

### Install dependencies

```bash
uv sync
```

### Configure environment

Copy the example env file and add your API key:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# LLM Model
LLM="openai/gpt-oss-20b"

# Embedding Model
EMBEDDING_MODEL="nomic-ai/nomic-embed-text-v1.5"

# Groq API key
GROQ_API_KEY=your_groq_api_key_here
```

### Run the backend

```bash
uv run uvicorn src.backend.app:app --reload
```

The backend starts at `http://localhost:8000`.

### Run the frontend

```bash
uv run streamlit run src/frontend/ui.py
```

The frontend starts at `http://localhost:8501`.

### Upload a PDF (API)

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@document.pdf"
```

**Response:**
```json
{
  "filename": "document.pdf",
  "content_type": "application/pdf",
  "saved_to": "src/backend/Media/Uploads/document.pdf",
  "markdown": "src/backend/Media/Extracts/document.md",
  "metadata": "src/backend/Media/Extracts/document.json",
  "chunks": "src/backend/Media/Extracts/document_chunks.json"
}
```

### Ask a question (API)

```bash
curl -X POST "http://localhost:8000/ask?request=What%20are%20the%20four%20laws%20of%20behavior%20change?"
```

**Response:**
```json
{
  "query": "What are the four laws of behavior change?",
  "results": "The Four Laws of Behavior Change are: 1) Make it obvious, 2) Make it attractive, 3) Make it easy, 4) Make it satisfying."
}
```

## Frontend

The Streamlit frontend provides a UI for interacting with Bud:

| Component | File | Description |
|-----------|------|-------------|
| **Sidebar** | `sidebar.py` | Upload PDF files |
| **Left Panel** | `leftpanel.py` | Preview uploaded PDFs |
| **Right Panel** | `rightpanel.py` | Ask questions and view responses |

## Configuration

### Hardcoded Settings

| Setting | Default | Location |
|---------|---------|----------|
| Upload directory | `src/backend/Media/Uploads/` | `orchestrator.py` |
| Extracts directory | `src/backend/Media/Extracts/` | `parser.py` |
| Max file size | 20 MB | `orchestrator.py` |
| Allowed extensions | `.pdf` | `orchestrator.py` |
| Chunk size | 2000 | `chunker.py` |
| Chunk overlap | 400 | `chunker.py` |
| Embedding model | `nomic-ai/nomic-embed-text-v1.5` | `embeddings.py` |
| ChromaDB path | `src/backend/Chroma_DB/` | `embeddings.py` |
| LLM model | `openai/gpt-oss-20b` | `generate.py` |
| LLM temperature | 0.3 | `generate.py` |
| LLM max tokens | 4000 | `generate.py` |
| Search results | 5 (top_k) | `retrieval.py` |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | API key for Groq LLM services |
| `EMBEDDING_MODEL` | No | Embedding model name (default: `nomic-ai/nomic-embed-text-v1.5`) |
| `LLM` | No | LLM model name (default: `openai/gpt-oss-20b`) |

## Dependencies

### Backend

| Package | Purpose |
|---------|---------|
| `fastapi[standard]` | Web framework with automatic OpenAPI docs |
| `pymupdf4llm` | Converts PDF pages to Markdown |
| `langchain-text-splitters` | Splits text into overlapping chunks |
| `sentence-transformers` | Generates embeddings for vector storage |
| `huggingface-hub` | Model hosting for sentence-transformers |
| `chromadb` | Vector database for storing embeddings |
| `groq` | LLM API for response generation |
| `python-dotenv` | Loads environment variables from `.env` |

### Frontend

| Package | Purpose |
|---------|---------|
| `streamlit` | Web UI framework |

## Embedding Model

Bud uses [nomic-embed-text-v1.5](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5) for generating embeddings:

- **Dimensions:** 768
- **Max tokens:** 8192
- **Type:** Open-source, production-ready embedding model
- **Prefixes:** Uses `search_document:` for indexing and `search_query:` for retrieval

The model is downloaded and cached locally on first run in `src/backend/Embedding_Model/`.

## Troubleshooting

### First run is slow

The first time you upload a PDF, the embedding model (~500MB) is downloaded from HuggingFace. Subsequent runs use the cached model.

### Model download fails

If you're behind a firewall or have limited bandwidth, you can manually download the model:

```python
from sentence_transformers import SentenceTransformer
SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)
```

### Groq API errors

Ensure your `GROQ_API_KEY` is set correctly in the `.env` file. Get a free key at [console.groq.com](https://console.groq.com/).

### ChromaDB data persists between runs

ChromaDB stores data in `src/backend/Chroma_DB/`. To reset the vector store, delete this directory:

```bash
rm -rf src/backend/Chroma_DB/
```

### Duplicate upload errors

If you upload the same PDF twice, ChromaDB will error due to duplicate IDs. Delete the existing collection or use a different filename.

## Limitations

| Limitation | Description |
|------------|-------------|
| **No duplicate uploads** | Uploading the same PDF twice causes a ChromaDB `UniqueConstraintError`. There is no upsert or deduplication logic. |
| **PDF only** | Only `.pdf` files are accepted. No support for DOCX, TXT, or other formats. |
| **Single collection** | All documents are stored in one ChromaDB collection (`my_embedded_pdfs`). No per-document or per-user isolation. |
| **No streaming** | The `/ask` endpoint returns the full response at once. No streaming support for long answers. |
| **Synchronous embedding** | The embedding model runs synchronously and blocks the event loop during uploads. |

## Project Status

| Feature | Status |
|---------|--------|
| PDF upload & parsing | ✅ Done |
| Markdown extraction | ✅ Done |
| Page-level metadata | ✅ Done |
| Text chunking | ✅ Done |
| Embedding generation | ✅ Done |
| ChromaDB storage | ✅ Done |
| Query/retrieval | ✅ Done |
| RAG response generation | ✅ Done |
| Streamlit frontend | ✅ Done |

## Development

### Backend

```bash
uv run uvicorn src.backend.app:app --reload
```

FastAPI provides interactive API docs at `http://localhost:8000/docs`.

### Frontend

```bash
uv run streamlit run src/frontend/ui.py
```

## License

MIT
