-- Migration: Convert UUID columns to VARCHAR(36) for SQLAlchemy compatibility
-- This allows String(36) columns in Python models to work with PostgreSQL

-- ============================================
-- STEP 1: Drop empty tables (will recreate)
-- ============================================
DROP TABLE IF EXISTS audit_log CASCADE;
DROP TABLE IF EXISTS pending_docket_actions CASCADE;
DROP TABLE IF EXISTS case_rule_sets CASCADE;
DROP TABLE IF EXISTS trigger_events CASCADE;
DROP TABLE IF EXISTS deadlines CASCADE;

-- ============================================
-- STEP 2: Drop foreign key constraints on tables with data
-- ============================================
ALTER TABLE rule_sets DROP CONSTRAINT IF EXISTS rule_sets_jurisdiction_id_fkey;
ALTER TABLE rule_set_dependencies DROP CONSTRAINT IF EXISTS rule_set_dependencies_rule_set_id_fkey;
ALTER TABLE rule_set_dependencies DROP CONSTRAINT IF EXISTS rule_set_dependencies_required_rule_set_id_fkey;
ALTER TABLE rule_templates DROP CONSTRAINT IF EXISTS rule_templates_rule_set_id_fkey;
ALTER TABLE rule_template_deadlines DROP CONSTRAINT IF EXISTS rule_template_deadlines_rule_template_id_fkey;
ALTER TABLE court_locations DROP CONSTRAINT IF EXISTS court_locations_jurisdiction_id_fkey;
ALTER TABLE court_locations DROP CONSTRAINT IF EXISTS court_locations_default_rule_set_id_fkey;
ALTER TABLE court_locations DROP CONSTRAINT IF EXISTS court_locations_local_rule_set_id_fkey;
ALTER TABLE jurisdictions DROP CONSTRAINT IF EXISTS jurisdictions_parent_jurisdiction_id_fkey;

-- ============================================
-- STEP 3: Alter column types (in dependency order)
-- ============================================

-- JURISDICTIONS (root - no FKs)
ALTER TABLE jurisdictions
    ALTER COLUMN id TYPE VARCHAR(36) USING id::text,
    ALTER COLUMN parent_jurisdiction_id TYPE VARCHAR(36) USING parent_jurisdiction_id::text;

-- RULE_SETS (depends on jurisdictions)
ALTER TABLE rule_sets
    ALTER COLUMN id TYPE VARCHAR(36) USING id::text,
    ALTER COLUMN jurisdiction_id TYPE VARCHAR(36) USING jurisdiction_id::text;

-- RULE_SET_DEPENDENCIES (depends on rule_sets)
ALTER TABLE rule_set_dependencies
    ALTER COLUMN id TYPE VARCHAR(36) USING id::text,
    ALTER COLUMN rule_set_id TYPE VARCHAR(36) USING rule_set_id::text,
    ALTER COLUMN required_rule_set_id TYPE VARCHAR(36) USING required_rule_set_id::text;

-- RULE_TEMPLATES (depends on rule_sets)
ALTER TABLE rule_templates
    ALTER COLUMN id TYPE VARCHAR(36) USING id::text,
    ALTER COLUMN rule_set_id TYPE VARCHAR(36) USING rule_set_id::text;

-- RULE_TEMPLATE_DEADLINES (depends on rule_templates)
ALTER TABLE rule_template_deadlines
    ALTER COLUMN id TYPE VARCHAR(36) USING id::text,
    ALTER COLUMN rule_template_id TYPE VARCHAR(36) USING rule_template_id::text;

-- COURT_LOCATIONS (depends on jurisdictions, rule_sets)
ALTER TABLE court_locations
    ALTER COLUMN id TYPE VARCHAR(36) USING id::text,
    ALTER COLUMN jurisdiction_id TYPE VARCHAR(36) USING jurisdiction_id::text,
    ALTER COLUMN default_rule_set_id TYPE VARCHAR(36) USING default_rule_set_id::text,
    ALTER COLUMN local_rule_set_id TYPE VARCHAR(36) USING local_rule_set_id::text;

-- ============================================
-- STEP 4: Re-add foreign key constraints
-- ============================================
ALTER TABLE jurisdictions
    ADD CONSTRAINT jurisdictions_parent_jurisdiction_id_fkey
    FOREIGN KEY (parent_jurisdiction_id) REFERENCES jurisdictions(id);

ALTER TABLE rule_sets
    ADD CONSTRAINT rule_sets_jurisdiction_id_fkey
    FOREIGN KEY (jurisdiction_id) REFERENCES jurisdictions(id);

ALTER TABLE rule_set_dependencies
    ADD CONSTRAINT rule_set_dependencies_rule_set_id_fkey
    FOREIGN KEY (rule_set_id) REFERENCES rule_sets(id) ON DELETE CASCADE;

ALTER TABLE rule_set_dependencies
    ADD CONSTRAINT rule_set_dependencies_required_rule_set_id_fkey
    FOREIGN KEY (required_rule_set_id) REFERENCES rule_sets(id) ON DELETE CASCADE;

ALTER TABLE rule_templates
    ADD CONSTRAINT rule_templates_rule_set_id_fkey
    FOREIGN KEY (rule_set_id) REFERENCES rule_sets(id) ON DELETE CASCADE;

ALTER TABLE rule_template_deadlines
    ADD CONSTRAINT rule_template_deadlines_rule_template_id_fkey
    FOREIGN KEY (rule_template_id) REFERENCES rule_templates(id) ON DELETE CASCADE;

ALTER TABLE court_locations
    ADD CONSTRAINT court_locations_jurisdiction_id_fkey
    FOREIGN KEY (jurisdiction_id) REFERENCES jurisdictions(id);

ALTER TABLE court_locations
    ADD CONSTRAINT court_locations_default_rule_set_id_fkey
    FOREIGN KEY (default_rule_set_id) REFERENCES rule_sets(id);

ALTER TABLE court_locations
    ADD CONSTRAINT court_locations_local_rule_set_id_fkey
    FOREIGN KEY (local_rule_set_id) REFERENCES rule_sets(id);

-- ============================================
-- STEP 5: Recreate dropped tables with VARCHAR(36)
-- ============================================

-- DEADLINES (comprehensive for SQLAlchemy model)
CREATE TABLE deadlines (
    id VARCHAR(36) PRIMARY KEY,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    document_id VARCHAR(36) REFERENCES documents(id) ON DELETE SET NULL,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Core deadline information
    title VARCHAR(500) NOT NULL,
    description TEXT,
    deadline_date DATE,
    deadline_time TIME,
    deadline_type VARCHAR(100),

    -- Jackson's methodology fields
    party_role VARCHAR(255),
    action_required TEXT,
    trigger_event VARCHAR(500),
    trigger_date DATE,
    is_estimated BOOLEAN DEFAULT FALSE,
    source_document VARCHAR(500),
    service_method VARCHAR(100),

    -- Advanced calculation
    calculation_type VARCHAR(50) DEFAULT 'calendar_days',
    days_count INTEGER,

    -- Confidence scoring
    source_page INTEGER,
    source_text TEXT,
    source_coordinates JSONB,
    confidence_score INTEGER,
    confidence_level VARCHAR(20),
    confidence_factors JSONB,

    -- Verification
    verification_status VARCHAR(20) DEFAULT 'pending',
    verified_by VARCHAR(36) REFERENCES users(id),
    verified_at TIMESTAMPTZ,
    verification_notes TEXT,

    -- AI extraction
    extraction_method VARCHAR(50),
    extraction_quality_score INTEGER,

    -- Rule citations
    applicable_rule VARCHAR(255),
    rule_citation TEXT,
    calculation_basis TEXT,
    rule_template_id VARCHAR(36) REFERENCES rule_templates(id),
    trigger_event_id VARCHAR(36),

    -- Status and priority
    priority VARCHAR(20) DEFAULT 'standard',
    status VARCHAR(50) DEFAULT 'pending',
    reminder_sent BOOLEAN DEFAULT FALSE,
    created_via_chat BOOLEAN DEFAULT FALSE,

    -- Trigger architecture
    is_calculated BOOLEAN DEFAULT FALSE,
    is_dependent BOOLEAN DEFAULT FALSE,
    parent_deadline_id VARCHAR(36) REFERENCES deadlines(id) ON DELETE CASCADE,
    auto_recalculate BOOLEAN DEFAULT TRUE,

    -- Audit trail
    modified_by VARCHAR(255),
    modification_reason TEXT,
    original_deadline_date DATE,

    -- Manual override
    is_manually_overridden BOOLEAN DEFAULT FALSE,
    override_timestamp TIMESTAMPTZ,
    override_user_id VARCHAR(36) REFERENCES users(id),
    override_reason TEXT,

    -- Archive
    is_archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    archived_by VARCHAR(36) REFERENCES users(id),
    archival_reason TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_deadlines_case_id ON deadlines(case_id);
CREATE INDEX idx_deadlines_user_id ON deadlines(user_id);
CREATE INDEX idx_deadlines_deadline_date ON deadlines(deadline_date);
CREATE INDEX idx_deadlines_status ON deadlines(status);

-- TRIGGER_EVENTS
CREATE TABLE trigger_events (
    id VARCHAR(36) PRIMARY KEY,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_document_id VARCHAR(36) REFERENCES documents(id) ON DELETE SET NULL,

    trigger_type VARCHAR(100) NOT NULL,
    trigger_date DATE NOT NULL,
    description TEXT,

    -- Rule engine
    rule_set_id VARCHAR(36) REFERENCES rule_sets(id),
    deadlines_generated INTEGER DEFAULT 0,

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_trigger_events_case_id ON trigger_events(case_id);
CREATE INDEX idx_trigger_events_user_id ON trigger_events(user_id);

-- Add FK from deadlines to trigger_events now that it exists
ALTER TABLE deadlines
    ADD CONSTRAINT fk_deadlines_trigger_event
    FOREIGN KEY (trigger_event_id) REFERENCES trigger_events(id) ON DELETE SET NULL;

-- CASE_RULE_SETS (junction table)
CREATE TABLE case_rule_sets (
    id VARCHAR(36) PRIMARY KEY,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    rule_set_id VARCHAR(36) NOT NULL REFERENCES rule_sets(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT TRUE,
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    applied_by VARCHAR(36) REFERENCES users(id),
    UNIQUE(case_id, rule_set_id)
);

-- PENDING_DOCKET_ACTIONS
CREATE TABLE pending_docket_actions (
    id VARCHAR(36) PRIMARY KEY,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_document_id VARCHAR(36) REFERENCES documents(id) ON DELETE SET NULL,

    action_type VARCHAR(50) NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    target_id VARCHAR(36),
    committed_record_id VARCHAR(36),

    proposed_data JSONB NOT NULL,
    ai_confidence NUMERIC(3,2),
    ai_reasoning TEXT,

    status VARCHAR(20) DEFAULT 'pending',
    reviewed_by VARCHAR(36) REFERENCES users(id),
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pending_actions_case_id ON pending_docket_actions(case_id);
CREATE INDEX idx_pending_actions_status ON pending_docket_actions(status);

-- AUDIT_LOG
CREATE TABLE audit_log (
    audit_id VARCHAR(36) PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_id VARCHAR(36) NOT NULL,
    action VARCHAR(20) NOT NULL,
    changed_by VARCHAR(36) REFERENCES users(id),
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    old_values JSONB,
    new_values JSONB,
    change_reason TEXT,
    previous_audit_id VARCHAR(36) REFERENCES audit_log(audit_id)
);

CREATE INDEX idx_audit_log_table_record ON audit_log(table_name, record_id);
CREATE INDEX idx_audit_log_changed_at ON audit_log(changed_at);

-- ============================================
-- STEP 6: Add update triggers for new tables
-- ============================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_deadlines_updated_at') THEN
        CREATE TRIGGER update_deadlines_updated_at BEFORE UPDATE ON deadlines FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_trigger_events_updated_at') THEN
        CREATE TRIGGER update_trigger_events_updated_at BEFORE UPDATE ON trigger_events FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_pending_docket_actions_updated_at') THEN
        CREATE TRIGGER update_pending_docket_actions_updated_at BEFORE UPDATE ON pending_docket_actions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;
