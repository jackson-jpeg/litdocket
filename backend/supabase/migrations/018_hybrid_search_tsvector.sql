-- Migration: Add tsvector column for BM25-style full-text search (hybrid search)
-- This enables combining semantic search (pgvector) with keyword search (PostgreSQL FTS)
-- Formula: hybrid_score = alpha * semantic + (1-alpha) * bm25

-- Add tsvector column for BM25-style full-text search
ALTER TABLE document_embeddings
ADD COLUMN IF NOT EXISTS chunk_text_search tsvector;

-- Populate from existing chunk_text
UPDATE document_embeddings
SET chunk_text_search = to_tsvector('english', COALESCE(chunk_text, ''))
WHERE chunk_text_search IS NULL;

-- Create GIN index for fast full-text search
CREATE INDEX IF NOT EXISTS idx_chunk_text_search_gin
ON document_embeddings USING GIN (chunk_text_search);

-- Auto-update trigger function
CREATE OR REPLACE FUNCTION update_chunk_text_search()
RETURNS TRIGGER AS $$
BEGIN
    NEW.chunk_text_search := to_tsvector('english', COALESCE(NEW.chunk_text, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop existing trigger if it exists (for idempotent migrations)
DROP TRIGGER IF EXISTS trigger_update_chunk_text_search ON document_embeddings;

-- Create trigger to auto-update tsvector on insert/update
CREATE TRIGGER trigger_update_chunk_text_search
    BEFORE INSERT OR UPDATE OF chunk_text
    ON document_embeddings
    FOR EACH ROW
    EXECUTE FUNCTION update_chunk_text_search();
