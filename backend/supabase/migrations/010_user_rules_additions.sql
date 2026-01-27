-- Migration: Additional fields for user rules system
-- Adds columns needed by the rules API that weren't in migration 009

-- Add dry_run column to rule_executions if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'rule_executions' AND column_name = 'dry_run'
    ) THEN
        ALTER TABLE rule_executions ADD COLUMN dry_run BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- Add errors column for array of error messages
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'rule_executions' AND column_name = 'errors'
    ) THEN
        ALTER TABLE rule_executions ADD COLUMN errors JSONB;
    END IF;
END $$;

-- Make trigger_data nullable if it isn't already (needed for some execution scenarios)
ALTER TABLE rule_executions ALTER COLUMN trigger_data DROP NOT NULL;

-- Make rule_version_id nullable (needed if version is deleted)
ALTER TABLE rule_executions ALTER COLUMN rule_version_id DROP NOT NULL;

-- Add index for efficient marketplace queries
CREATE INDEX IF NOT EXISTS idx_rule_templates_public_active
    ON rule_templates(is_public, status)
    WHERE is_public = TRUE;

-- Add index for user's own rules
CREATE INDEX IF NOT EXISTS idx_rule_templates_created_by_status
    ON rule_templates(created_by, status);

COMMENT ON COLUMN rule_executions.dry_run IS 'If true, this was a preview execution that did not create actual deadlines';
COMMENT ON COLUMN rule_executions.errors IS 'Array of error messages if execution had issues';
