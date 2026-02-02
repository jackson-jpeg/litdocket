-- Migration: 015_document_deadline_suggestions.sql
-- Description: Creates table for storing AI-extracted deadline suggestions from documents
-- Part of: Document → Deadline Auto-Generation Pipeline (Feature 1)

-- ============================================================================
-- Document Deadline Suggestions Table
-- ============================================================================
-- Stores AI-extracted deadlines as reviewable suggestions before they become
-- actual deadlines. Allows users to approve/reject and optionally trigger
-- cascade calculations.

CREATE TABLE IF NOT EXISTS document_deadline_suggestions (
    -- Primary key
    id VARCHAR(36) PRIMARY KEY,

    -- Foreign keys with ownership verification
    document_id VARCHAR(36) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Suggestion content
    title VARCHAR(500) NOT NULL,
    description TEXT,
    suggested_date DATE,
    deadline_type VARCHAR(100),

    -- Extraction metadata
    extraction_method VARCHAR(50) NOT NULL,  -- 'ai_key_dates', 'ai_deadlines_mentioned', 'trigger_detected'
    source_text TEXT,  -- Original text from document that led to this suggestion

    -- Rule matching (if applicable)
    matched_trigger_type VARCHAR(100),  -- Maps to TriggerType enum if detected
    rule_citation VARCHAR(255),

    -- Confidence scoring
    confidence_score INTEGER DEFAULT 50 CHECK (confidence_score >= 0 AND confidence_score <= 100),
    confidence_factors JSONB DEFAULT '{}',

    -- Status tracking
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'expired')),
    reviewed_at TIMESTAMPTZ,
    created_deadline_id VARCHAR(36) REFERENCES deadlines(id) ON DELETE SET NULL,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Index for fetching suggestions by document
CREATE INDEX idx_doc_suggestions_document_id ON document_deadline_suggestions(document_id);

-- Index for fetching pending suggestions by user
CREATE INDEX idx_doc_suggestions_user_pending ON document_deadline_suggestions(user_id, status) WHERE status = 'pending';

-- Index for case-level suggestion queries
CREATE INDEX idx_doc_suggestions_case_id ON document_deadline_suggestions(case_id);

-- Composite index for deduplication check
CREATE INDEX idx_doc_suggestions_dedupe ON document_deadline_suggestions(document_id, title, suggested_date);

-- ============================================================================
-- Trigger for updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION update_document_suggestions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER document_suggestions_updated_at
    BEFORE UPDATE ON document_deadline_suggestions
    FOR EACH ROW
    EXECUTE FUNCTION update_document_suggestions_updated_at();

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE document_deadline_suggestions IS 'Stores AI-extracted deadline suggestions from documents for user review before conversion to actual deadlines';
COMMENT ON COLUMN document_deadline_suggestions.extraction_method IS 'How the suggestion was extracted: ai_key_dates, ai_deadlines_mentioned, trigger_detected';
COMMENT ON COLUMN document_deadline_suggestions.matched_trigger_type IS 'If a trigger type was detected, references TriggerType enum values';
COMMENT ON COLUMN document_deadline_suggestions.confidence_score IS 'AI confidence in this suggestion (0-100)';
COMMENT ON COLUMN document_deadline_suggestions.status IS 'Review status: pending (awaiting review), approved (converted to deadline), rejected (user dismissed), expired (document updated)';
