-- ============================================================
-- H-RAG Fix: Replace IVFFlat indexes with HNSW
-- Run this in Supabase SQL Editor to fix the 0-results issue
-- ============================================================

-- Drop the broken IVFFlat indexes (created on empty tables)
DROP INDEX IF EXISTS idx_folder_summaries_embedding;
DROP INDEX IF EXISTS idx_doc_summaries_embedding;
DROP INDEX IF EXISTS idx_chunks_embedding;

-- Recreate with HNSW (works correctly regardless of insert order)
CREATE INDEX idx_folder_summaries_embedding
    ON hrag_folder_summaries
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX idx_doc_summaries_embedding
    ON hrag_doc_summaries
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX idx_chunks_embedding
    ON hrag_chunks
    USING hnsw (embedding vector_cosine_ops);
