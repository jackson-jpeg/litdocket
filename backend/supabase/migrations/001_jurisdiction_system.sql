-- ============================================
-- LitDocket Jurisdiction System Migration
-- CompuLaw-style Rule Management
-- ============================================
-- Run this in Supabase SQL Editor
-- This creates the hierarchical jurisdiction and rule system

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- ENUM TYPES
-- ============================================

-- Jurisdiction types
CREATE TYPE jurisdiction_type AS ENUM (
    'federal',
    'state',
    'local',
    'bankruptcy',
    'appellate'
);

-- Court types
CREATE TYPE court_type AS ENUM (
    'circuit',
    'county',
    'district',
    'bankruptcy',
    'appellate_state',
    'appellate_federal',
    'supreme_state',
    'supreme_federal'
);

-- Rule set dependency types
CREATE TYPE dependency_type AS ENUM (
    'concurrent',    -- Loads alongside (e.g., FRCP with local rules)
    'inherits',      -- Inherits and can override
    'supplements',   -- Adds to parent rules
    'overrides'      -- Completely replaces parent
);

-- Trigger event types
CREATE TYPE trigger_type AS ENUM (
    'case_filed',
    'service_completed',
    'complaint_served',
    'answer_due',
    'discovery_commenced',
    'discovery_deadline',
    'dispositive_motions_due',
    'pretrial_conference',
    'trial_date',
    'hearing_scheduled',
    'motion_filed',
    'order_entered',
    'appeal_filed',
    'mediation_scheduled',
    'custom_trigger'
);

-- Deadline priority levels
CREATE TYPE deadline_priority AS ENUM (
    'informational',
    'standard',
    'important',
    'critical',
    'fatal'
);

-- Calculation methods
CREATE TYPE calculation_method AS ENUM (
    'calendar_days',
    'court_days',
    'business_days'
);

-- ============================================
-- JURISDICTIONS TABLE
-- ============================================
-- Hierarchical jurisdiction structure (Federal > State > Local)

CREATE TABLE IF NOT EXISTS jurisdictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(50) UNIQUE NOT NULL,  -- e.g., 'FED', 'FL', 'FL-11CIR'
    name VARCHAR(255) NOT NULL,
    description TEXT,
    jurisdiction_type jurisdiction_type NOT NULL,
    parent_jurisdiction_id UUID REFERENCES jurisdictions(id) ON DELETE SET NULL,
    state VARCHAR(50),  -- State code for state jurisdictions
    federal_circuit INTEGER CHECK (federal_circuit >= 1 AND federal_circuit <= 13),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for hierarchy queries
CREATE INDEX idx_jurisdictions_parent ON jurisdictions(parent_jurisdiction_id);
CREATE INDEX idx_jurisdictions_type ON jurisdictions(jurisdiction_type);
CREATE INDEX idx_jurisdictions_state ON jurisdictions(state);

-- ============================================
-- RULE SETS TABLE
-- ============================================
-- Individual rule sets (FRCP, FL:RCP, FL:BRMD-7, etc.)

CREATE TABLE IF NOT EXISTS rule_sets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(50) UNIQUE NOT NULL,  -- e.g., 'FRCP', 'FL:RCP', 'FL:BRMD-7'
    name VARCHAR(255) NOT NULL,
    description TEXT,
    jurisdiction_id UUID NOT NULL REFERENCES jurisdictions(id) ON DELETE CASCADE,
    court_type court_type NOT NULL,
    version VARCHAR(50) DEFAULT 'current',
    effective_date DATE,
    is_local BOOLEAN DEFAULT FALSE,  -- True for local court rules
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX idx_rule_sets_jurisdiction ON rule_sets(jurisdiction_id);
CREATE INDEX idx_rule_sets_court_type ON rule_sets(court_type);

-- ============================================
-- RULE SET DEPENDENCIES TABLE
-- ============================================
-- Defines which rule sets load together (CompuLaw concurrent rules)
-- e.g., FL:BRMD-7 requires FRCP + FRBP to load concurrently

CREATE TABLE IF NOT EXISTS rule_set_dependencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_set_id UUID NOT NULL REFERENCES rule_sets(id) ON DELETE CASCADE,
    required_rule_set_id UUID NOT NULL REFERENCES rule_sets(id) ON DELETE CASCADE,
    dependency_type dependency_type DEFAULT 'concurrent',
    priority INTEGER DEFAULT 0,  -- Load order (lower = first)
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(rule_set_id, required_rule_set_id)
);

CREATE INDEX idx_rule_set_deps_rule_set ON rule_set_dependencies(rule_set_id);
CREATE INDEX idx_rule_set_deps_required ON rule_set_dependencies(required_rule_set_id);

-- ============================================
-- COURT LOCATIONS TABLE
-- ============================================
-- Specific court locations for auto-detection

CREATE TABLE IF NOT EXISTS court_locations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    jurisdiction_id UUID NOT NULL REFERENCES jurisdictions(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    short_name VARCHAR(100),
    court_type court_type NOT NULL,
    district VARCHAR(100),  -- e.g., 'Southern', 'Middle', 'Northern'
    circuit INTEGER,
    division VARCHAR(100),
    -- Patterns for auto-detection from documents
    detection_patterns JSONB DEFAULT '[]'::JSONB,  -- Array of regex patterns
    case_number_pattern VARCHAR(255),  -- Regex for case number format
    -- Default rule sets for this court
    default_rule_set_id UUID REFERENCES rule_sets(id) ON DELETE SET NULL,
    local_rule_set_id UUID REFERENCES rule_sets(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_court_locations_jurisdiction ON court_locations(jurisdiction_id);
CREATE INDEX idx_court_locations_type ON court_locations(court_type);

-- ============================================
-- RULE TEMPLATES TABLE
-- ============================================
-- Template for deadline calculations based on triggers

CREATE TABLE IF NOT EXISTS rule_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_set_id UUID NOT NULL REFERENCES rule_sets(id) ON DELETE CASCADE,
    rule_code VARCHAR(100) NOT NULL,  -- e.g., 'FRCP-4', 'FL-RCP-1.140'
    name VARCHAR(255) NOT NULL,
    description TEXT,
    trigger_type trigger_type NOT NULL,
    citation VARCHAR(255),  -- e.g., 'Fla. R. Civ. P. 1.140(a)(1)'
    court_type court_type,  -- Optional: specific court type override
    case_types JSONB DEFAULT '[]'::JSONB,  -- Array of applicable case types
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(rule_set_id, rule_code)
);

CREATE INDEX idx_rule_templates_rule_set ON rule_templates(rule_set_id);
CREATE INDEX idx_rule_templates_trigger ON rule_templates(trigger_type);

-- ============================================
-- RULE TEMPLATE DEADLINES TABLE
-- ============================================
-- Individual deadlines generated from a rule template

CREATE TABLE IF NOT EXISTS rule_template_deadlines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_template_id UUID NOT NULL REFERENCES rule_templates(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    days_from_trigger INTEGER NOT NULL,  -- Negative = before, Positive = after
    priority deadline_priority DEFAULT 'standard',
    party_responsible VARCHAR(100),  -- 'plaintiff', 'defendant', 'both', 'court'
    action_required TEXT,
    calculation_method calculation_method DEFAULT 'calendar_days',
    add_service_days BOOLEAN DEFAULT FALSE,  -- Add service method days
    rule_citation VARCHAR(255),
    notes TEXT,
    conditions JSONB DEFAULT '{}'::JSONB,  -- Conditional logic
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_template_deadlines_template ON rule_template_deadlines(rule_template_id);

-- ============================================
-- CASE RULE SETS TABLE
-- ============================================
-- Links cases to their applicable rule sets

CREATE TABLE IF NOT EXISTS case_rule_sets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL,  -- References cases table
    rule_set_id UUID NOT NULL REFERENCES rule_sets(id) ON DELETE CASCADE,
    assignment_method VARCHAR(50) DEFAULT 'auto_detected',  -- 'auto_detected', 'user_selected', 'system'
    priority INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(case_id, rule_set_id)
);

CREATE INDEX idx_case_rule_sets_case ON case_rule_sets(case_id);
CREATE INDEX idx_case_rule_sets_rule_set ON case_rule_sets(rule_set_id);

-- ============================================
-- TRIGGER FOR UPDATED_AT
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to all tables with updated_at
CREATE TRIGGER update_jurisdictions_updated_at BEFORE UPDATE ON jurisdictions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_rule_sets_updated_at BEFORE UPDATE ON rule_sets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_court_locations_updated_at BEFORE UPDATE ON court_locations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_rule_templates_updated_at BEFORE UPDATE ON rule_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- ROW LEVEL SECURITY (Optional)
-- ============================================
-- Enable RLS for multi-tenant access control

-- Jurisdictions are public (read-only for most users)
ALTER TABLE jurisdictions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Jurisdictions are viewable by everyone" ON jurisdictions
    FOR SELECT USING (true);
CREATE POLICY "Jurisdictions are manageable by service role" ON jurisdictions
    FOR ALL USING (auth.role() = 'service_role');

-- Rule sets are public
ALTER TABLE rule_sets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Rule sets are viewable by everyone" ON rule_sets
    FOR SELECT USING (true);
CREATE POLICY "Rule sets are manageable by service role" ON rule_sets
    FOR ALL USING (auth.role() = 'service_role');

-- Rule templates are public
ALTER TABLE rule_templates ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Rule templates are viewable by everyone" ON rule_templates
    FOR SELECT USING (true);
CREATE POLICY "Rule templates are manageable by service role" ON rule_templates
    FOR ALL USING (auth.role() = 'service_role');

-- Rule template deadlines are public
ALTER TABLE rule_template_deadlines ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Rule template deadlines are viewable by everyone" ON rule_template_deadlines
    FOR SELECT USING (true);
CREATE POLICY "Rule template deadlines are manageable by service role" ON rule_template_deadlines
    FOR ALL USING (auth.role() = 'service_role');

-- Case rule sets - users can only see their own cases' rule sets
-- (Requires cases table with user_id)
ALTER TABLE case_rule_sets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Case rule sets are viewable by service role" ON case_rule_sets
    FOR ALL USING (auth.role() = 'service_role');

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Function to get all applicable rule sets for a case (including dependencies)
CREATE OR REPLACE FUNCTION get_applicable_rule_sets(p_case_id UUID)
RETURNS TABLE (
    rule_set_id UUID,
    code VARCHAR(50),
    name VARCHAR(255),
    assignment_method VARCHAR(50),
    priority INTEGER,
    is_dependency BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE rule_chain AS (
        -- Base: directly assigned rule sets
        SELECT
            rs.id as rule_set_id,
            rs.code,
            rs.name,
            crs.assignment_method,
            crs.priority,
            FALSE as is_dependency
        FROM case_rule_sets crs
        JOIN rule_sets rs ON rs.id = crs.rule_set_id
        WHERE crs.case_id = p_case_id AND crs.is_active = TRUE

        UNION

        -- Recursive: dependencies
        SELECT
            dep_rs.id,
            dep_rs.code,
            dep_rs.name,
            'dependency'::VARCHAR(50),
            rsd.priority,
            TRUE
        FROM rule_chain rc
        JOIN rule_set_dependencies rsd ON rsd.rule_set_id = rc.rule_set_id
        JOIN rule_sets dep_rs ON dep_rs.id = rsd.required_rule_set_id
        WHERE dep_rs.is_active = TRUE
    )
    SELECT DISTINCT ON (rule_chain.rule_set_id)
        rule_chain.rule_set_id,
        rule_chain.code,
        rule_chain.name,
        rule_chain.assignment_method,
        rule_chain.priority,
        rule_chain.is_dependency
    FROM rule_chain
    ORDER BY rule_chain.rule_set_id, rule_chain.is_dependency;
END;
$$ LANGUAGE plpgsql;

-- Function to get deadlines for a trigger type from applicable rule sets
CREATE OR REPLACE FUNCTION get_trigger_deadlines(
    p_rule_set_ids UUID[],
    p_trigger_type trigger_type
)
RETURNS TABLE (
    template_id UUID,
    template_name VARCHAR(255),
    deadline_id UUID,
    deadline_name VARCHAR(255),
    days_from_trigger INTEGER,
    priority deadline_priority,
    party_responsible VARCHAR(100),
    action_required TEXT,
    calculation_method calculation_method,
    add_service_days BOOLEAN,
    rule_citation VARCHAR(255)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        rt.id as template_id,
        rt.name as template_name,
        rtd.id as deadline_id,
        rtd.name as deadline_name,
        rtd.days_from_trigger,
        rtd.priority,
        rtd.party_responsible,
        rtd.action_required,
        rtd.calculation_method,
        rtd.add_service_days,
        COALESCE(rtd.rule_citation, rt.citation) as rule_citation
    FROM rule_templates rt
    JOIN rule_template_deadlines rtd ON rtd.rule_template_id = rt.id
    WHERE rt.rule_set_id = ANY(p_rule_set_ids)
      AND rt.trigger_type = p_trigger_type
      AND rt.is_active = TRUE
      AND rtd.is_active = TRUE
    ORDER BY rtd.days_from_trigger, rtd.display_order;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON TABLE jurisdictions IS 'Hierarchical jurisdiction structure (Federal > State > Local)';
COMMENT ON TABLE rule_sets IS 'Individual rule sets (FRCP, FL:RCP, etc.) - CompuLaw style codes';
COMMENT ON TABLE rule_set_dependencies IS 'Defines concurrent rule loading (e.g., bankruptcy rules require FRCP)';
COMMENT ON TABLE court_locations IS 'Specific courts with detection patterns for auto-identification';
COMMENT ON TABLE rule_templates IS 'Templates for deadline calculations based on trigger events';
COMMENT ON TABLE rule_template_deadlines IS 'Individual deadline definitions within a rule template';
COMMENT ON TABLE case_rule_sets IS 'Links cases to their applicable rule sets';
