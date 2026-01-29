-- Migration 011: Document Classification Phase 1
-- Adds fields to support "soft ingestion" - rich classification for all documents,
-- including those that don't match known trigger patterns.

-- ============================================================================
-- PART 1: Add classification fields to documents table
-- ============================================================================

-- Classification status tracks where the document is in the classification pipeline
ALTER TABLE documents ADD COLUMN IF NOT EXISTS classification_status VARCHAR(50) DEFAULT 'pending';

-- What trigger type was matched (if any)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS matched_trigger_type VARCHAR(100);

-- What pattern matched (for debugging/transparency)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS matched_pattern VARCHAR(255);

-- Classification confidence score (0.0 - 1.0)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS classification_confidence DECIMAL(3,2);

-- For unrecognized documents: AI's best guess at the trigger event
ALTER TABLE documents ADD COLUMN IF NOT EXISTS potential_trigger_event VARCHAR(255);

-- Whether this document requires a response
ALTER TABLE documents ADD COLUMN IF NOT EXISTS response_required BOOLEAN DEFAULT FALSE;

-- Who must respond (plaintiff, defendant, both, third_party)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS response_party VARCHAR(50);

-- Estimated response deadline in days (from AI analysis)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS response_deadline_days INTEGER;

-- What stage the case is in (Pre-Answer, Discovery, etc.)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS procedural_posture VARCHAR(100);

-- What the filing party is asking for
ALTER TABLE documents ADD COLUMN IF NOT EXISTS relief_sought TEXT;

-- Urgency indicators found in the document (JSON array)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS urgency_indicators JSONB DEFAULT '[]';

-- Rule citations found in the document (JSON array)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS rule_references JSONB DEFAULT '[]';

-- Suggested next action for the user
ALTER TABLE documents ADD COLUMN IF NOT EXISTS suggested_action VARCHAR(50);

-- Document category (motion, order, notice, pleading, discovery, etc.)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS document_category VARCHAR(50);

-- ============================================================================
-- PART 2: Create index for efficient querying by classification status
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_documents_classification_status
ON documents(classification_status);

CREATE INDEX IF NOT EXISTS idx_documents_response_required
ON documents(response_required)
WHERE response_required = TRUE;

CREATE INDEX IF NOT EXISTS idx_documents_suggested_action
ON documents(suggested_action)
WHERE suggested_action IN ('research_deadlines', 'manual_review');

-- ============================================================================
-- PART 3: Add comment documentation
-- ============================================================================

COMMENT ON COLUMN documents.classification_status IS
'Classification pipeline status: pending, matched, unrecognized, needs_research, researched, manual';

COMMENT ON COLUMN documents.matched_trigger_type IS
'If matched, the TriggerType enum value that was matched';

COMMENT ON COLUMN documents.classification_confidence IS
'Confidence score from 0.0 to 1.0 for the classification';

COMMENT ON COLUMN documents.potential_trigger_event IS
'For unrecognized documents, AI best guess at what trigger event this might be';

COMMENT ON COLUMN documents.response_required IS
'Whether this document requires a response from another party';

COMMENT ON COLUMN documents.procedural_posture IS
'What stage the case is in (Pre-Answer, Discovery Phase, etc.)';

COMMENT ON COLUMN documents.urgency_indicators IS
'JSON array of urgency keywords found (emergency, expedited, ex parte, etc.)';

COMMENT ON COLUMN documents.rule_references IS
'JSON array of rule citations found in the document';

COMMENT ON COLUMN documents.suggested_action IS
'Next step: apply_rules, research_deadlines, manual_review, or none';

-- ============================================================================
-- PART 4: Create rule_proposals table for Phase 2 preparation
-- This allows AI to propose rules that require attorney review
-- ============================================================================

CREATE TABLE IF NOT EXISTS rule_proposals (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,

    -- Link to source document that triggered the research
    case_id VARCHAR(36) REFERENCES cases(id) ON DELETE CASCADE,
    document_id VARCHAR(36) REFERENCES documents(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL,

    -- What trigger event was detected/proposed
    proposed_trigger VARCHAR(255) NOT NULL,
    proposed_trigger_type VARCHAR(100),

    -- Proposed deadline rule
    proposed_days INTEGER NOT NULL,
    proposed_priority VARCHAR(20) DEFAULT 'standard',
    proposed_calculation_method VARCHAR(50) DEFAULT 'calendar_days',

    -- Rule citation if found
    citation VARCHAR(255),
    citation_url VARCHAR(500),

    -- Source text that supports this proposal
    source_text TEXT,
    source_snippet TEXT,

    -- AI confidence in this proposal
    confidence_score DECIMAL(3,2),

    -- Detected conflicts with existing rules
    conflicts JSONB DEFAULT '[]',

    -- Review workflow
    status VARCHAR(20) DEFAULT 'pending',
    reviewed_by VARCHAR(36),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    user_notes TEXT,

    -- If approved, link to the created rule template
    created_rule_template_id VARCHAR(36),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for rule_proposals
CREATE INDEX IF NOT EXISTS idx_rule_proposals_status
ON rule_proposals(status);

CREATE INDEX IF NOT EXISTS idx_rule_proposals_user
ON rule_proposals(user_id);

CREATE INDEX IF NOT EXISTS idx_rule_proposals_case
ON rule_proposals(case_id);

CREATE INDEX IF NOT EXISTS idx_rule_proposals_document
ON rule_proposals(document_id);

-- Comments
COMMENT ON TABLE rule_proposals IS
'AI-proposed deadline rules awaiting attorney review. Phase 2 of intelligent document recognition.';

COMMENT ON COLUMN rule_proposals.status IS
'Proposal status: pending, approved, rejected, modified';

COMMENT ON COLUMN rule_proposals.conflicts IS
'JSON array of detected conflicts with existing rules';

-- ============================================================================
-- PART 5: Add fields to rule_templates for AI-created rules
-- ============================================================================

ALTER TABLE rule_templates ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';
ALTER TABLE rule_templates ADD COLUMN IF NOT EXISTS is_official BOOLEAN DEFAULT TRUE;
ALTER TABLE rule_templates ADD COLUMN IF NOT EXISTS created_by VARCHAR(100) DEFAULT 'SYSTEM';
ALTER TABLE rule_templates ADD COLUMN IF NOT EXISTS research_sources JSONB DEFAULT '[]';
ALTER TABLE rule_templates ADD COLUMN IF NOT EXISTS conflict_notes TEXT;
ALTER TABLE rule_templates ADD COLUMN IF NOT EXISTS approved_by VARCHAR(36);
ALTER TABLE rule_templates ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP WITH TIME ZONE;

COMMENT ON COLUMN rule_templates.status IS
'Rule status: active, draft, rejected, archived';

COMMENT ON COLUMN rule_templates.is_official IS
'TRUE for official court rules, FALSE for AI-discovered or user-created';

COMMENT ON COLUMN rule_templates.created_by IS
'Who created: SYSTEM, AI_AGENT, or user_id';

COMMENT ON COLUMN rule_templates.research_sources IS
'JSON array of sources used to create this rule (for AI-created rules)';
