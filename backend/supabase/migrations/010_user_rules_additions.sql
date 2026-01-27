-- Migration: User-Created Rules System
-- Creates separate tables for user-created rules to avoid conflict with
-- the CompuLaw-style RuleTemplate in jurisdiction.py

-- ============================================
-- USER RULE TEMPLATES TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS user_rule_templates (
    id VARCHAR(36) PRIMARY KEY,
    rule_name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    description TEXT,

    -- Classification
    jurisdiction VARCHAR(100) NOT NULL,
    trigger_type VARCHAR(100) NOT NULL,
    tags TEXT[],

    -- Ownership
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Sharing
    is_public BOOLEAN DEFAULT FALSE,
    is_official BOOLEAN DEFAULT FALSE,

    -- Current version tracking
    current_version_id VARCHAR(36),

    -- Statistics
    version_count INTEGER DEFAULT 1,
    usage_count INTEGER DEFAULT 0,
    user_count INTEGER DEFAULT 0,

    -- Status
    status VARCHAR(50) DEFAULT 'draft',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    published_at TIMESTAMPTZ,
    deprecated_at TIMESTAMPTZ
);

-- Indexes for user_rule_templates
CREATE INDEX IF NOT EXISTS idx_user_rule_templates_user_id ON user_rule_templates(user_id);
CREATE INDEX IF NOT EXISTS idx_user_rule_templates_slug ON user_rule_templates(slug);
CREATE INDEX IF NOT EXISTS idx_user_rule_templates_jurisdiction ON user_rule_templates(jurisdiction);
CREATE INDEX IF NOT EXISTS idx_user_rule_templates_trigger_type ON user_rule_templates(trigger_type);
CREATE INDEX IF NOT EXISTS idx_user_rule_templates_is_public ON user_rule_templates(is_public);
CREATE INDEX IF NOT EXISTS idx_user_rule_templates_status ON user_rule_templates(status);
CREATE INDEX IF NOT EXISTS idx_user_rule_templates_public_active
    ON user_rule_templates(is_public, status)
    WHERE is_public = TRUE;

-- Unique constraint for slug per user
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_rule_templates_user_slug
    ON user_rule_templates(user_id, slug);

-- ============================================
-- USER RULE TEMPLATE VERSIONS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS user_rule_template_versions (
    id VARCHAR(36) PRIMARY KEY,
    rule_template_id VARCHAR(36) NOT NULL REFERENCES user_rule_templates(id) ON DELETE CASCADE,

    -- Version info
    version_number INTEGER NOT NULL,
    version_name VARCHAR(255),

    -- The actual rule definition (JSON)
    rule_schema JSONB NOT NULL,

    -- Creator
    created_by VARCHAR(36) REFERENCES users(id),

    -- Change tracking
    change_summary TEXT,

    -- Validation
    is_validated BOOLEAN DEFAULT FALSE,
    validation_errors JSONB,

    -- Testing
    test_cases_passed INTEGER DEFAULT 0,
    test_cases_failed INTEGER DEFAULT 0,

    -- Status
    status VARCHAR(50) DEFAULT 'draft',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    activated_at TIMESTAMPTZ,
    deprecated_at TIMESTAMPTZ
);

-- Indexes for user_rule_template_versions
CREATE INDEX IF NOT EXISTS idx_user_rule_versions_template_id ON user_rule_template_versions(rule_template_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_rule_versions_unique_version
    ON user_rule_template_versions(rule_template_id, version_number);

-- ============================================
-- USER RULE EXECUTIONS TABLE (Audit Trail)
-- ============================================

CREATE TABLE IF NOT EXISTS user_rule_executions (
    id VARCHAR(36) PRIMARY KEY,

    -- What was executed
    rule_template_id VARCHAR(36) REFERENCES user_rule_templates(id) ON DELETE SET NULL,
    rule_version_id VARCHAR(36) REFERENCES user_rule_template_versions(id) ON DELETE SET NULL,

    -- Who executed and where
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    case_id VARCHAR(36) REFERENCES cases(id) ON DELETE SET NULL,

    -- Input data
    trigger_data JSONB,

    -- Output results
    deadlines_created INTEGER DEFAULT 0,
    deadline_ids TEXT[],

    -- Performance
    execution_time_ms INTEGER,

    -- Status
    status VARCHAR(50) DEFAULT 'success',
    error_message TEXT,
    errors JSONB,

    -- Dry run flag
    dry_run BOOLEAN DEFAULT FALSE,

    -- Timestamps
    executed_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indexes for user_rule_executions
CREATE INDEX IF NOT EXISTS idx_user_rule_executions_template_id ON user_rule_executions(rule_template_id);
CREATE INDEX IF NOT EXISTS idx_user_rule_executions_version_id ON user_rule_executions(rule_version_id);
CREATE INDEX IF NOT EXISTS idx_user_rule_executions_case_id ON user_rule_executions(case_id);
CREATE INDEX IF NOT EXISTS idx_user_rule_executions_user_id ON user_rule_executions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_rule_executions_executed_at ON user_rule_executions(executed_at);

-- ============================================
-- UPDATED_AT TRIGGER FOR USER RULE TEMPLATES
-- ============================================

CREATE OR REPLACE FUNCTION update_user_rule_templates_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_user_rule_templates_updated_at ON user_rule_templates;
CREATE TRIGGER trigger_update_user_rule_templates_updated_at
    BEFORE UPDATE ON user_rule_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_user_rule_templates_updated_at();

-- ============================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================

COMMENT ON TABLE user_rule_templates IS 'User-created deadline calculation rules. Separate from CompuLaw-style RuleTemplate in rule_templates table.';
COMMENT ON TABLE user_rule_template_versions IS 'Immutable versions of user rules for rollback and audit trail.';
COMMENT ON TABLE user_rule_executions IS 'Audit trail of when user rules were executed, with inputs and results.';

COMMENT ON COLUMN user_rule_templates.slug IS 'URL-friendly identifier unique per user';
COMMENT ON COLUMN user_rule_templates.is_public IS 'Whether rule is shareable in marketplace';
COMMENT ON COLUMN user_rule_templates.is_official IS 'LitDocket-verified rule';
COMMENT ON COLUMN user_rule_template_versions.rule_schema IS 'JSON schema defining trigger, deadlines, validation, and settings';
COMMENT ON COLUMN user_rule_executions.dry_run IS 'If true, this was a preview execution that did not create actual deadlines';
