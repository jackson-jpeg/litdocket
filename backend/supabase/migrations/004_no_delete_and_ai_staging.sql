-- ============================================
-- NO-DELETE POLICY & AI STAGING AREA
-- "The Tombstone Pattern" + "Four-Eyes Guardrail"
-- ============================================
--
-- Layer III: No hard deletes - only soft archive with reason
-- Layer IV: AI proposes, Human approves
--
-- A deadline that was "deleted" is actually a deadline that was
-- "removed from the active calendar." We need to know it WAS there.

-- ============================================
-- DEADLINES TABLE (with archive support)
-- ============================================
-- Core deadline tracking with built-in soft delete

CREATE TABLE IF NOT EXISTS deadlines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Ownership
    user_id UUID NOT NULL,  -- References auth.users
    case_id UUID NOT NULL,  -- References cases table

    -- Core deadline data
    title TEXT NOT NULL,
    description TEXT,
    deadline_date DATE NOT NULL,
    deadline_time TIME,
    deadline_type TEXT,

    -- Rule linkage
    applicable_rule TEXT,
    rule_citation TEXT,
    rule_template_id UUID REFERENCES rule_templates(id),
    trigger_event_id UUID,  -- References trigger_events table

    -- Priority and status
    priority TEXT DEFAULT 'standard'
        CHECK (priority IN ('informational', 'standard', 'important', 'critical', 'fatal')),
    status TEXT DEFAULT 'pending'
        CHECK (status IN ('pending', 'completed', 'cancelled', 'archived')),

    -- Calculation metadata
    calculation_basis TEXT,
    days_from_trigger INTEGER,
    is_calculated BOOLEAN DEFAULT FALSE,
    is_manually_overridden BOOLEAN DEFAULT FALSE,

    -- Confidence (for AI-extracted deadlines)
    confidence_score DECIMAL(3,2),
    confidence_level TEXT CHECK (confidence_level IN ('low', 'medium', 'high')),
    verification_status TEXT DEFAULT 'pending'
        CHECK (verification_status IN ('pending', 'verified', 'rejected')),

    -- ============================================
    -- THE TOMBSTONE FIELDS
    -- ============================================
    -- These enable soft delete with full audit trail

    is_archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    archived_by UUID,  -- Who archived it
    archival_reason TEXT,  -- REQUIRED when archiving

    -- Standard timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Indexes for common queries
CREATE INDEX idx_deadlines_user ON deadlines(user_id);
CREATE INDEX idx_deadlines_case ON deadlines(case_id);
CREATE INDEX idx_deadlines_date ON deadlines(deadline_date);
CREATE INDEX idx_deadlines_status ON deadlines(status) WHERE status != 'archived';
CREATE INDEX idx_deadlines_active ON deadlines(user_id, deadline_date)
    WHERE is_archived = FALSE AND status = 'pending';

-- ============================================
-- RLS: BLOCK ALL DELETE OPERATIONS
-- ============================================
-- This is the core "No-Delete" enforcement

ALTER TABLE deadlines ENABLE ROW LEVEL SECURITY;

-- Users can see their own deadlines (including archived for history)
CREATE POLICY "Users can view own deadlines"
    ON deadlines FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

-- Users can INSERT their own deadlines
CREATE POLICY "Users can create own deadlines"
    ON deadlines FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());

-- Users can UPDATE their own deadlines
CREATE POLICY "Users can update own deadlines"
    ON deadlines FOR UPDATE
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- ============================================
-- CRITICAL: BLOCK DELETE FOR EVERYONE
-- ============================================
-- Even service_role must use archive_deadline()

CREATE POLICY "No deletes allowed - use archive_deadline()"
    ON deadlines FOR DELETE
    USING (FALSE);  -- Always fails

-- ============================================
-- THE ARCHIVE FUNCTION
-- ============================================
-- This is the ONLY way to "delete" a deadline

CREATE OR REPLACE FUNCTION archive_deadline(
    target_id UUID,
    reason TEXT
) RETURNS deadlines AS $$
DECLARE
    v_deadline deadlines;
    v_user_id UUID;
BEGIN
    -- Get current user
    v_user_id := auth.uid();

    -- Validate reason is provided
    IF reason IS NULL OR trim(reason) = '' THEN
        RAISE EXCEPTION 'Archival reason is required. Example: "Court rescheduled", "Entered in error"';
    END IF;

    -- Update the deadline (this will trigger audit logging)
    UPDATE deadlines
    SET
        status = 'archived',
        is_archived = TRUE,
        archived_at = NOW(),
        archived_by = v_user_id,
        archival_reason = reason,
        updated_at = NOW()
    WHERE id = target_id
      AND user_id = v_user_id  -- Security: only own deadlines
    RETURNING * INTO v_deadline;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Deadline not found or access denied';
    END IF;

    RETURN v_deadline;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- RESTORE ARCHIVED DEADLINE
-- ============================================
-- For when archives need to be restored

CREATE OR REPLACE FUNCTION restore_deadline(
    target_id UUID,
    restore_reason TEXT DEFAULT 'Restored from archive'
) RETURNS deadlines AS $$
DECLARE
    v_deadline deadlines;
    v_user_id UUID;
BEGIN
    v_user_id := auth.uid();

    UPDATE deadlines
    SET
        status = 'pending',
        is_archived = FALSE,
        archived_at = NULL,
        archived_by = NULL,
        archival_reason = NULL,
        updated_at = NOW()
    WHERE id = target_id
      AND user_id = v_user_id
      AND is_archived = TRUE
    RETURNING * INTO v_deadline;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Archived deadline not found or access denied';
    END IF;

    RETURN v_deadline;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- TRIGGER EVENTS TABLE
-- ============================================
-- Tracks the triggering events that generate deadlines

CREATE TABLE IF NOT EXISTS trigger_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Ownership
    user_id UUID NOT NULL,
    case_id UUID NOT NULL,

    -- Trigger data
    trigger_type TEXT NOT NULL,  -- 'trial_date', 'complaint_served', etc.
    trigger_date DATE NOT NULL,
    description TEXT,

    -- Source tracking
    source_document_id UUID,  -- Document that created this trigger
    source_type TEXT DEFAULT 'manual'
        CHECK (source_type IN ('manual', 'ai_extracted', 'system')),

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    archival_reason TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_trigger_events_case ON trigger_events(case_id);
CREATE INDEX idx_trigger_events_active ON trigger_events(case_id, trigger_type)
    WHERE is_active = TRUE;

-- Apply same RLS pattern
ALTER TABLE trigger_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own trigger events"
    ON trigger_events FOR SELECT TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Users can create own trigger events"
    ON trigger_events FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own trigger events"
    ON trigger_events FOR UPDATE TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "No deletes on trigger events"
    ON trigger_events FOR DELETE
    USING (FALSE);

-- ============================================
-- LAYER IV: AI STAGING AREA
-- "The Four-Eyes Guardrail"
-- ============================================
-- AI Agent NEVER writes to live tables. It proposes here.
-- Human must approve to commit changes.

CREATE TABLE IF NOT EXISTS pending_docket_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- What the AI wants to do
    action_type TEXT NOT NULL CHECK (action_type IN (
        'CREATE_DEADLINE',
        'UPDATE_DEADLINE',
        'CREATE_TRIGGER',
        'UPDATE_TRIGGER',
        'CREATE_CASE',
        'UPDATE_CASE',
        'LINK_DOCUMENT'
    )),

    -- Target information
    target_table TEXT NOT NULL,
    target_id UUID,  -- NULL for CREATE actions

    -- The proposed change
    payload JSONB NOT NULL,  -- Full data for the proposed action

    -- AI reasoning (for human review)
    confidence DECIMAL(3,2) NOT NULL,
    reasoning TEXT,  -- "Derived from Notice of Hearing, paragraph 2"
    source_document_id UUID,  -- Document that triggered this proposal
    source_text TEXT,  -- Extracted text that supports the action

    -- Ownership
    user_id UUID NOT NULL,  -- User who will own the resulting record
    case_id UUID,  -- Case context

    -- Status workflow
    status TEXT DEFAULT 'pending' CHECK (status IN (
        'pending',      -- Awaiting human review
        'approved',     -- Human approved, being committed
        'committed',    -- Successfully written to live table
        'rejected',     -- Human rejected
        'expired',      -- Auto-expired after timeout
        'error'         -- Commit failed
    )),

    -- Review tracking
    reviewed_by UUID,
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT,

    -- Result tracking
    committed_record_id UUID,  -- ID of the created/updated record
    commit_error TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '7 days'),

    -- AI agent tracking
    ai_agent_id TEXT,  -- Identifier for the AI agent/model
    ai_session_id TEXT,  -- Session that created this
    ai_request_id TEXT   -- Specific request ID for debugging
);

-- Indexes
CREATE INDEX idx_pending_actions_user ON pending_docket_actions(user_id);
CREATE INDEX idx_pending_actions_status ON pending_docket_actions(status, created_at DESC)
    WHERE status = 'pending';
CREATE INDEX idx_pending_actions_case ON pending_docket_actions(case_id);

-- RLS for pending actions
ALTER TABLE pending_docket_actions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own pending actions"
    ON pending_docket_actions FOR SELECT TO authenticated
    USING (user_id = auth.uid());

-- AI service role can INSERT proposals
CREATE POLICY "Service can create pending actions"
    ON pending_docket_actions FOR INSERT TO service_role
    WITH CHECK (TRUE);

-- Users can UPDATE (approve/reject) their own pending actions
CREATE POLICY "Users can review own pending actions"
    ON pending_docket_actions FOR UPDATE TO authenticated
    USING (user_id = auth.uid());

-- No deletes - keep audit trail
CREATE POLICY "No deletes on pending actions"
    ON pending_docket_actions FOR DELETE
    USING (FALSE);

-- ============================================
-- APPROVE PENDING ACTION FUNCTION
-- ============================================
-- Human approves an AI proposal, committing it to live tables

CREATE OR REPLACE FUNCTION approve_pending_action(
    action_id UUID,
    review_notes TEXT DEFAULT NULL
) RETURNS pending_docket_actions AS $$
DECLARE
    v_action pending_docket_actions;
    v_user_id UUID;
    v_new_id UUID;
BEGIN
    v_user_id := auth.uid();

    -- Lock and validate the action
    SELECT * INTO v_action
    FROM pending_docket_actions
    WHERE id = action_id
      AND user_id = v_user_id
      AND status = 'pending'
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Pending action not found, already processed, or access denied';
    END IF;

    -- Mark as approved (in progress)
    UPDATE pending_docket_actions
    SET
        status = 'approved',
        reviewed_by = v_user_id,
        reviewed_at = NOW(),
        review_notes = approve_pending_action.review_notes
    WHERE id = action_id;

    -- Execute the action based on type
    BEGIN
        CASE v_action.action_type
            WHEN 'CREATE_DEADLINE' THEN
                INSERT INTO deadlines (
                    user_id,
                    case_id,
                    title,
                    description,
                    deadline_date,
                    deadline_time,
                    deadline_type,
                    applicable_rule,
                    rule_citation,
                    priority,
                    calculation_basis,
                    confidence_score,
                    confidence_level,
                    verification_status
                )
                SELECT
                    v_user_id,
                    COALESCE((v_action.payload->>'case_id')::UUID, v_action.case_id),
                    v_action.payload->>'title',
                    v_action.payload->>'description',
                    (v_action.payload->>'deadline_date')::DATE,
                    (v_action.payload->>'deadline_time')::TIME,
                    v_action.payload->>'deadline_type',
                    v_action.payload->>'applicable_rule',
                    v_action.payload->>'rule_citation',
                    COALESCE(v_action.payload->>'priority', 'standard'),
                    v_action.payload->>'calculation_basis',
                    v_action.confidence,
                    CASE
                        WHEN v_action.confidence >= 0.9 THEN 'high'
                        WHEN v_action.confidence >= 0.7 THEN 'medium'
                        ELSE 'low'
                    END,
                    'verified'  -- Human approved = verified
                RETURNING id INTO v_new_id;

            WHEN 'CREATE_TRIGGER' THEN
                INSERT INTO trigger_events (
                    user_id,
                    case_id,
                    trigger_type,
                    trigger_date,
                    description,
                    source_document_id,
                    source_type
                )
                SELECT
                    v_user_id,
                    COALESCE((v_action.payload->>'case_id')::UUID, v_action.case_id),
                    v_action.payload->>'trigger_type',
                    (v_action.payload->>'trigger_date')::DATE,
                    v_action.payload->>'description',
                    v_action.source_document_id,
                    'ai_extracted'
                RETURNING id INTO v_new_id;

            -- Add more action types as needed
            ELSE
                RAISE EXCEPTION 'Unsupported action type: %', v_action.action_type;
        END CASE;

        -- Mark as committed
        UPDATE pending_docket_actions
        SET
            status = 'committed',
            committed_record_id = v_new_id
        WHERE id = action_id
        RETURNING * INTO v_action;

    EXCEPTION WHEN OTHERS THEN
        -- Mark as error
        UPDATE pending_docket_actions
        SET
            status = 'error',
            commit_error = SQLERRM
        WHERE id = action_id
        RETURNING * INTO v_action;

        RAISE;
    END;

    RETURN v_action;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- REJECT PENDING ACTION FUNCTION
-- ============================================

CREATE OR REPLACE FUNCTION reject_pending_action(
    action_id UUID,
    rejection_reason TEXT
) RETURNS pending_docket_actions AS $$
DECLARE
    v_action pending_docket_actions;
    v_user_id UUID;
BEGIN
    v_user_id := auth.uid();

    IF rejection_reason IS NULL OR trim(rejection_reason) = '' THEN
        RAISE EXCEPTION 'Rejection reason is required';
    END IF;

    UPDATE pending_docket_actions
    SET
        status = 'rejected',
        reviewed_by = v_user_id,
        reviewed_at = NOW(),
        review_notes = rejection_reason
    WHERE id = action_id
      AND user_id = v_user_id
      AND status = 'pending'
    RETURNING * INTO v_action;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Pending action not found or already processed';
    END IF;

    RETURN v_action;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- GET PENDING ACTIONS COUNT
-- ============================================
-- For the "Pending Approvals" indicator in the UI

CREATE OR REPLACE FUNCTION get_pending_actions_count()
RETURNS INTEGER AS $$
BEGIN
    RETURN (
        SELECT COUNT(*)
        FROM pending_docket_actions
        WHERE user_id = auth.uid()
          AND status = 'pending'
          AND expires_at > NOW()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- AUTO-EXPIRE OLD PENDING ACTIONS
-- ============================================
-- Run this periodically via pg_cron or external scheduler

CREATE OR REPLACE FUNCTION expire_old_pending_actions()
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    UPDATE pending_docket_actions
    SET status = 'expired'
    WHERE status = 'pending'
      AND expires_at < NOW();

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- ENABLE AUDITING ON NEW TABLES
-- ============================================

SELECT enable_audit_for_table('deadlines');
SELECT enable_audit_for_table('trigger_events');
SELECT enable_audit_for_table('pending_docket_actions');

-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON TABLE deadlines IS 'Deadline tracking with mandatory soft delete (no hard deletes allowed)';
COMMENT ON FUNCTION archive_deadline IS 'The ONLY way to remove a deadline - requires reason';
COMMENT ON TABLE pending_docket_actions IS 'AI staging area - proposals require human approval';
COMMENT ON FUNCTION approve_pending_action IS 'Human approves AI proposal, committing to live tables';
