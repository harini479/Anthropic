-- ============================================================
-- H-RAG Migration: Add Multi-Node Support
-- Run this in your Supabase SQL Editor
-- ============================================================

-- 1. Add node column to all existing tables (default to 'anthropic' to preserve existing data)
ALTER TABLE hrag_collection_summaries ADD COLUMN IF NOT EXISTS node TEXT DEFAULT 'anthropic';
ALTER TABLE hrag_folder_summaries ADD COLUMN IF NOT EXISTS node TEXT DEFAULT 'anthropic';
ALTER TABLE hrag_doc_summaries ADD COLUMN IF NOT EXISTS node TEXT DEFAULT 'anthropic';
ALTER TABLE hrag_chunks ADD COLUMN IF NOT EXISTS node TEXT DEFAULT 'anthropic';

-- 2. Create indexes on the node column for fast filtering
CREATE INDEX IF NOT EXISTS idx_coll_node ON hrag_collection_summaries(node);
CREATE INDEX IF NOT EXISTS idx_folder_node ON hrag_folder_summaries(node);
CREATE INDEX IF NOT EXISTS idx_doc_node ON hrag_doc_summaries(node);
CREATE INDEX IF NOT EXISTS idx_chunks_node ON hrag_chunks(node);

-- 3. Create Multi-Node RPC functions
-- ──────────────────────────────────────────────────────────────

-- Search folder summaries across multiple nodes
CREATE OR REPLACE FUNCTION match_folder_summaries_multi(
    query_embedding VECTOR(1536),
    nodes TEXT[],
    match_count INT DEFAULT 2
)
RETURNS TABLE (
    id TEXT,
    folder_path TEXT,
    content TEXT,
    metadata JSONB,
    node TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        fs.id,
        fs.folder_path,
        fs.content,
        fs.metadata,
        fs.node,
        1 - (fs.embedding <=> query_embedding) AS similarity
    FROM hrag_folder_summaries fs
    WHERE fs.node = ANY(nodes)
    ORDER BY fs.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Search document summaries across multiple nodes, filtered by folders
CREATE OR REPLACE FUNCTION match_doc_summaries_multi(
    query_embedding VECTOR(1536),
    nodes TEXT[],
    filter_folder_paths TEXT[],
    match_count INT DEFAULT 3
)
RETURNS TABLE (
    id TEXT,
    folder_path TEXT,
    file_path TEXT,
    content TEXT,
    metadata JSONB,
    node TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ds.id,
        ds.folder_path,
        ds.file_path,
        ds.content,
        ds.metadata,
        ds.node,
        1 - (ds.embedding <=> query_embedding) AS similarity
    FROM hrag_doc_summaries ds
    WHERE ds.node = ANY(nodes) AND ds.folder_path = ANY(filter_folder_paths)
    ORDER BY ds.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Search chunks across multiple nodes, filtered by file paths
CREATE OR REPLACE FUNCTION match_chunks_multi(
    query_embedding VECTOR(1536),
    nodes TEXT[],
    filter_file_paths TEXT[],
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id TEXT,
    doc_id TEXT,
    folder_path TEXT,
    file_path TEXT,
    content TEXT,
    metadata JSONB,
    node TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.doc_id,
        c.folder_path,
        c.file_path,
        c.content,
        c.metadata,
        c.node,
        1 - (c.embedding <=> query_embedding) AS similarity
    FROM hrag_chunks c
    WHERE c.node = ANY(nodes) AND c.file_path = ANY(filter_file_paths)
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
