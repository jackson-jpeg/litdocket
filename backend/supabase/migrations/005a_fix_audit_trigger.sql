-- ============================================
-- FIX: Audit Trigger Ambiguous Column Reference
-- ============================================
-- The original audit_trigger_func() has ambiguous "key" references
-- when using jsonb_each(). This fixes the issue.

CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
DECLARE
    v_old_values JSONB;
    v_new_values JSONB;
    v_changed_fields TEXT[];
    v_previous_hash TEXT;
    v_new_hash TEXT;
    v_sequence_number INTEGER;
BEGIN
    -- Get previous hash for chain integrity
    SELECT current_hash, sequence_number INTO v_previous_hash, v_sequence_number
    FROM audit_log
    WHERE record_id = COALESCE(NEW.id, OLD.id)::TEXT
      AND table_name = TG_TABLE_NAME
    ORDER BY sequence_number DESC
    LIMIT 1;

    -- Initialize sequence
    v_sequence_number := COALESCE(v_sequence_number, 0) + 1;

    -- Handle different operations
    IF TG_OP = 'DELETE' THEN
        v_old_values := to_jsonb(OLD);
        v_new_values := NULL;
        v_changed_fields := ARRAY(SELECT jsonb_object_keys(v_old_values));
    ELSIF TG_OP = 'INSERT' THEN
        v_old_values := NULL;
        v_new_values := to_jsonb(NEW);
        v_changed_fields := ARRAY(SELECT jsonb_object_keys(v_new_values));
    ELSIF TG_OP = 'UPDATE' THEN
        v_old_values := to_jsonb(OLD);
        v_new_values := to_jsonb(NEW);
        -- Find changed fields with proper aliasing to avoid ambiguity
        SELECT array_agg(changed_key) INTO v_changed_fields
        FROM (
            SELECT old_kv.key AS changed_key FROM jsonb_each(v_old_values) AS old_kv
            EXCEPT
            SELECT new_kv.key FROM jsonb_each(v_new_values) AS new_kv
            UNION
            SELECT new_kv.key FROM jsonb_each(v_new_values) AS new_kv
            EXCEPT
            SELECT old_kv.key FROM jsonb_each(v_old_values) AS old_kv
            UNION
            SELECT old_kv.key FROM jsonb_each(v_old_values) AS old_kv
            JOIN jsonb_each(v_new_values) AS new_kv ON old_kv.key = new_kv.key
            WHERE old_kv.value IS DISTINCT FROM new_kv.value
        ) AS changed;
    END IF;

    -- Generate cryptographic hash for chain integrity
    v_new_hash := encode(
        sha256(
            (COALESCE(v_previous_hash, 'GENESIS') ||
             TG_OP ||
             TG_TABLE_NAME ||
             COALESCE(NEW.id, OLD.id)::TEXT ||
             v_sequence_number::TEXT ||
             COALESCE(v_old_values::TEXT, '') ||
             COALESCE(v_new_values::TEXT, ''))::bytea
        ),
        'hex'
    );

    -- Insert audit record
    INSERT INTO audit_log (
        table_name,
        record_id,
        operation,
        old_values,
        new_values,
        changed_fields,
        previous_hash,
        current_hash,
        sequence_number,
        performed_by,
        performed_at,
        ip_address,
        user_agent
    ) VALUES (
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id)::TEXT,
        TG_OP,
        v_old_values,
        v_new_values,
        v_changed_fields,
        v_previous_hash,
        v_new_hash,
        v_sequence_number,
        COALESCE(current_setting('app.current_user_id', true), 'system'),
        NOW(),
        current_setting('app.client_ip', true),
        current_setting('app.user_agent', true)
    );

    -- Return appropriate value
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

SELECT 'Audit trigger fixed' AS status;
