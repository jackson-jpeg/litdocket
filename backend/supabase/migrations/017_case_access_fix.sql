-- Migration: 017_case_access_fix.sql
-- Description: Fix CaseAccess model - add is_active column and updated_at
-- Part of: Case Sharing & Multi-User Collaboration (Feature 3)

-- ============================================================================
-- Fix CaseAccess Table
-- ============================================================================
-- The WebSocket middleware references CaseAccess.is_active which doesn't exist.
-- This migration adds the missing columns and indexes.

-- Add is_active column if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'case_access' AND column_name = 'is_active') THEN
        ALTER TABLE case_access ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
    END IF;
END $$;

-- Add updated_at column if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'case_access' AND column_name = 'updated_at') THEN
        ALTER TABLE case_access ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
    END IF;
END $$;

-- Add invited_email column (for invites before user registration)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'case_access' AND column_name = 'invited_email') THEN
        ALTER TABLE case_access ADD COLUMN invited_email VARCHAR(255);
    END IF;
END $$;

-- Add invitation_accepted_at column
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'case_access' AND column_name = 'invitation_accepted_at') THEN
        ALTER TABLE case_access ADD COLUMN invitation_accepted_at TIMESTAMPTZ;
    END IF;
END $$;

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Index for active access lookup (used by WebSocket middleware)
CREATE INDEX IF NOT EXISTS idx_case_access_active
ON case_access(case_id, user_id, is_active)
WHERE is_active = TRUE;

-- Index for finding user's shared cases
CREATE INDEX IF NOT EXISTS idx_case_access_user_active
ON case_access(user_id, is_active)
WHERE is_active = TRUE;

-- Index for pending invitations by email
CREATE INDEX IF NOT EXISTS idx_case_access_invited_email
ON case_access(invited_email)
WHERE invited_email IS NOT NULL AND user_id IS NULL;

-- ============================================================================
-- Trigger for updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION update_case_access_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS case_access_updated_at ON case_access;

CREATE TRIGGER case_access_updated_at
    BEFORE UPDATE ON case_access
    FOR EACH ROW
    EXECUTE FUNCTION update_case_access_updated_at();

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON COLUMN case_access.is_active IS 'Whether the access grant is currently active (false = revoked)';
COMMENT ON COLUMN case_access.invited_email IS 'Email address for pending invitations (before user accepts)';
COMMENT ON COLUMN case_access.invitation_accepted_at IS 'When the user accepted the invitation';
