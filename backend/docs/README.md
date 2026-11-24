# Project Documentation & Architecture Artifacts

This folder contains all technical design documents, architectural decisions, memory benchmarks, and implementation logs developed for Bud's PDF Reader backend.

---

## 📑 Table of Contents

| Document | Description | Status |
| :--- | :--- | :--- |
| [**`walkthrough.md`**](./walkthrough.md) | Summary of changes, components, and verification results (62/62 tests passing). | ✅ Completed |
| [**`implementation_todo.md`**](./implementation_todo.md) | 10-step sequential checklist tracking execution from staging buffer to test verification. | ✅ 10/10 Complete |
| [**`staged_scratch_sync_pipeline.md`**](./staged_scratch_sync_pipeline.md) | Complete architectural design for the staged scratch buffer and resilient Supabase sync. | Approved & Implemented |
| [**`memory_analysis_and_optimization_plan.md`**](./memory_analysis_and_optimization_plan.md) | Deep memory analysis (PyMuPDF C-heap, PyTorch embeddings) for large (30MB / 400-page) PDFs. | Reference / Benchmark |
| [**`supabase_as_primary_pipeline.md`**](./supabase_as_primary_pipeline.md) | Strategy for decommissioning local `Media/` storage and using Supabase as primary catalog. | Approved & Implemented |
| [**`resumable_packet_upload_plan.md`**](./resumable_packet_upload_plan.md) | Exploration of streaming packets vs. staged scratch buffer sync under flaky networks. | Analysis / Discussion |
| [**`pgvector_integration_plan.md`**](./pgvector_integration_plan.md) | Comparison between Supabase pgvector and ChromaDB vector search. | ChromaDB Retained |
| [**`supabase_integration_plan.md`**](./supabase_integration_plan.md) | Initial integration roadmap for Supabase Storage and PostgreSQL document catalog. | Initial Spec |

---

## 🛠 Architecture Summary

```mermaid
flowchart TD
    Client["Client (Upload PDF)"] -->|Stream chunks <= 50MB| Orch["core/orchestrator.py"]
    Orch -->|Write to disk| Staging["Staging/<doc_id>/<br/>(state.json, PDF)"]
    
    Staging --> Parser["core/parser.py<br/>(PyMuPDF extract + doc.close())"]
    Parser -->|Write extracts| DiskExtracts["Staging/<doc_id>/<br/>(.md, pages.json, chunks.json)"]
    Parser -->|Embed chunks| Chroma[("Local ChromaDB")]
    
    DiskExtracts --> Sync["core/supabase_sync.py<br/>(Tenacity Exponential Retry)"]
    Sync -->|1. Upload PDF| S1[("Supabase Storage: pdfs/")]
    Sync -->|2. Upload Markdown| S2[("Supabase Storage: markdown/")]
    Sync -->|3. Upload Extracts| S3[("Supabase Storage: extracts/")]
    Sync -->|4. Upload Chunks| S4[("Supabase Storage: chunks/")]
    Sync -->|5. Commit Metadata| DB[("Supabase PostgreSQL: documents")]
    
    DB -->|Confirmed| Cleanup["Delete Staging/<doc_id>/"]
    
    subgraph Recovery["Startup Recovery"]
        Lifespan["FastAPI Lifespan Startup"] -->|Scan incomplete jobs| Scan["list_incomplete_jobs()"]
        Scan -->|Resume from checkpoint| Sync
    end
```
