# Bud - Backend

FastAPI RAG (Retrieval-Augmented Generation) backend service for document ingestion, semantic search with ChromaDB, cross-encoder re-ranking, and Groq LLM response generation.

## Features

- **Document Ingestion**: Extracts text & markdown from PDF documents using `pymupdf4llm`.
- **Text Chunking**: Configurable chunk size and overlap using LangChain's `RecursiveCharacterTextSplitter`.
- **Vector Storage**: Embeds chunks using `sentence-transformers` (`nomic-ai/nomic-embed-text-v1.5`) stored persistently in `ChromaDB`.
- **Dense Search & Re-Ranking**: ChromaDB similarity search combined with a cross-encoder model (`ms-marco-MiniLM-L-6-v2`) for reranking candidate chunks.
- **LLM Generation**: Streams tokens and sources using Groq API (`openai/gpt-oss-20b`) via Server-Sent Events (SSE).

## Requirements

- Python 3.14+
- [`uv`](https://docs.astral.sh/uv/) (recommended) or `pip`

## Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Configure your environment variables in `.env`:
   - `GROQ_API_KEY`: Your Groq API key
   - `LLM`: `openai/gpt-oss-20b`
   - `EMBEDDING_MODEL`: `nomic-ai/nomic-embed-text-v1.5`

3. Install dependencies:
   ```bash
   uv sync
   # or with pip:
   # pip install -e .
   ```

## Running the Server

Start the FastAPI server:

```bash
uv run uvicorn app:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.
Interactive Swagger API documentation is available at `http://localhost:8000/docs`.

## API Endpoints

- `GET /` — Health check
- `POST /upload` — Upload a PDF file for parsing and embedding
- `POST /ask` — Query uploaded documents (synchronous)
- `POST /ask/stream` — Query uploaded documents (SSE token streaming)
- `GET /list_files` — List uploaded PDFs
- `GET /files/{filename}` — Preview / stream a PDF document
