# Plan: Supabase pgvector Architecture & Migration

## 1. What is pgvector?

Supabase is built on **PostgreSQL**. The `pgvector` extension adds native support for storing vector embeddings directly inside PostgreSQL tables and performing fast vector similarity search using vector distance operators (like cosine distance `<=>`).

### Current Setup (ChromaDB) vs. Supabase pgvector

| Feature | Local ChromaDB (Current) | Supabase pgvector (Proposed) |
| :--- | :--- | :--- |
| **Where Vectors Live** | Stored in local folder (`Chroma_DB/`) on backend disk | Stored directly in Supabase PostgreSQL (`document_chunks` table) |
| **Server Scaling / Deployment** | Server is stateful. Moving to cloud/Docker requires volume mounts or re-embedding | Server is 100% stateless. Multiple backend instances can query the same vector DB |
| **Unified Transactions** | Documents in Supabase, but vectors on disk (can fall out of sync if deletion fails) | Atomic: deleting a document from `documents` deletes all chunks and vectors automatically (`ON DELETE CASCADE`) |
| **Search Mechanism** | `chromadb.PersistentClient().query()` | `supabase.rpc('match_chunks', {...})` using PostgreSQL HNSW index |
| **Local Disk Footprint** | Hundreds of MBs on local disk | **0 bytes** on local disk |

---

## 2. Technical Design for pgvector

### 2.1 Database Schema & Function

`nomic-ai/nomic-embed-text-v1.5` outputs **768-dimensional** embeddings.

```sql
-- 1. Enable the vector extension in Supabase
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create the document_chunks table
CREATE TABLE IF NOT EXISTS public.document_chunks (
    id TEXT PRIMARY KEY,                       -- e.g. "document_page1_chunk0"
    doc_name TEXT NOT NULL REFERENCES public.documents(filename) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(768),                     -- 768 dimensions for Nomic Embed
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Create HNSW index for ultra-fast cosine similarity search
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding 
ON public.document_chunks 
USING hnsw (embedding vector_cosine_ops);

-- 4. Search RPC function callable from Python
CREATE OR REPLACE FUNCTION match_chunks (
  query_embedding VECTOR(768),
  match_count INT DEFAULT 20,
  filter_doc_name TEXT DEFAULT NULL
)
RETURNS TABLE (
  id TEXT,
  doc_name TEXT,
  page_number INTEGER,
  content TEXT,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    dc.id,
    dc.doc_name,
    dc.page_number,
    dc.content,
    1 - (dc.embedding <=> query_embedding) AS similarity
  FROM public.document_chunks dc
  WHERE filter_doc_name IS NULL OR dc.doc_name = filter_doc_name
  ORDER BY dc.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
```

---

## 3. Impact on Backend Code

```mermaid
flowchart TD
    subgraph Current Architecture
        A1[Upload PDF] --> B1[Write to Media/Uploads]
        B1 --> C1[Write to Media/Extracts]
        C1 --> D1[ChromaDB SQLite on Disk]
    end

    subgraph Supabase-Native Architecture
        A2[Upload PDF] --> B2[Supabase Storage: pdfs/, markdown/, extracts/]
        B2 --> C2[Supabase DB: documents table]
        C2 --> D2[Supabase pgvector: document_chunks table]
    end
```

### Modules to Modify:
1. **`core/embeddings.py`**:
   - Keep `EmbeddingModel` (using `SentenceTransformer` to encode `search_document:` and `search_query:` into 768-dim float lists).
   - Update `embed(chunks, filename)`: Instead of inserting into ChromaDB client, upserts rows with `embedding` list into `document_chunks` table via Supabase client:
     ```python
     client.table("document_chunks").upsert(rows).execute()
     ```
   - ChromaDB client dependency can be deprecated.
2. **`core/retrieval.py`**:
   - Call the `match_chunks` RPC function:
     ```python
     res = client.rpc("match_chunks", {
         "query_embedding": query_embedding,
         "match_count": top_k,
         "filter_doc_name": doc_name
     }).execute()
     ```
   - Formats candidate chunks for cross-encoder reranking (`core/reranker.py`).
3. **`pyproject.toml`**:
   - `chromadb` can eventually be removed from dependencies (reducing build size and eliminating C++ SQLite compile overhead).

---

## 4. Verification Plan

1. Execute the pgvector SQL in Supabase SQL editor.
2. Embed test chunks and verify similarity search via `client.rpc("match_chunks", ...)`.
3. Run the full unit test suite with mock RPC calls to confirm tests pass without external dependencies.
4. Verify `/ask` and `/ask/stream` return accurate responses with sources.

---

## 5. Next Decision For You

- **Option A (Full Supabase Unification)**: Implement `pgvector` so 100% of data (files, metadata, and vectors) lives in Supabase, completely eliminating local ChromaDB and `Media/`.
- **Option B (Hybrid)**: Store files and metadata in Supabase, but keep vector search in local ChromaDB.
