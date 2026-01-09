-- ============================================
-- IRONCLAD AUDIT SYSTEM
-- "The Database is the Witness"
-- ============================================
-- Cryptographic Shadow Ledger with Hash Chaining
-- Creates tamper-evident audit trail for all critical tables
--
-- Features:
-- 1. SHA-256 hash chaining (micro-blockchain per record)
-- 2. Append-only audit log (no updates/deletes allowed)
-- 3. Full OLD/NEW state capture as JSONB
-- 4. Automatic trigger on all tracked tables

-- ============================================
-- ENABLE REQUIRED EXTENSIONS
-- ============================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- THE SHADOW LEDGER TABLE
-- ============================================
-- This is the immutable audit log. Every change to tracked tables
-- is recorded here with cryptographic proof of integrity.

CREATE TABLE IF NOT EXISTS audit_log (
    -- Identity
    id BIGSERIAL PRIMARY KEY,
    audit_id UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,

    -- What changed
    table_name TEXT NOT NULL,
    record_id UUID NOT NULL,
    operation TEXT NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),

    -- Who changed it
    changed_by UUID,  -- References auth.users(id) but not enforced for flexibility
    changed_by_type TEXT DEFAULT 'user' CHECK (changed_by_type IN ('user', 'system', 'ai_agent', 'migration')),
    session_id TEXT,  -- For tracking request context

    -- When
    changed_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- The data (JSONB for flexibility and queryability)
    old_values JSONB,
    new_values JSONB,

    -- Changed fields summary (for quick scanning)
    changed_fields TEXT[],

    -- ============================================
    -- THE CRYPTOGRAPHIC CHAIN
    -- ============================================
    -- This is what makes tampering detectable

    -- Hash of the previous audit entry for this specific record
    -- Creates a linked chain per record_id
    previous_audit_id UUID,
    previous_record_hash TEXT,

    -- SHA-256 hash of: table_name + record_id + operation + old_values + new_values + previous_record_hash
    -- If ANY of these change, the hash breaks the chain
    record_hash TEXT NOT NULL,

    -- Sequence number for this record (for easy ordering)
    record_sequence INTEGER NOT NULL DEFAULT 1,

    -- Metadata
    client_info JSONB DEFAULT '{}'::JSONB,  -- User agent, IP (hashed), etc.
    context_info JSONB DEFAULT '{}'::JSONB  -- Additional context (document_id, case_id, etc.)
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- Primary query: "Show me the history of this record"
CREATE INDEX idx_audit_record_history
    ON audit_log(record_id, changed_at DESC);

-- Query: "Show me all changes to this table today"
CREATE INDEX idx_audit_table_time
    ON audit_log(table_name, changed_at DESC);

-- Query: "Show me what this user changed"
CREATE INDEX idx_audit_user
    ON audit_log(changed_by, changed_at DESC);

-- Query: "Find audit entry by hash" (for verification)
CREATE INDEX idx_audit_hash
    ON audit_log(record_hash);

-- Query: "Chain integrity check"
CREATE INDEX idx_audit_chain
    ON audit_log(record_id, record_sequence);

-- ============================================
-- THE HASH CALCULATION FUNCTION
-- ============================================
-- Generates a SHA-256 hash of the audit record data
-- This creates the cryptographic link in the chain

CREATE OR REPLACE FUNCTION calculate_audit_hash(
    p_table_name TEXT,
    p_record_id UUID,
    p_operation TEXT,
    p_old_values JSONB,
    p_new_values JSONB,
    p_previous_hash TEXT
) RETURNS TEXT AS $$
DECLARE
    hash_input TEXT;
BEGIN
    -- Concatenate all relevant fields into a single string
    -- The order matters and must be consistent
    hash_input := COALESCE(p_table_name, '') || '|' ||
                  COALESCE(p_record_id::TEXT, '') || '|' ||
                  COALESCE(p_operation, '') || '|' ||
                  COALESCE(p_old_values::TEXT, 'NULL') || '|' ||
                  COALESCE(p_new_values::TEXT, 'NULL') || '|' ||
                  COALESCE(p_previous_hash, 'GENESIS');

    -- Return SHA-256 hash encoded as hex
    RETURN encode(digest(hash_input, 'sha256'), 'hex');
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================
-- THE AUDIT TRIGGER FUNCTION
-- ============================================
-- This is the core function that captures all changes

CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
DECLARE
    v_old_values JSONB;
    v_new_values JSONB;
    v_record_id UUID;
    v_operation TEXT;
    v_changed_fields TEXT[];
    v_previous_audit RECORD;
    v_previous_hash TEXT;
    v_previous_audit_id UUID;
    v_record_sequence INTEGER;
    v_record_hash TEXT;
    v_changed_by UUID;
    v_session_id TEXT;
BEGIN
    -- Determine operation type
    v_operation := TG_OP;

    -- Get the record ID and values based on operation
    IF TG_OP = 'DELETE' THEN
        v_record_id := OLD.id;
        v_old_values := to_jsonb(OLD);
        v_new_values := NULL;
        v_changed_fields := NULL;
    ELSIF TG_OP = 'INSERT' THEN
        v_record_id := NEW.id;
        v_old_values := NULL;
        v_new_values := to_jsonb(NEW);
        v_changed_fields := NULL;
    ELSIF TG_OP = 'UPDATE' THEN
        v_record_id := NEW.id;
        v_old_values := to_jsonb(OLD);
        v_new_values := to_jsonb(NEW);
        -- Calculate which fields changed
        SELECT array_agg(key) INTO v_changed_fields
        FROM (
            SELECT key FROM jsonb_each(v_old_values)
            EXCEPT
            SELECT key FROM jsonb_each(v_new_values)
            UNION
            SELECT key FROM jsonb_each(v_new_values)
            EXCEPT
            SELECT key FROM jsonb_each(v_old_values)
            UNION
            SELECT key FROM jsonb_each(v_old_values) o
            JOIN jsonb_each(v_new_values) n ON o.key = n.key
            WHERE o.value IS DISTINCT FROM n.value
        ) changed;
    END IF;

    -- Get the previous audit entry for this record (for hash chaining)
    SELECT audit_id, record_hash, record_sequence
    INTO v_previous_audit
    FROM audit_log
    WHERE record_id = v_record_id
    ORDER BY record_sequence DESC
    LIMIT 1;

    IF FOUND THEN
        v_previous_audit_id := v_previous_audit.audit_id;
        v_previous_hash := v_previous_audit.record_hash;
        v_record_sequence := v_previous_audit.record_sequence + 1;
    ELSE
        v_previous_audit_id := NULL;
        v_previous_hash := NULL;
        v_record_sequence := 1;
    END IF;

    -- Calculate the hash for this audit entry
    v_record_hash := calculate_audit_hash(
        TG_TABLE_NAME,
        v_record_id,
        v_operation,
        v_old_values,
        v_new_values,
        v_previous_hash
    );

    -- Try to get the current user from session variables
    -- These would be set by the application before each request
    BEGIN
        v_changed_by := current_setting('app.current_user_id', true)::UUID;
    EXCEPTION WHEN OTHERS THEN
        v_changed_by := NULL;
    END;

    BEGIN
        v_session_id := current_setting('app.session_id', true);
    EXCEPTION WHEN OTHERS THEN
        v_session_id := NULL;
    END;

    -- Insert the audit record
    INSERT INTO audit_log (
        table_name,
        record_id,
        operation,
        changed_by,
        changed_by_type,
        session_id,
        old_values,
        new_values,
        changed_fields,
        previous_audit_id,
        previous_record_hash,
        record_hash,
        record_sequence
    ) VALUES (
        TG_TABLE_NAME,
        v_record_id,
        v_operation,
        v_changed_by,
        COALESCE(current_setting('app.actor_type', true), 'user'),
        v_session_id,
        v_old_values,
        v_new_values,
        v_changed_fields,
        v_previous_audit_id,
        v_previous_hash,
        v_record_hash,
        v_record_sequence
    );

    -- Return appropriate value
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- HELPER: APPLY AUDIT TRIGGER TO A TABLE
-- ============================================
-- Call this function to add auditing to any table

CREATE OR REPLACE FUNCTION enable_audit_for_table(target_table TEXT)
RETURNS VOID AS $$
DECLARE
    trigger_name TEXT;
BEGIN
    trigger_name := 'audit_trigger_' || target_table;

    -- Drop existing trigger if present
    EXECUTE format('DROP TRIGGER IF EXISTS %I ON %I', trigger_name, target_table);

    -- Create the trigger
    EXECUTE format(
        'CREATE TRIGGER %I
         AFTER INSERT OR UPDATE OR DELETE ON %I
         FOR EACH ROW EXECUTE FUNCTION audit_trigger_func()',
        trigger_name,
        target_table
    );

    RAISE NOTICE 'Audit trigger enabled for table: %', target_table;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- CHAIN INTEGRITY VERIFICATION FUNCTION
-- ============================================
-- This function verifies the hash chain for a specific record
-- Returns TRUE if chain is intact, FALSE if tampering detected

CREATE OR REPLACE FUNCTION verify_audit_chain(p_record_id UUID)
RETURNS TABLE (
    is_valid BOOLEAN,
    total_entries INTEGER,
    broken_at_sequence INTEGER,
    error_message TEXT
) AS $$
DECLARE
    v_entry RECORD;
    v_expected_hash TEXT;
    v_previous_hash TEXT := NULL;
    v_count INTEGER := 0;
BEGIN
    is_valid := TRUE;
    broken_at_sequence := NULL;
    error_message := NULL;

    FOR v_entry IN
        SELECT * FROM audit_log
        WHERE record_id = p_record_id
        ORDER BY record_sequence ASC
    LOOP
        v_count := v_count + 1;

        -- Calculate what the hash SHOULD be
        v_expected_hash := calculate_audit_hash(
            v_entry.table_name,
            v_entry.record_id,
            v_entry.operation,
            v_entry.old_values,
            v_entry.new_values,
            v_previous_hash
        );

        -- Check if it matches
        IF v_entry.record_hash != v_expected_hash THEN
            is_valid := FALSE;
            broken_at_sequence := v_entry.record_sequence;
            error_message := format(
                'Hash mismatch at sequence %s. Expected: %s, Found: %s',
                v_entry.record_sequence,
                v_expected_hash,
                v_entry.record_hash
            );
            total_entries := v_count;
            RETURN NEXT;
            RETURN;
        END IF;

        -- Also verify the chain link
        IF v_entry.previous_record_hash IS DISTINCT FROM v_previous_hash THEN
            is_valid := FALSE;
            broken_at_sequence := v_entry.record_sequence;
            error_message := format(
                'Chain link broken at sequence %s. Previous hash mismatch.',
                v_entry.record_sequence
            );
            total_entries := v_count;
            RETURN NEXT;
            RETURN;
        END IF;

        v_previous_hash := v_entry.record_hash;
    END LOOP;

    total_entries := v_count;
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- FULL TABLE INTEGRITY CHECK
-- ============================================
-- Verify all records in a table

CREATE OR REPLACE FUNCTION verify_table_integrity(p_table_name TEXT)
RETURNS TABLE (
    record_id UUID,
    is_valid BOOLEAN,
    total_entries INTEGER,
    broken_at_sequence INTEGER,
    error_message TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT
        al.record_id,
        (v.is_valid),
        (v.total_entries),
        (v.broken_at_sequence),
        (v.error_message)
    FROM audit_log al
    CROSS JOIN LATERAL verify_audit_chain(al.record_id) v
    WHERE al.table_name = p_table_name;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- ROW LEVEL SECURITY: APPEND-ONLY AUDIT LOG
-- ============================================
-- The audit log is IMMUTABLE. No one can update or delete entries.
-- Only INSERT is allowed, and only through the trigger function.

ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- Allow everyone to READ audit logs (for their own records)
CREATE POLICY "Audit logs are readable by authenticated users"
    ON audit_log FOR SELECT
    TO authenticated
    USING (true);

-- Allow the service role to read everything
CREATE POLICY "Service role can read all audit logs"
    ON audit_log FOR SELECT
    TO service_role
    USING (true);

-- CRITICAL: Block ALL updates and deletes
-- Even service_role cannot modify audit entries
CREATE POLICY "No updates allowed on audit log"
    ON audit_log FOR UPDATE
    USING (false);

CREATE POLICY "No deletes allowed on audit log"
    ON audit_log FOR DELETE
    USING (false);

-- Only allow inserts through the trigger (SECURITY DEFINER)
-- Regular users cannot insert directly
CREATE POLICY "Inserts only through trigger"
    ON audit_log FOR INSERT
    TO authenticated
    WITH CHECK (false);  -- Block direct inserts from users

-- Service role can insert (for the trigger function)
CREATE POLICY "Service role can insert audit logs"
    ON audit_log FOR INSERT
    TO service_role
    WITH CHECK (true);

-- ============================================
-- APPLY AUDITING TO CRITICAL TABLES
-- ============================================
-- Enable auditing on all tables that matter for legal defensibility

-- Cases table
SELECT enable_audit_for_table('jurisdictions');
SELECT enable_audit_for_table('rule_sets');
SELECT enable_audit_for_table('rule_templates');
SELECT enable_audit_for_table('rule_template_deadlines');
SELECT enable_audit_for_table('case_rule_sets');

-- NOTE: Add these when the tables exist:
-- SELECT enable_audit_for_table('cases');
-- SELECT enable_audit_for_table('deadlines');
-- SELECT enable_audit_for_table('documents');

-- ============================================
-- GET RECORD HISTORY FUNCTION
-- ============================================
-- Easy way to retrieve the full audit history of a record

CREATE OR REPLACE FUNCTION get_record_history(
    p_record_id UUID,
    p_limit INTEGER DEFAULT 100
)
RETURNS TABLE (
    audit_id UUID,
    operation TEXT,
    changed_at TIMESTAMPTZ,
    changed_by UUID,
    changed_by_type TEXT,
    changed_fields TEXT[],
    old_values JSONB,
    new_values JSONB,
    record_sequence INTEGER,
    chain_valid BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    WITH verification AS (
        SELECT * FROM verify_audit_chain(p_record_id)
    )
    SELECT
        al.audit_id,
        al.operation,
        al.changed_at,
        al.changed_by,
        al.changed_by_type,
        al.changed_fields,
        al.old_values,
        al.new_values,
        al.record_sequence,
        v.is_valid as chain_valid
    FROM audit_log al
    CROSS JOIN verification v
    WHERE al.record_id = p_record_id
    ORDER BY al.record_sequence DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON TABLE audit_log IS 'Immutable cryptographic audit trail - The Shadow Ledger';
COMMENT ON COLUMN audit_log.record_hash IS 'SHA-256 hash creating tamper-evident chain';
COMMENT ON COLUMN audit_log.previous_record_hash IS 'Links to previous entry - breaks if tampered';
COMMENT ON FUNCTION verify_audit_chain IS 'Verifies cryptographic integrity of audit chain for a record';
COMMENT ON FUNCTION audit_trigger_func IS 'Core trigger function that captures all changes with hash chaining';
