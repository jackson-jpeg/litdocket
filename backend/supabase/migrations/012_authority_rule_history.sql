-- ============================================================================
-- Migration 012: Authority Rule History (Version Control)
--
-- Creates the authority_rule_history table for tracking changes to authority
-- rules. This supports:
-- - Legal defensibility through complete audit trail
-- - Version rollback capabilities
-- - Change attribution and compliance tracking
-- ============================================================================

-- ============================================================================
-- 1. Create authority_rule_history table
-- ============================================================================

CREATE TABLE IF NOT EXISTS authority_rule_history (
    id VARCHAR(36) PRIMARY KEY,

    -- The rule this history entry belongs to
    rule_id VARCHAR(36) NOT NULL REFERENCES authority_rules(id) ON DELETE CASCADE,

    -- Version number (incrementing)
    version INTEGER NOT NULL DEFAULT 1,

    -- Who made the change
    changed_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,

    -- What type of change was made
    -- Values: created, updated, superseded, deactivated, reactivated
    change_type VARCHAR(50) NOT NULL,

    -- Snapshots of the rule data before and after the change
    previous_data JSONB,  -- Full rule data before change (null for 'created')
    new_data JSONB NOT NULL,  -- Full rule data after change

    -- Fields that were changed (for easier diffing)
    changed_fields TEXT[],  -- ["deadlines", "citation", "conditions"]

    -- Reason for the change
    change_reason TEXT,

    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 2. Create indexes for efficient queries
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_authority_rule_history_rule_id
    ON authority_rule_history(rule_id);

CREATE INDEX IF NOT EXISTS idx_authority_rule_history_changed_by
    ON authority_rule_history(changed_by);

CREATE INDEX IF NOT EXISTS idx_authority_rule_history_change_type
    ON authority_rule_history(change_type);

CREATE INDEX IF NOT EXISTS idx_authority_rule_history_created_at
    ON authority_rule_history(created_at DESC);

-- Composite index for getting latest version of a rule
CREATE INDEX IF NOT EXISTS idx_authority_rule_history_rule_version
    ON authority_rule_history(rule_id, version DESC);

-- ============================================================================
-- 3. Create trigger function to auto-capture rule changes
-- ============================================================================

CREATE OR REPLACE FUNCTION capture_authority_rule_history()
RETURNS TRIGGER AS $$
DECLARE
    v_version INTEGER;
    v_change_type VARCHAR(50);
    v_previous_data JSONB;
    v_new_data JSONB;
    v_changed_fields TEXT[];
BEGIN
    -- Get the next version number for this rule
    SELECT COALESCE(MAX(version), 0) + 1 INTO v_version
    FROM authority_rule_history
    WHERE rule_id = COALESCE(NEW.id, OLD.id);

    -- Determine change type
    IF TG_OP = 'INSERT' THEN
        v_change_type := 'created';
        v_previous_data := NULL;
    ELSIF TG_OP = 'UPDATE' THEN
        -- Check if is_active changed
        IF OLD.is_active = TRUE AND NEW.is_active = FALSE THEN
            v_change_type := 'deactivated';
        ELSIF OLD.is_active = FALSE AND NEW.is_active = TRUE THEN
            v_change_type := 'reactivated';
        ELSIF NEW.superseded_date IS NOT NULL AND OLD.superseded_date IS NULL THEN
            v_change_type := 'superseded';
        ELSE
            v_change_type := 'updated';
        END IF;

        -- Build previous data snapshot
        v_previous_data := jsonb_build_object(
            'rule_code', OLD.rule_code,
            'rule_name', OLD.rule_name,
            'trigger_type', OLD.trigger_type,
            'authority_tier', OLD.authority_tier,
            'citation', OLD.citation,
            'source_url', OLD.source_url,
            'source_text', OLD.source_text,
            'deadlines', OLD.deadlines,
            'conditions', OLD.conditions,
            'service_extensions', OLD.service_extensions,
            'confidence_score', OLD.confidence_score,
            'is_verified', OLD.is_verified,
            'is_active', OLD.is_active,
            'effective_date', OLD.effective_date,
            'superseded_date', OLD.superseded_date
        );

        -- Detect changed fields
        v_changed_fields := ARRAY[]::TEXT[];
        IF OLD.rule_code IS DISTINCT FROM NEW.rule_code THEN
            v_changed_fields := array_append(v_changed_fields, 'rule_code');
        END IF;
        IF OLD.rule_name IS DISTINCT FROM NEW.rule_name THEN
            v_changed_fields := array_append(v_changed_fields, 'rule_name');
        END IF;
        IF OLD.trigger_type IS DISTINCT FROM NEW.trigger_type THEN
            v_changed_fields := array_append(v_changed_fields, 'trigger_type');
        END IF;
        IF OLD.authority_tier IS DISTINCT FROM NEW.authority_tier THEN
            v_changed_fields := array_append(v_changed_fields, 'authority_tier');
        END IF;
        IF OLD.citation IS DISTINCT FROM NEW.citation THEN
            v_changed_fields := array_append(v_changed_fields, 'citation');
        END IF;
        IF OLD.deadlines::text IS DISTINCT FROM NEW.deadlines::text THEN
            v_changed_fields := array_append(v_changed_fields, 'deadlines');
        END IF;
        IF OLD.conditions::text IS DISTINCT FROM NEW.conditions::text THEN
            v_changed_fields := array_append(v_changed_fields, 'conditions');
        END IF;
        IF OLD.service_extensions::text IS DISTINCT FROM NEW.service_extensions::text THEN
            v_changed_fields := array_append(v_changed_fields, 'service_extensions');
        END IF;
        IF OLD.is_verified IS DISTINCT FROM NEW.is_verified THEN
            v_changed_fields := array_append(v_changed_fields, 'is_verified');
        END IF;
        IF OLD.is_active IS DISTINCT FROM NEW.is_active THEN
            v_changed_fields := array_append(v_changed_fields, 'is_active');
        END IF;
    ELSE
        -- DELETE - we don't track deletions (rules should be deactivated, not deleted)
        RETURN OLD;
    END IF;

    -- Build new data snapshot
    v_new_data := jsonb_build_object(
        'rule_code', NEW.rule_code,
        'rule_name', NEW.rule_name,
        'trigger_type', NEW.trigger_type,
        'authority_tier', NEW.authority_tier,
        'citation', NEW.citation,
        'source_url', NEW.source_url,
        'source_text', NEW.source_text,
        'deadlines', NEW.deadlines,
        'conditions', NEW.conditions,
        'service_extensions', NEW.service_extensions,
        'confidence_score', NEW.confidence_score,
        'is_verified', NEW.is_verified,
        'is_active', NEW.is_active,
        'effective_date', NEW.effective_date,
        'superseded_date', NEW.superseded_date
    );

    -- Insert history record
    INSERT INTO authority_rule_history (
        id,
        rule_id,
        version,
        changed_by,
        change_type,
        previous_data,
        new_data,
        changed_fields
    ) VALUES (
        gen_random_uuid()::text,
        NEW.id,
        v_version,
        NEW.verified_by,  -- Use verified_by as the changer (best available)
        v_change_type,
        v_previous_data,
        v_new_data,
        v_changed_fields
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 4. Create trigger on authority_rules table
-- ============================================================================

DROP TRIGGER IF EXISTS trg_authority_rule_history ON authority_rules;

CREATE TRIGGER trg_authority_rule_history
    AFTER INSERT OR UPDATE ON authority_rules
    FOR EACH ROW
    EXECUTE FUNCTION capture_authority_rule_history();

-- ============================================================================
-- 5. Backfill history for existing rules
-- ============================================================================

-- Create initial history entries for all existing rules
INSERT INTO authority_rule_history (
    id,
    rule_id,
    version,
    changed_by,
    change_type,
    previous_data,
    new_data,
    changed_fields,
    created_at
)
SELECT
    gen_random_uuid()::text,
    id,
    1,
    verified_by,
    'created',
    NULL,
    jsonb_build_object(
        'rule_code', rule_code,
        'rule_name', rule_name,
        'trigger_type', trigger_type,
        'authority_tier', authority_tier,
        'citation', citation,
        'source_url', source_url,
        'source_text', source_text,
        'deadlines', deadlines,
        'conditions', conditions,
        'service_extensions', service_extensions,
        'confidence_score', confidence_score,
        'is_verified', is_verified,
        'is_active', is_active,
        'effective_date', effective_date,
        'superseded_date', superseded_date
    ),
    NULL,
    created_at
FROM authority_rules
WHERE NOT EXISTS (
    SELECT 1 FROM authority_rule_history h WHERE h.rule_id = authority_rules.id
);

-- ============================================================================
-- 6. Add helper function to get rule at specific version
-- ============================================================================

CREATE OR REPLACE FUNCTION get_authority_rule_at_version(
    p_rule_id VARCHAR(36),
    p_version INTEGER
) RETURNS JSONB AS $$
DECLARE
    v_data JSONB;
BEGIN
    SELECT new_data INTO v_data
    FROM authority_rule_history
    WHERE rule_id = p_rule_id AND version = p_version;

    RETURN v_data;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 7. Add helper function to get rule change diff
-- ============================================================================

CREATE OR REPLACE FUNCTION get_authority_rule_diff(
    p_rule_id VARCHAR(36),
    p_from_version INTEGER,
    p_to_version INTEGER
) RETURNS TABLE (
    field_name TEXT,
    old_value JSONB,
    new_value JSONB
) AS $$
DECLARE
    v_from_data JSONB;
    v_to_data JSONB;
    v_key TEXT;
BEGIN
    SELECT new_data INTO v_from_data
    FROM authority_rule_history
    WHERE rule_id = p_rule_id AND version = p_from_version;

    SELECT new_data INTO v_to_data
    FROM authority_rule_history
    WHERE rule_id = p_rule_id AND version = p_to_version;

    FOR v_key IN SELECT jsonb_object_keys(v_to_data)
    LOOP
        IF v_from_data->v_key IS DISTINCT FROM v_to_data->v_key THEN
            RETURN QUERY SELECT
                v_key,
                v_from_data->v_key,
                v_to_data->v_key;
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Migration complete
-- ============================================================================
