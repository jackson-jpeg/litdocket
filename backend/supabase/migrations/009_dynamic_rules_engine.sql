-- Migration: Dynamic Rules Engine - Database-Driven Jurisdiction Rules
-- Transforms hardcoded rules into user-created, versionable JSON schemas
-- Enables unlimited jurisdictions without code changes

-- ============================================
-- RULE TEMPLATES TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS rule_templates (
    id VARCHAR(36) PRIMARY KEY,
    rule_name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    jurisdiction VARCHAR(100) NOT NULL,
    trigger_type VARCHAR(100) NOT NULL,

    -- Ownership
    created_by VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_public BOOLEAN DEFAULT FALSE,
    is_official BOOLEAN DEFAULT FALSE,

    -- Versioning
    current_version_id VARCHAR(36),
    version_count INTEGER DEFAULT 1,

    -- Status
    status VARCHAR(50) DEFAULT 'draft',

    -- Usage tracking
    usage_count INTEGER DEFAULT 0,
    user_count INTEGER DEFAULT 0,

    -- Metadata
    description TEXT,
    tags TEXT[],

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    published_at TIMESTAMPTZ,
    deprecated_at TIMESTAMPTZ
);

-- Indexes for rule_templates
CREATE INDEX IF NOT EXISTS idx_rule_templates_slug ON rule_templates(slug);
CREATE INDEX IF NOT EXISTS idx_rule_templates_jurisdiction ON rule_templates(jurisdiction);
CREATE INDEX IF NOT EXISTS idx_rule_templates_trigger_type ON rule_templates(trigger_type);
CREATE INDEX IF NOT EXISTS idx_rule_templates_is_public ON rule_templates(is_public);
CREATE INDEX IF NOT EXISTS idx_rule_templates_status ON rule_templates(status);
CREATE INDEX IF NOT EXISTS idx_rule_templates_created_by ON rule_templates(created_by);
CREATE INDEX IF NOT EXISTS idx_rule_templates_jurisdiction_trigger ON rule_templates(jurisdiction, trigger_type);

-- ============================================
-- RULE VERSIONS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS rule_versions (
    id VARCHAR(36) PRIMARY KEY,
    rule_template_id VARCHAR(36) NOT NULL REFERENCES rule_templates(id) ON DELETE CASCADE,

    -- Version info
    version_number INTEGER NOT NULL,
    version_name VARCHAR(255),

    -- The actual rule definition (JSON)
    rule_schema JSONB NOT NULL,

    -- Change tracking
    created_by VARCHAR(36) NOT NULL REFERENCES users(id),
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

-- Indexes for rule_versions
CREATE INDEX IF NOT EXISTS idx_rule_versions_template_id ON rule_versions(rule_template_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_rule_versions_unique_version
    ON rule_versions(rule_template_id, version_number);

-- Add foreign key for current_version_id in rule_templates
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_rule_templates_current_version'
        AND table_name = 'rule_templates'
    ) THEN
        ALTER TABLE rule_templates
        ADD CONSTRAINT fk_rule_templates_current_version
        FOREIGN KEY (current_version_id)
        REFERENCES rule_versions(id)
        ON DELETE SET NULL;
    END IF;
END $$;

-- ============================================
-- RULE CONDITIONS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS rule_conditions (
    id VARCHAR(36) PRIMARY KEY,
    rule_version_id VARCHAR(36) NOT NULL REFERENCES rule_versions(id) ON DELETE CASCADE,
    deadline_id VARCHAR(100) NOT NULL,

    -- Condition definition (JSON)
    condition_schema JSONB NOT NULL,

    -- Priority (conditions evaluated in order)
    priority INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for rule_conditions
CREATE INDEX IF NOT EXISTS idx_rule_conditions_version_id ON rule_conditions(rule_version_id);

-- ============================================
-- RULE EXECUTIONS TABLE (Audit Trail)
-- ============================================

CREATE TABLE IF NOT EXISTS rule_executions (
    id VARCHAR(36) PRIMARY KEY,

    -- What was executed
    rule_template_id VARCHAR(36) NOT NULL REFERENCES rule_templates(id),
    rule_version_id VARCHAR(36) NOT NULL REFERENCES rule_versions(id),

    -- Where it was executed
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id),
    trigger_deadline_id VARCHAR(36) REFERENCES deadlines(id),

    -- Who executed it
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),

    -- Input data
    trigger_data JSONB,

    -- Output results
    deadlines_created INTEGER DEFAULT 0,
    deadline_ids TEXT[],

    -- Performance
    execution_time_ms INTEGER,

    -- Status
    status VARCHAR(50),
    error_message TEXT,

    -- Timestamps
    executed_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indexes for rule_executions
CREATE INDEX IF NOT EXISTS idx_rule_executions_template_id ON rule_executions(rule_template_id);
CREATE INDEX IF NOT EXISTS idx_rule_executions_version_id ON rule_executions(rule_version_id);
CREATE INDEX IF NOT EXISTS idx_rule_executions_case_id ON rule_executions(case_id);
CREATE INDEX IF NOT EXISTS idx_rule_executions_user_id ON rule_executions(user_id);
CREATE INDEX IF NOT EXISTS idx_rule_executions_executed_at ON rule_executions(executed_at);

-- ============================================
-- RULE TEST CASES TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS rule_test_cases (
    id VARCHAR(36) PRIMARY KEY,
    rule_template_id VARCHAR(36) NOT NULL REFERENCES rule_templates(id) ON DELETE CASCADE,

    -- Test case definition
    test_name VARCHAR(255) NOT NULL,
    test_description TEXT,

    -- Input data
    input_data JSONB NOT NULL,

    -- Expected output
    expected_deadlines JSONB NOT NULL,

    -- Validation rules
    validation_rules JSONB,

    -- Test results
    last_run_at TIMESTAMPTZ,
    last_run_status VARCHAR(50),
    last_run_errors JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for rule_test_cases
CREATE INDEX IF NOT EXISTS idx_rule_test_cases_template_id ON rule_test_cases(rule_template_id);

-- ============================================
-- RULE DEPENDENCIES TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS rule_dependencies (
    id VARCHAR(36) PRIMARY KEY,
    rule_version_id VARCHAR(36) NOT NULL REFERENCES rule_versions(id) ON DELETE CASCADE,

    -- Dependency relationship
    deadline_id VARCHAR(100) NOT NULL,
    depends_on_deadline_id VARCHAR(100) NOT NULL,

    -- Dependency type
    dependency_type VARCHAR(50),

    -- Offset if sequential
    offset_days INTEGER,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for rule_dependencies
CREATE INDEX IF NOT EXISTS idx_rule_dependencies_version_id ON rule_dependencies(rule_version_id);

-- ============================================
-- UPDATED_AT TRIGGER FOR RULE TEMPLATES
-- ============================================

CREATE OR REPLACE FUNCTION update_rule_templates_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_rule_templates_updated_at ON rule_templates;
CREATE TRIGGER trigger_update_rule_templates_updated_at
    BEFORE UPDATE ON rule_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_rule_templates_updated_at();

-- ============================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================

COMMENT ON TABLE rule_templates IS 'Master rule definitions for jurisdiction/trigger combinations. Example: "Florida Civil - Trial Date Chain"';
COMMENT ON TABLE rule_versions IS 'Immutable versions of rules. Changes create new versions for rollback capability and audit trail.';
COMMENT ON TABLE rule_conditions IS 'Conditional logic for deadlines (if-then rules). Example: If case_type = "personal_injury" then offset_days = -120';
COMMENT ON TABLE rule_executions IS 'Complete audit trail of when rules were executed, with what data, and what results. Critical for legal defensibility.';
COMMENT ON TABLE rule_test_cases IS 'Test cases proving rules generate correct deadlines. Each rule should have comprehensive test coverage.';
COMMENT ON TABLE rule_dependencies IS 'Models deadline dependencies (deadline A must come before/after deadline B)';

COMMENT ON COLUMN rule_templates.slug IS 'Unique identifier for URLs: "florida-civil-trial-date"';
COMMENT ON COLUMN rule_templates.is_public IS 'Whether rule is shareable in marketplace';
COMMENT ON COLUMN rule_templates.is_official IS 'LitDocket-verified rule';
COMMENT ON COLUMN rule_templates.current_version_id IS 'Points to the active version of this rule';
COMMENT ON COLUMN rule_versions.rule_schema IS 'JSON schema defining trigger, deadlines, validation, and settings';
COMMENT ON COLUMN rule_executions.trigger_data IS 'Input data provided when rule was executed. Example: {"trial_date": "2026-03-01", "trial_type": "jury"}';
