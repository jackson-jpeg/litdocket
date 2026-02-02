-- Migration: 016_enhanced_recommendations.sql
-- Description: Creates table for enhanced case recommendations with actionable context
-- Part of: Enhanced Case Intelligence with Actionable Recommendations (Feature 2)

-- ============================================================================
-- Case Recommendations Table
-- ============================================================================
-- Stores AI-generated actionable recommendations for cases with full context:
-- - Links to specific deadlines/documents that triggered the recommendation
-- - Rule citations and legal consequences
-- - Suggested tools and next actions

CREATE TABLE IF NOT EXISTS case_recommendations (
    -- Primary key
    id VARCHAR(36) PRIMARY KEY,

    -- Foreign keys with ownership
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Core recommendation fields
    priority INTEGER NOT NULL DEFAULT 10,  -- Lower = more important (1 is highest)
    action TEXT NOT NULL,  -- What the user should do
    reasoning TEXT,  -- Why this recommendation was generated
    category VARCHAR(50) NOT NULL,  -- deadlines, documents, discovery, risk, compliance, etc.

    -- Context linking
    triggered_by_deadline_id VARCHAR(36) REFERENCES deadlines(id) ON DELETE SET NULL,
    triggered_by_document_id VARCHAR(36) REFERENCES documents(id) ON DELETE SET NULL,

    -- Legal context
    rule_citations JSONB DEFAULT '[]',  -- Array of rule citations e.g. ["Fla. R. Civ. P. 1.140(a)(1)"]
    consequence_if_ignored TEXT,  -- What happens if user doesn't act
    urgency_level VARCHAR(20) DEFAULT 'medium' CHECK (urgency_level IN ('critical', 'high', 'medium', 'low')),
    days_until_consequence INTEGER,  -- Days until the consequence occurs

    -- Actionable tools
    suggested_tools JSONB DEFAULT '[]',  -- Array of tool suggestions with actions
    -- Example: [{"tool": "deadline-calculator", "action": "Verify calculation", "params": {"deadline_id": "xxx"}}]

    suggested_document_types JSONB DEFAULT '[]',  -- Document types to upload
    -- Example: ["Answer", "Motion to Dismiss", "Certificate of Service"]

    -- Status tracking
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'dismissed', 'expired')),
    completed_at TIMESTAMPTZ,
    dismissed_at TIMESTAMPTZ,
    dismissed_reason TEXT,

    -- Auto-expiration
    expires_at TIMESTAMPTZ,  -- Recommendation may expire (e.g., after deadline passes)

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Index for fetching recommendations by case
CREATE INDEX idx_recommendations_case_id ON case_recommendations(case_id);

-- Index for fetching active recommendations by user
CREATE INDEX idx_recommendations_user_active ON case_recommendations(user_id, status) WHERE status IN ('pending', 'in_progress');

-- Index for urgency-based queries
CREATE INDEX idx_recommendations_urgency ON case_recommendations(urgency_level, priority) WHERE status = 'pending';

-- Index for deadline-linked recommendations
CREATE INDEX idx_recommendations_deadline ON case_recommendations(triggered_by_deadline_id) WHERE triggered_by_deadline_id IS NOT NULL;

-- ============================================================================
-- Trigger for updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION update_recommendations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER recommendations_updated_at
    BEFORE UPDATE ON case_recommendations
    FOR EACH ROW
    EXECUTE FUNCTION update_recommendations_updated_at();

-- ============================================================================
-- Auto-expire function (optional - can be called by cron)
-- ============================================================================

CREATE OR REPLACE FUNCTION expire_old_recommendations()
RETURNS INTEGER AS $$
DECLARE
    expired_count INTEGER;
BEGIN
    UPDATE case_recommendations
    SET status = 'expired', updated_at = NOW()
    WHERE status = 'pending'
      AND expires_at IS NOT NULL
      AND expires_at < NOW();

    GET DIAGNOSTICS expired_count = ROW_COUNT;
    RETURN expired_count;
END;
$$ language 'plpgsql';

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE case_recommendations IS 'Stores AI-generated actionable recommendations for cases with full context including rule citations and consequences';
COMMENT ON COLUMN case_recommendations.priority IS 'Priority level (1 = highest priority, higher numbers = lower priority)';
COMMENT ON COLUMN case_recommendations.triggered_by_deadline_id IS 'The deadline that triggered this recommendation, if applicable';
COMMENT ON COLUMN case_recommendations.rule_citations IS 'Array of legal rule citations supporting this recommendation';
COMMENT ON COLUMN case_recommendations.consequence_if_ignored IS 'Description of what happens if user ignores this recommendation';
COMMENT ON COLUMN case_recommendations.urgency_level IS 'Urgency level: critical (immediate action), high (urgent), medium (soon), low (whenever)';
COMMENT ON COLUMN case_recommendations.suggested_tools IS 'Array of tool suggestions with action descriptions and parameters';
COMMENT ON COLUMN case_recommendations.suggested_document_types IS 'Array of document types the user should upload';
