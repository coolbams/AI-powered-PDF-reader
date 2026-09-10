# Bud ✨✨🖥️

A lightweight PDF ingestion backend that converts PDFs into clean Markdown, chunks the text, and embeds it into a vector database using FastAPI, PyMuPDF, and ChromaDB.

## Architecture

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌───────────┐     ┌──────────┐     ┌──────────┐
│  Upload   │────▶│  Parse   │────▶│  Chunk   │────▶│   Embed   │────▶│  Store   │────▶│ Retrieve │
│  (PDF)    │     │ (Markdown)│     │ (Splits) │     │ (Vectors) │     │ (ChromaDB)│     │ (Search) │
└──────────┘     └──────────┘     └──────────┘     └───────────┘     └──────────┘     └──────────┘
     │                │                │                  │                │                │
     ▼                ▼                ▼                  ▼                ▼                ▼
  app.py          parser.py       chunker.py        embeddings.py     Chroma_DB/      retrieval.py
```

## Project Structure

```
Bud/
├── src/
│   ├── bud/
│   │   └── __init__.py         # Package entry point
│   └── backend/
│       ├── __init__.py
│       ├── app.py              # FastAPI server & routes
│       ├── Ingestion/
│       │   ├── __init__.py
│       │   ├── parser.py       # PDF → Markdown + metadata + chunks
│       │   ├── chunker.py      # Text splitting into chunks
│       │   └── embeddings.py   # ChromaDB vector store + embeddings
│       ├── Retrieval/
│       │   ├── __init__.py
│       │   └── retrieval.py    # Semantic search over embedded chunks
│       └── Media/
│           ├── Uploads/        # Stored PDFs
│           └── Extracts/       # Generated .md, .json, and _chunks.json files
├── pyproject.toml              # Project config & dependencies
├── uv.lock                     # Dependency lock file
└── README.md
```

## How It Works

1. **Upload** — Send a PDF file to `POST /upload`
2. **Parse** — The PDF is converted to Markdown page-by-page using `pymupdf4llm`
3. **Chunk** — Text is split into overlapping chunks using `RecursiveCharacterTextSplitter`
4. **Embed** — Chunks are embedded using `sentence-transformers` and stored in ChromaDB
5. **Save** — Extracted content is saved to `src/backend/Media/Extracts/` as:
   - `<filename>.md` — full Markdown of the document
   - `<filename>.json` — per-page text with page numbers
   - `<filename>_chunks.json` — text chunks with page metadata
6. **Respond** — Returns the markdown, metadata, and chunks file paths in JSON

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

| Method | Endpoint   | Description                        |
|--------|------------|------------------------------------|
| GET    | `/`        | Health check — returns `"Bud's Backend is 200"` |
| POST   | `/upload`  | Upload a PDF for parsing           |
| POST   | `/ask`     | Query the vector store             |

### Error Responses

| Status | Cause |
|--------|-------|
| 400    | File is not a PDF |
| 400    | File is empty |
| 413    | File exceeds 10 MB limit |
| 500    | PDF parsing/embedding failed |

## Setup

### Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager

### Install dependencies

```bash
uv sync
```

### Run the server

```bash
uv run uvicorn src.backend.app:app --reload
```

The server starts at `http://localhost:8000`.

### Upload a PDF

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

## Querying the Vector Store

### Via API

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"request": "What are the four laws of behavior change?"}'
```

**Response:**
```json
{
  "query": "What are the four laws of behavior change?",
  "results": [
    {
      "text": "The Four Laws of Behavior Change provide a simple set of rules...",
      "metadata": {"page_number": 5},
      "id": "document_page5_chunk3",
      "distance": 0.342
    }
  ]
}
```

### Via Python

```python
from backend.Ingestion.embeddings import embeder

query = "What are the four laws of behavior change?"
query_embedding = embeder.embed_query(query)

# Use query_embedding to search ChromaDB collection
```

## Configuration

These values are currently hardcoded:

| Setting | Default | Location |
|---------|---------|----------|
| Upload directory | `src/backend/Media/Uploads/` | `app.py` |
| Extracts directory | `src/backend/Media/Extracts/` | `parser.py` |
| Max file size | 10 MB | `app.py` |
| Allowed extensions | `.pdf` | `app.py` |
| Chunk size | 1000 | `chunker.py` |
| Chunk overlap | 200 | `chunker.py` |
| Embedding model | `nomic-ai/nomic-embed-text-v1.5` | `embeddings.py` |
| ChromaDB path | `src/backend/Chroma_DB/` | `embeddings.py` |

## Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi[standard]` | Web framework with automatic OpenAPI docs |
| `pymupdf4llm` | Converts PDF pages to Markdown |
| `langchain-text-splitters` | Splits text into overlapping chunks |
| `sentence-transformers` | Generates embeddings for vector storage |
| `huggingface-hub` | Model hosting for sentence-transformers |
| `chromadb` | Vector database for storing embeddings |

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

### ChromaDB data persists between runs

ChromaDB stores data in `src/backend/Chroma_DB/`. To reset the vector store, delete this directory:

```bash
rm -rf src/backend/Chroma_DB/
```

### Duplicate upload errors

If you upload the same PDF twice, ChromaDB will error due to duplicate IDs. Delete the existing collection or use a different filename.

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
| RAG response generation | 🔲 WIP |

## Development

Run with auto-reload for development:

```bash
uv run uvicorn src.backend.app:app --reload
```

FastAPI provides interactive API docs at `http://localhost:8000/docs`.

## License

MIT
