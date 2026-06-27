-- ============================================================
-- H-RAG Supabase Setup Script
-- Run this in your Supabase SQL Editor (Dashboard → SQL Editor)
-- ============================================================

-- 1. Enable the pgvector extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;


-- 2. Create the 4 hierarchy tables
-- ──────────────────────────────────────────────────────────────

-- Level 0: Collection summaries (top-level, typically just 1 row)
CREATE TABLE IF NOT EXISTS hrag_collection_summaries (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    embedding VECTOR(1536),  -- text-embedding-3-small dimension
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Level 1: Folder summaries
CREATE TABLE IF NOT EXISTS hrag_folder_summaries (
    id TEXT PRIMARY KEY,
    folder_path TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1536),
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Level 2: Document summaries
CREATE TABLE IF NOT EXISTS hrag_doc_summaries (
    id TEXT PRIMARY KEY,
    folder_path TEXT NOT NULL,
    file_path TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1536),
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Level 3: Document chunks (the most granular level)
CREATE TABLE IF NOT EXISTS hrag_chunks (
    id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    folder_path TEXT NOT NULL,
    file_path TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1536),
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);


-- 3. Create indexes for fast vector similarity search
-- ──────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_folder_summaries_embedding
    ON hrag_folder_summaries
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_doc_summaries_embedding
    ON hrag_doc_summaries
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_chunks_embedding
    ON hrag_chunks
    USING hnsw (embedding vector_cosine_ops);

-- Additional indexes for filtered queries
CREATE INDEX IF NOT EXISTS idx_doc_summaries_folder
    ON hrag_doc_summaries (folder_path);

CREATE INDEX IF NOT EXISTS idx_chunks_folder
    ON hrag_chunks (folder_path);

CREATE INDEX IF NOT EXISTS idx_chunks_file
    ON hrag_chunks (file_path);

CREATE INDEX IF NOT EXISTS idx_chunks_doc_id
    ON hrag_chunks (doc_id);


-- 4. Create RPC functions for vector similarity search
-- ──────────────────────────────────────────────────────────────

-- Search folder summaries by cosine similarity
CREATE OR REPLACE FUNCTION match_folder_summaries(
    query_embedding VECTOR(1536),
    match_count INT DEFAULT 2
)
RETURNS TABLE (
    id TEXT,
    folder_path TEXT,
    content TEXT,
    metadata JSONB,
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
        1 - (fs.embedding <=> query_embedding) AS similarity
    FROM hrag_folder_summaries fs
    ORDER BY fs.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;


-- Search document summaries filtered by folder paths
CREATE OR REPLACE FUNCTION match_doc_summaries(
    query_embedding VECTOR(1536),
    filter_folder_paths TEXT[],
    match_count INT DEFAULT 3
)
RETURNS TABLE (
    id TEXT,
    folder_path TEXT,
    file_path TEXT,
    content TEXT,
    metadata JSONB,
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
        1 - (ds.embedding <=> query_embedding) AS similarity
    FROM hrag_doc_summaries ds
    WHERE ds.folder_path = ANY(filter_folder_paths)
    ORDER BY ds.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;


-- Search chunks filtered by file paths
CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding VECTOR(1536),
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
        1 - (c.embedding <=> query_embedding) AS similarity
    FROM hrag_chunks c
    WHERE c.file_path = ANY(filter_file_paths)
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;


-- 5. Enable Row Level Security (optional but recommended)
-- ──────────────────────────────────────────────────────────────

ALTER TABLE hrag_collection_summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE hrag_folder_summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE hrag_doc_summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE hrag_chunks ENABLE ROW LEVEL SECURITY;

-- Allow service role full access (your SUPABASE_SERVICE_KEY uses this role)
CREATE POLICY "Service role access" ON hrag_collection_summaries
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role access" ON hrag_folder_summaries
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role access" ON hrag_doc_summaries
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role access" ON hrag_chunks
    FOR ALL USING (true) WITH CHECK (true);
