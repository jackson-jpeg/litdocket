-- Migration 021: Phase 7 Step 11 - Proposals Table for AI Safety Rails
--
-- Purpose: Implement proposal/approval workflow to prevent AI from writing directly to database
--
-- Safety Benefits:
-- - Prevents AI from corrupting data with incorrect actions
-- - Provides undo capability (reject proposal)
-- - Creates audit trail of AI actions
-- - Gives user final control over database changes
--
-- Workflow:
-- 1. AI wants to create/update/delete data
-- 2. AI creates Proposal (not actual data)
-- 3. Frontend shows proposal to user with [Approve] [Reject] buttons
-- 4. User approves → API executes action and marks proposal approved
-- 5. User rejects → API marks proposal rejected (no action taken)

-- Create enum for proposal action types
CREATE TYPE proposal_action_type AS ENUM (
    'create_deadline',
    'update_deadline',
    'delete_deadline',
    'move_deadline',
    'update_case',
    'add_party',
    'remove_party',
    'upload_document'
);

-- Create enum for proposal status (if not exists from earlier migrations)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'proposal_status') THEN
        CREATE TYPE proposal_status AS ENUM ('pending', 'approved', 'rejected', 'needs_revision');
    END IF;
END$$;

-- Create proposals table
CREATE TABLE IF NOT EXISTS proposals (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- What action is being proposed
    action_type proposal_action_type NOT NULL,
    action_data JSONB NOT NULL,  -- The proposed changes (deadline data, case updates, etc.)

    -- AI reasoning and context
    ai_reasoning TEXT,  -- Why AI proposed this action
    ai_message_id VARCHAR(36),  -- Reference to the chat message that triggered this
    conversation_context JSONB,  -- Relevant context from the conversation

    -- Approval workflow
    status proposal_status NOT NULL DEFAULT 'pending',

    -- Resolution tracking
    resolved_by VARCHAR(36) REFERENCES users(id),  -- User who approved/rejected
    resolved_at TIMESTAMPTZ,  -- When was it resolved
    resolution_notes TEXT,  -- Optional user notes on approval/rejection

    -- Result tracking (for approved proposals)
    executed_successfully VARCHAR(10),  -- 'true'/'false'/null (string to avoid type issues)
    execution_error TEXT,  -- Error message if execution failed
    created_resource_id VARCHAR(36),  -- ID of created deadline/document/etc (if applicable)

    -- Preview data (shown to user before approval)
    preview_summary TEXT,  -- Human-readable summary: "Create Trial Date deadline on June 15, 2026"
    affected_items JSONB,  -- List of items that will be affected (e.g., cascaded deadlines)

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_proposals_case_id ON proposals(case_id);
CREATE INDEX IF NOT EXISTS idx_proposals_user_id ON proposals(user_id);
CREATE INDEX IF NOT EXISTS idx_proposals_status ON proposals(status);
CREATE INDEX IF NOT EXISTS idx_proposals_action_type ON proposals(action_type);
CREATE INDEX IF NOT EXISTS idx_proposals_created_at ON proposals(created_at DESC);

-- Create composite index for user's pending proposals
CREATE INDEX IF NOT EXISTS idx_proposals_user_pending ON proposals(user_id, status) WHERE status = 'pending';

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_proposals_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_proposals_updated_at
    BEFORE UPDATE ON proposals
    FOR EACH ROW
    EXECUTE FUNCTION update_proposals_updated_at();

-- Add comment
COMMENT ON TABLE proposals IS 'Phase 7 Step 11: AI-proposed actions awaiting user approval. Prevents AI from writing directly to database.';

-- Grant permissions (adjust based on your RLS setup)
ALTER TABLE proposals ENABLE ROW LEVEL SECURITY;

-- Policy: Users can see their own proposals
CREATE POLICY proposals_user_access ON proposals
    FOR ALL
    USING (user_id = current_setting('app.current_user_id', TRUE)::VARCHAR);

-- Policy: Users with case access can see proposals for that case
CREATE POLICY proposals_case_access ON proposals
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM case_access
            WHERE case_access.case_id = proposals.case_id
            AND case_access.user_id = current_setting('app.current_user_id', TRUE)::VARCHAR
            AND case_access.access_revoked_at IS NULL
        )
    );

-- Verify migration
DO $$
BEGIN
    RAISE NOTICE '✅ Migration 021 complete: proposals table created with % columns',
        (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'proposals');
END$$;
