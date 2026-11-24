-- Supabase SQL Schema for Bud PDF Reader
-- Run this in your Supabase SQL Editor: Dashboard -> SQL Editor -> New Query

-- 1. Create documents tracking table
CREATE TABLE IF NOT EXISTS public.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL UNIQUE,
    title TEXT,
    file_path TEXT NOT NULL,         -- Path in Supabase bucket, e.g. "pdfs/sample.pdf"
    markdown_path TEXT,              -- Path in bucket, e.g. "markdown/sample.md"
    json_extract_path TEXT,          -- Path in bucket, e.g. "extracts/sample.json"
    chunks_path TEXT,                -- Path in bucket, e.g. "chunks/sample_chunks.json"
    file_size_bytes BIGINT DEFAULT 0,
    page_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'processed', -- 'processing', 'processed', 'error'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast filename lookups
CREATE INDEX IF NOT EXISTS idx_documents_filename ON public.documents(filename);

-- 2. Create the storage bucket 'pdf-reader' (if not already existing)
INSERT INTO storage.buckets (id, name, public)
VALUES ('pdf-reader', 'pdf-reader', true)
ON CONFLICT (id) DO NOTHING;

-- 3. Storage Policies (Adjust as needed for public read or authenticated access)
-- Allow public access to view/download files from the pdf-reader bucket
CREATE POLICY "Public Read Access"
ON storage.objects FOR SELECT
USING (bucket_id = 'pdf-reader');

-- Allow service role or authenticated uploads
CREATE POLICY "Public/Service Upload Access"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'pdf-reader');

CREATE POLICY "Public/Service Update Access"
ON storage.objects FOR UPDATE
USING (bucket_id = 'pdf-reader');

CREATE POLICY "Public/Service Delete Access"
ON storage.objects FOR DELETE
USING (bucket_id = 'pdf-reader');
