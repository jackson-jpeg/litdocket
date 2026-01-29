-- Migration: Authority Core - AI-Powered Rules Database
-- Creates the primary rules database that replaces hardcoded templates
-- Supports scraping pipeline, approval workflow, and conflict detection

-- ============================================
-- NEW ENUMS
-- ============================================

-- Note: PostgreSQL doesn't have IF NOT EXISTS for CREATE TYPE
-- So we check existence first

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'authority_tier') THEN
        CREATE TYPE authority_tier AS ENUM (
            'federal',
            'state',
            'local',
            'standing_order',
            'firm'
        );
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'proposal_status') THEN
        CREATE TYPE proposal_status AS ENUM (
            'pending',
            'approved',
            'rejected',
            'needs_revision'
        );
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'scrape_status') THEN
        CREATE TYPE scrape_status AS ENUM (
            'queued',
            'searching',
            'extracting',
            'completed',
            'failed'
        );
    END IF;
END $$;

-- ============================================
-- AUTHORITY RULES TABLE - Primary Rules Database
-- ============================================

CREATE TABLE IF NOT EXISTS authority_rules (
    id VARCHAR(36) PRIMARY KEY,

    -- Ownership (NULL for system rules)
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,

    -- Jurisdiction reference
    jurisdiction_id VARCHAR(36) REFERENCES jurisdictions(id) ON DELETE CASCADE,

    -- Authority level for precedence
    authority_tier authority_tier NOT NULL DEFAULT 'state',

    -- Rule identification
    rule_code VARCHAR(100) NOT NULL,
    rule_name VARCHAR(255) NOT NULL,

    -- What triggers this rule
    trigger_type VARCHAR(100) NOT NULL,

    -- Source information
    citation TEXT,
    source_url TEXT,
    source_text TEXT,

    -- Deadline specifications (JSONB array)
    -- Structure: [{ title, days_from_trigger, calculation_method, priority, party_responsible, conditions }]
    deadlines JSONB NOT NULL DEFAULT '[]',

    -- Conditions when rule applies (JSONB)
    -- Structure: { case_types: [], motion_types: [], service_methods: [], exclusions: {} }
    conditions JSONB DEFAULT '{}',

    -- Service method extensions (JSONB)
    -- Structure: { mail: 3, electronic: 0, personal: 0 }
    service_extensions JSONB DEFAULT '{"mail": 3, "electronic": 0, "personal": 0}',

    -- AI extraction confidence (0.00 - 1.00)
    confidence_score DECIMAL(3,2) DEFAULT 0.00,

    -- Verification status
    is_verified BOOLEAN DEFAULT FALSE,
    verified_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    verified_at TIMESTAMPTZ,

    -- Active status
    is_active BOOLEAN DEFAULT TRUE,

    -- Effective dates
    effective_date DATE,
    superseded_date DATE,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indexes for authority_rules
CREATE INDEX IF NOT EXISTS idx_authority_rules_user_id ON authority_rules(user_id);
CREATE INDEX IF NOT EXISTS idx_authority_rules_jurisdiction_id ON authority_rules(jurisdiction_id);
CREATE INDEX IF NOT EXISTS idx_authority_rules_authority_tier ON authority_rules(authority_tier);
CREATE INDEX IF NOT EXISTS idx_authority_rules_trigger_type ON authority_rules(trigger_type);
CREATE INDEX IF NOT EXISTS idx_authority_rules_is_verified ON authority_rules(is_verified);
CREATE INDEX IF NOT EXISTS idx_authority_rules_is_active ON authority_rules(is_active);
CREATE INDEX IF NOT EXISTS idx_authority_rules_rule_code ON authority_rules(rule_code);

-- Composite index for common query pattern
CREATE INDEX IF NOT EXISTS idx_authority_rules_jurisdiction_trigger_active
    ON authority_rules(jurisdiction_id, trigger_type, is_active)
    WHERE is_active = TRUE;

-- Unique constraint for rule_code within jurisdiction
CREATE UNIQUE INDEX IF NOT EXISTS idx_authority_rules_jurisdiction_code
    ON authority_rules(jurisdiction_id, rule_code);

-- ============================================
-- SCRAPE JOBS TABLE - Tracks Scraping Operations
-- ============================================

CREATE TABLE IF NOT EXISTS scrape_jobs (
    id VARCHAR(36) PRIMARY KEY,

    -- Who initiated
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Target jurisdiction
    jurisdiction_id VARCHAR(36) REFERENCES jurisdictions(id) ON DELETE SET NULL,

    -- Search parameters
    search_query TEXT NOT NULL,

    -- Status tracking
    status scrape_status NOT NULL DEFAULT 'queued',
    progress_pct INTEGER DEFAULT 0 CHECK (progress_pct >= 0 AND progress_pct <= 100),

    -- Results
    rules_found INTEGER DEFAULT 0,
    proposals_created INTEGER DEFAULT 0,
    urls_processed TEXT[] DEFAULT '{}',

    -- Error handling
    error_message TEXT,
    error_details JSONB,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- Indexes for scrape_jobs
CREATE INDEX IF NOT EXISTS idx_scrape_jobs_user_id ON scrape_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_scrape_jobs_jurisdiction_id ON scrape_jobs(jurisdiction_id);
CREATE INDEX IF NOT EXISTS idx_scrape_jobs_status ON scrape_jobs(status);
CREATE INDEX IF NOT EXISTS idx_scrape_jobs_created_at ON scrape_jobs(created_at DESC);

-- ============================================
-- RULE PROPOSALS TABLE - Pending Review Queue
-- ============================================

CREATE TABLE IF NOT EXISTS rule_proposals (
    id VARCHAR(36) PRIMARY KEY,

    -- Who created the proposal (usually system via scrape)
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Parent scrape job (NULL if manually created)
    scrape_job_id VARCHAR(36) REFERENCES scrape_jobs(id) ON DELETE SET NULL,

    -- Target jurisdiction
    jurisdiction_id VARCHAR(36) REFERENCES jurisdictions(id) ON DELETE SET NULL,

    -- Proposed rule data (full structure matching authority_rules)
    proposed_rule_data JSONB NOT NULL,

    -- Source information
    source_url TEXT,
    source_text TEXT,

    -- AI extraction metadata
    confidence_score DECIMAL(3,2) DEFAULT 0.00,
    extraction_notes TEXT,

    -- Review status
    status proposal_status NOT NULL DEFAULT 'pending',

    -- Review tracking
    reviewed_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    reviewer_notes TEXT,

    -- If approved, link to created rule
    approved_rule_id VARCHAR(36) REFERENCES authority_rules(id) ON DELETE SET NULL,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    reviewed_at TIMESTAMPTZ
);

-- Indexes for rule_proposals
CREATE INDEX IF NOT EXISTS idx_rule_proposals_user_id ON rule_proposals(user_id);
CREATE INDEX IF NOT EXISTS idx_rule_proposals_scrape_job_id ON rule_proposals(scrape_job_id);
CREATE INDEX IF NOT EXISTS idx_rule_proposals_jurisdiction_id ON rule_proposals(jurisdiction_id);
CREATE INDEX IF NOT EXISTS idx_rule_proposals_status ON rule_proposals(status);
CREATE INDEX IF NOT EXISTS idx_rule_proposals_created_at ON rule_proposals(created_at DESC);

-- Index for pending proposals (common query)
CREATE INDEX IF NOT EXISTS idx_rule_proposals_pending
    ON rule_proposals(status, created_at DESC)
    WHERE status = 'pending';

-- ============================================
-- RULE CONFLICTS TABLE - Detected Conflicts
-- ============================================

CREATE TABLE IF NOT EXISTS rule_conflicts (
    id VARCHAR(36) PRIMARY KEY,

    -- The two conflicting rules
    rule_a_id VARCHAR(36) NOT NULL REFERENCES authority_rules(id) ON DELETE CASCADE,
    rule_b_id VARCHAR(36) NOT NULL REFERENCES authority_rules(id) ON DELETE CASCADE,

    -- Conflict details
    conflict_type VARCHAR(50) NOT NULL,  -- days_mismatch, method_mismatch, priority_mismatch, condition_overlap
    severity VARCHAR(20) NOT NULL DEFAULT 'warning',  -- info, warning, error
    description TEXT NOT NULL,

    -- Resolution
    resolution VARCHAR(50) DEFAULT 'pending',  -- pending, use_higher_tier, use_rule_a, use_rule_b, manual, ignored
    resolution_notes TEXT,

    resolved_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    resolved_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Prevent duplicate conflicts
    CONSTRAINT unique_rule_conflict UNIQUE (rule_a_id, rule_b_id, conflict_type)
);

-- Indexes for rule_conflicts
CREATE INDEX IF NOT EXISTS idx_rule_conflicts_rule_a_id ON rule_conflicts(rule_a_id);
CREATE INDEX IF NOT EXISTS idx_rule_conflicts_rule_b_id ON rule_conflicts(rule_b_id);
CREATE INDEX IF NOT EXISTS idx_rule_conflicts_resolution ON rule_conflicts(resolution);
CREATE INDEX IF NOT EXISTS idx_rule_conflicts_severity ON rule_conflicts(severity);

-- Index for unresolved conflicts
CREATE INDEX IF NOT EXISTS idx_rule_conflicts_pending
    ON rule_conflicts(created_at DESC)
    WHERE resolution = 'pending';

-- ============================================
-- RULE USAGE TRACKING TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS authority_rule_usage (
    id VARCHAR(36) PRIMARY KEY,

    -- Which rule was used
    rule_id VARCHAR(36) NOT NULL REFERENCES authority_rules(id) ON DELETE CASCADE,

    -- Where it was used
    case_id VARCHAR(36) REFERENCES cases(id) ON DELETE SET NULL,
    deadline_id VARCHAR(36) REFERENCES deadlines(id) ON DELETE SET NULL,

    -- Who used it
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Context
    trigger_type VARCHAR(100),
    trigger_date DATE,

    -- Result
    deadlines_generated INTEGER DEFAULT 0,

    -- Timestamp
    used_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indexes for authority_rule_usage
CREATE INDEX IF NOT EXISTS idx_authority_rule_usage_rule_id ON authority_rule_usage(rule_id);
CREATE INDEX IF NOT EXISTS idx_authority_rule_usage_case_id ON authority_rule_usage(case_id);
CREATE INDEX IF NOT EXISTS idx_authority_rule_usage_user_id ON authority_rule_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_authority_rule_usage_used_at ON authority_rule_usage(used_at DESC);

-- ============================================
-- UPDATED_AT TRIGGERS
-- ============================================

CREATE OR REPLACE FUNCTION update_authority_rules_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_authority_rules_updated_at ON authority_rules;
CREATE TRIGGER trigger_update_authority_rules_updated_at
    BEFORE UPDATE ON authority_rules
    FOR EACH ROW
    EXECUTE FUNCTION update_authority_rules_updated_at();

-- ============================================
-- ADD source_rule_id TO DEADLINES TABLE
-- ============================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'deadlines' AND column_name = 'source_rule_id'
    ) THEN
        ALTER TABLE deadlines
        ADD COLUMN source_rule_id VARCHAR(36) REFERENCES authority_rules(id) ON DELETE SET NULL;

        CREATE INDEX IF NOT EXISTS idx_deadlines_source_rule_id ON deadlines(source_rule_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'deadlines' AND column_name = 'rule_citation'
    ) THEN
        ALTER TABLE deadlines
        ADD COLUMN rule_citation TEXT;
    END IF;
END $$;

-- ============================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================

COMMENT ON TABLE authority_rules IS 'Primary rules database - single source of truth for deadline calculation rules. Replaces hardcoded templates.';
COMMENT ON TABLE scrape_jobs IS 'Tracks AI-powered web scraping operations for extracting court rules.';
COMMENT ON TABLE rule_proposals IS 'Queue of AI-extracted rules awaiting attorney review and approval.';
COMMENT ON TABLE rule_conflicts IS 'Detected conflicts between rules in same jurisdiction, helps ensure consistency.';
COMMENT ON TABLE authority_rule_usage IS 'Audit trail of when rules were applied to generate deadlines.';

COMMENT ON COLUMN authority_rules.authority_tier IS 'Precedence level: federal > state > local > standing_order > firm';
COMMENT ON COLUMN authority_rules.deadlines IS 'JSONB array of deadline specifications to generate when rule triggers';
COMMENT ON COLUMN authority_rules.conditions IS 'JSONB conditions that must be met for rule to apply (case_type, motion_type, etc)';
COMMENT ON COLUMN authority_rules.service_extensions IS 'Additional days to add based on service method (mail +3, etc)';
COMMENT ON COLUMN authority_rules.confidence_score IS 'AI extraction confidence 0.00-1.00, helps prioritize review';
COMMENT ON COLUMN authority_rules.is_verified IS 'Attorney-approved rules marked as verified';

COMMENT ON COLUMN rule_proposals.proposed_rule_data IS 'Full rule structure matching authority_rules schema, ready for approval';
COMMENT ON COLUMN rule_proposals.confidence_score IS 'AI confidence in extraction accuracy, lower scores need closer review';

COMMENT ON COLUMN rule_conflicts.conflict_type IS 'Type of conflict: days_mismatch, method_mismatch, priority_mismatch, condition_overlap';
COMMENT ON COLUMN rule_conflicts.resolution IS 'How conflict was resolved: pending, use_higher_tier, use_rule_a, use_rule_b, manual, ignored';
