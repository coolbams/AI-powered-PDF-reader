# Bud

A lightweight PDF ingestion backend that converts PDFs into clean Markdown and structured metadata using FastAPI and PyMuPDF.

## Project Structure

```
Bud/
├── backend/
│   ├── app.py              # FastAPI server & routes
│   ├── Ingestion/
│   │   └── parser.py       # PDF → Markdown conversion
│   └── Media/
│       ├── Uploads/        # Stored PDFs
│       └── Extracts/       # Generated .md and .json files
├── src/bud/__init__.py     # Package entry point
├── pyproject.toml          # Project config & dependencies
└── README.md
```

## How It Works

1. **Upload** — Send a PDF file to `POST /upload`
2. **Parse** — The PDF is converted to Markdown page-by-page using `pymupdf4llm`
3. **Save** — Extracted content is saved to `backend/Media/Extracts/` as:
   - `<filename>.md` — full Markdown of the document
   - `<filename>.json` — per-page text with page numbers
4. **Respond** — Returns the markdown and metadata file paths in JSON

## API Reference

| Method | Endpoint   | Description                        |
|--------|------------|------------------------------------|
| GET    | `/`        | Health check — returns `"Bud's Backend is 200"` |
| POST   | `/upload`  | Upload a PDF for parsing           |

### Error Responses

| Status | Cause |
|--------|-------|
| 400    | File is not a PDF |
| 400    | File is empty |
| 413    | File exceeds 10 MB limit |
| 500    | PDF parsing failed |

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
uv run uvicorn backend.app:app --reload
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
  "saved_to": "backend/Media/Uploads/document.pdf",
  "markdown": "backend/Media/Extracts/document.md",
  "metadata": "backend/Media/Extracts/document.json"
}
```

## Configuration

These values are currently hardcoded in `backend/app.py` and `backend/Ingestion/parser.py`:

| Setting | Default | Location |
|---------|---------|----------|
| Upload directory | `backend/Media/Uploads/` | `app.py` |
| Extracts directory | `backend/Media/Extracts/` | `parser.py` |
| Max file size | 10 MB | `app.py` |
| Allowed extensions | `.pdf` | `app.py` |

## Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi[standard]` | Web framework with automatic OpenAPI docs |
| `pymupdf4llm` | Converts PDF pages to Markdown |

## Development

Run with auto-reload for development:

```bash
uv run uvicorn backend.app:app --reload
```

FastAPI provides interactive API docs at `http://localhost:8000/docs`.

## License

MIT
