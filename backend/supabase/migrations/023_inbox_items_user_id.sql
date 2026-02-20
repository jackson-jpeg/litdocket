-- Migration: 023_inbox_items_user_id.sql
-- Description: Add user_id column to inbox_items for IDOR prevention.
--   Every inbox item must belong to a user so queries can be scoped.
--
-- Safety: Uses IF NOT EXISTS / DO-block guard so migration is idempotent.

-- ============================================================================
-- PART 1: Add user_id column to inbox_items
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'inbox_items' AND column_name = 'user_id'
    ) THEN
        -- Add column as nullable first to avoid breaking existing rows
        ALTER TABLE inbox_items ADD COLUMN user_id VARCHAR(36);

        -- Set existing rows to 'system' (background job items)
        UPDATE inbox_items SET user_id = 'system' WHERE user_id IS NULL;

        -- Now make it NOT NULL
        ALTER TABLE inbox_items ALTER COLUMN user_id SET NOT NULL;

        -- Add foreign key constraint
        ALTER TABLE inbox_items ADD CONSTRAINT fk_inbox_items_user
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

        RAISE NOTICE 'Added user_id column to inbox_items';
    ELSE
        RAISE NOTICE 'user_id column already exists on inbox_items';
    END IF;
END $$;

-- ============================================================================
-- PART 2: Add index for user_id + status queries
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_inbox_items_user_status
    ON inbox_items (user_id, status);

-- ============================================================================
-- PART 3: Verification
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Migration 023 complete: inbox_items.user_id for IDOR prevention';
END $$;
