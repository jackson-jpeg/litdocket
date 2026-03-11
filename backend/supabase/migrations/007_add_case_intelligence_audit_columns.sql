-- Migration: Add soft-delete and audit columns to case intelligence tables
-- Adds deleted_at and updated_by columns to all tables in case_intelligence.py

-- ============================================
-- CASE HEALTH SCORES TABLE
-- ============================================
ALTER TABLE case_health_scores 
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS updated_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL;

-- ============================================
-- CASE PREDICTIONS TABLE
-- ============================================
ALTER TABLE case_predictions 
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS updated_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL;

-- ============================================
-- JUDGE PROFILES TABLE
-- ============================================
ALTER TABLE judge_profiles 
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS updated_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL;

-- ============================================
-- CASE EVENTS TABLE
-- ============================================
ALTER TABLE case_events 
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS updated_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL;

-- ============================================
-- DISCOVERY REQUESTS TABLE
-- ============================================
ALTER TABLE discovery_requests 
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS updated_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL;

-- ============================================
-- CASE FACTS TABLE
-- ============================================
ALTER TABLE case_facts 
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS updated_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL;

-- ============================================
-- BRIEF DRAFTS TABLE
-- ============================================
ALTER TABLE brief_drafts 
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS updated_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL;

-- ============================================
-- CREATE INDEXES FOR PERFORMANCE
-- ============================================
CREATE INDEX IF NOT EXISTS idx_case_health_scores_deleted_at ON case_health_scores(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_case_health_scores_updated_by ON case_health_scores(updated_by);

CREATE INDEX IF NOT EXISTS idx_case_predictions_deleted_at ON case_predictions(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_case_predictions_updated_by ON case_predictions(updated_by);

CREATE INDEX IF NOT EXISTS idx_judge_profiles_deleted_at ON judge_profiles(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_judge_profiles_updated_by ON judge_profiles(updated_by);

CREATE INDEX IF NOT EXISTS idx_case_events_deleted_at ON case_events(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_case_events_updated_by ON case_events(updated_by);

CREATE INDEX IF NOT EXISTS idx_discovery_requests_deleted_at ON discovery_requests(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_discovery_requests_updated_by ON discovery_requests(updated_by);

CREATE INDEX IF NOT EXISTS idx_case_facts_deleted_at ON case_facts(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_case_facts_updated_by ON case_facts(updated_by);

CREATE INDEX IF NOT EXISTS idx_brief_drafts_deleted_at ON brief_drafts(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_brief_drafts_updated_by ON brief_drafts(updated_by);

-- ============================================
-- ENABLE AUDIT TRIGGERS FOR NEW TABLES
-- ============================================
-- These tables may not exist yet, but when they do, they should be audited
-- The enable_audit_for_table function is defined in 003_ironclad_audit_system.sql

-- Enable auditing for case intelligence tables when they exist
SELECT enable_audit_for_table('case_health_scores');
SELECT enable_audit_for_table('case_predictions');
SELECT enable_audit_for_table('judge_profiles');
SELECT enable_audit_for_table('case_events');
SELECT enable_audit_for_table('discovery_requests');
SELECT enable_audit_for_table('case_facts');
SELECT enable_audit_for_table('brief_drafts');