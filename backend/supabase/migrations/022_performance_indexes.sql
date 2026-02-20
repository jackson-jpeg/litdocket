-- Migration: 022_performance_indexes.sql
-- Description: Add composite indexes for common query patterns and a unique
--   constraint on case_access to prevent duplicate invitations.
--
-- Safety: All statements use IF NOT EXISTS / DO-block guards so the migration
--   is idempotent and safe to re-run.

-- ============================================================================
-- PART 1: Composite Indexes for Deadline Queries
-- ============================================================================
-- These cover the morning report, case detail view, and calendar page which
-- all filter deadlines by (user_id, status) and sort by deadline_date.

CREATE INDEX IF NOT EXISTS idx_deadlines_user_status_date
    ON deadlines (user_id, status, deadline_date);

-- Case detail view and priority-sorted listings
CREATE INDEX IF NOT EXISTS idx_deadlines_case_priority_date
    ON deadlines (case_id, priority, deadline_date);

-- ============================================================================
-- PART 2: Composite Index for Document Queries
-- ============================================================================
-- Document listing within a case filtered by analysis status (pending,
-- processing, completed, failed, needs_ocr).

CREATE INDEX IF NOT EXISTS idx_documents_case_analysis
    ON documents (case_id, analysis_status);

-- ============================================================================
-- PART 3: Composite Index for Chat Message Queries
-- ============================================================================
-- Chat history is always loaded per-case ordered by creation time descending.

CREATE INDEX IF NOT EXISTS idx_chat_messages_case_created
    ON chat_messages (case_id, created_at DESC);

-- ============================================================================
-- PART 4: Composite Index for Authority Rules Lookup
-- ============================================================================
-- Rules engine filters by jurisdiction + active status when calculating
-- deadlines.  A similar index already exists that also includes trigger_type;
-- this narrower index supports the jurisdiction admin view.

CREATE INDEX IF NOT EXISTS idx_authority_rules_jurisdiction_active
    ON authority_rules (jurisdiction_id, is_active);

-- ============================================================================
-- PART 5: Unique Constraint on case_access (case_id, invited_email)
-- ============================================================================
-- Prevents duplicate invitations for the same case + email combination.
-- Uses a partial unique index so that rows with NULL invited_email are
-- excluded (NULL columns are not equal under SQL semantics, so a plain
-- UNIQUE constraint would allow duplicate NULLs anyway -- but a partial
-- index makes the intent explicit and keeps the index small).

CREATE UNIQUE INDEX IF NOT EXISTS uq_case_access_case_email
    ON case_access (case_id, invited_email)
    WHERE invited_email IS NOT NULL;

-- ============================================================================
-- PART 6: Verification
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Migration 022 complete: Performance indexes and CaseAccess unique constraint';
    RAISE NOTICE '  - idx_deadlines_user_status_date';
    RAISE NOTICE '  - idx_deadlines_case_priority_date';
    RAISE NOTICE '  - idx_documents_case_analysis';
    RAISE NOTICE '  - idx_chat_messages_case_created';
    RAISE NOTICE '  - idx_authority_rules_jurisdiction_active';
    RAISE NOTICE '  - uq_case_access_case_email (unique, partial)';
END $$;
