-- Migration 020: Rules Harvester Integration
-- Adds scraper health tracking, watchtower monitoring, inbox system, and complexity scoring
-- Based on patterns from RulesHarvester project

-- ============================================================================
-- PART 1: Enhance Jurisdictions with Scraper Configuration
-- ============================================================================

-- Add scraper configuration and health tracking fields to jurisdictions
ALTER TABLE jurisdictions ADD COLUMN IF NOT EXISTS scraper_config JSONB DEFAULT NULL;
ALTER TABLE jurisdictions ADD COLUMN IF NOT EXISTS auto_sync_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE jurisdictions ADD COLUMN IF NOT EXISTS sync_frequency VARCHAR(20) DEFAULT 'WEEKLY';
ALTER TABLE jurisdictions ADD COLUMN IF NOT EXISTS consecutive_scrape_failures INTEGER DEFAULT 0;
ALTER TABLE jurisdictions ADD COLUMN IF NOT EXISTS last_scrape_error TEXT DEFAULT NULL;
ALTER TABLE jurisdictions ADD COLUMN IF NOT EXISTS last_successful_scrape TIMESTAMP WITH TIME ZONE DEFAULT NULL;
ALTER TABLE jurisdictions ADD COLUMN IF NOT EXISTS scraper_config_version INTEGER DEFAULT 1;

-- Add Cartographer discovery metadata
ALTER TABLE jurisdictions ADD COLUMN IF NOT EXISTS discovery_source VARCHAR(50) DEFAULT NULL;
ALTER TABLE jurisdictions ADD COLUMN IF NOT EXISTS discovery_score NUMERIC(5,2) DEFAULT NULL;
ALTER TABLE jurisdictions ADD COLUMN IF NOT EXISTS discovery_url TEXT DEFAULT NULL;
ALTER TABLE jurisdictions ADD COLUMN IF NOT EXISTS discovery_query TEXT DEFAULT NULL;
ALTER TABLE jurisdictions ADD COLUMN IF NOT EXISTS discovered_at TIMESTAMP WITH TIME ZONE DEFAULT NULL;
ALTER TABLE jurisdictions ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP WITH TIME ZONE DEFAULT NULL;
ALTER TABLE jurisdictions ADD COLUMN IF NOT EXISTS approved_by VARCHAR(36) DEFAULT NULL;
ALTER TABLE jurisdictions ADD COLUMN IF NOT EXISTS rejected_at TIMESTAMP WITH TIME ZONE DEFAULT NULL;
ALTER TABLE jurisdictions ADD COLUMN IF NOT EXISTS rejection_reason TEXT DEFAULT NULL;

-- Add foreign key for approved_by
ALTER TABLE jurisdictions ADD CONSTRAINT fk_jurisdictions_approved_by
  FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL;

-- Add check constraint for sync_frequency
ALTER TABLE jurisdictions ADD CONSTRAINT chk_sync_frequency
  CHECK (sync_frequency IN ('DAILY', 'WEEKLY', 'MANUAL_ONLY'));

-- Add index for auto-sync queries
CREATE INDEX IF NOT EXISTS idx_jurisdictions_auto_sync
  ON jurisdictions(auto_sync_enabled, sync_frequency)
  WHERE auto_sync_enabled = TRUE;

CREATE INDEX IF NOT EXISTS idx_jurisdictions_discovery
  ON jurisdictions(discovery_score DESC, discovered_at DESC)
  WHERE discovery_score IS NOT NULL;

-- ============================================================================
-- PART 2: Enhance Authority Rules with Versioning and Complexity
-- ============================================================================

-- Add complexity scoring, version tracking, and raw text for change detection
ALTER TABLE authority_rules ADD COLUMN IF NOT EXISTS raw_text TEXT DEFAULT NULL;
ALTER TABLE authority_rules ADD COLUMN IF NOT EXISTS complexity INTEGER DEFAULT NULL;
ALTER TABLE authority_rules ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;
ALTER TABLE authority_rules ADD COLUMN IF NOT EXISTS previous_raw_text TEXT DEFAULT NULL;

-- Add check constraint for complexity (1-10 scale)
ALTER TABLE authority_rules ADD CONSTRAINT chk_complexity_range
  CHECK (complexity IS NULL OR (complexity >= 1 AND complexity <= 10));

-- Add index for complexity-based queries
CREATE INDEX IF NOT EXISTS idx_authority_rules_complexity
  ON authority_rules(complexity)
  WHERE complexity IS NOT NULL;

-- ============================================================================
-- PART 3: Watchtower Hash Tracking
-- ============================================================================

-- Create table for watchtower content hashes
CREATE TABLE IF NOT EXISTS watchtower_hashes (
  id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
  jurisdiction_id VARCHAR(36) NOT NULL REFERENCES jurisdictions(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  content_hash VARCHAR(64) NOT NULL,
  checked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  -- Prevent duplicate entries for same jurisdiction + URL
  CONSTRAINT unique_watchtower_hash UNIQUE (jurisdiction_id, url)
);

CREATE INDEX IF NOT EXISTS idx_watchtower_hashes_jurisdiction
  ON watchtower_hashes(jurisdiction_id, checked_at DESC);

-- ============================================================================
-- PART 4: Unified Inbox System
-- ============================================================================

-- Create inbox item types enum
DO $$ BEGIN
  CREATE TYPE inbox_item_type AS ENUM (
    'JURISDICTION_APPROVAL',
    'RULE_VERIFICATION',
    'WATCHTOWER_CHANGE',
    'SCRAPER_FAILURE',
    'CONFLICT_RESOLUTION'
  );
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

-- Create inbox status enum
DO $$ BEGIN
  CREATE TYPE inbox_status AS ENUM (
    'PENDING',
    'REVIEWED',
    'DEFERRED'
  );
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

-- Create inbox items table
CREATE TABLE IF NOT EXISTS inbox_items (
  id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
  type inbox_item_type NOT NULL,
  status inbox_status DEFAULT 'PENDING' NOT NULL,
  title VARCHAR(255) NOT NULL,
  description TEXT,

  -- Polymorphic references (only one should be set based on type)
  jurisdiction_id VARCHAR(36) REFERENCES jurisdictions(id) ON DELETE CASCADE,
  rule_id VARCHAR(36) REFERENCES authority_rules(id) ON DELETE CASCADE,
  conflict_id VARCHAR(36) REFERENCES rule_conflicts(id) ON DELETE CASCADE,
  scrape_job_id VARCHAR(36) REFERENCES scrape_jobs(id) ON DELETE CASCADE,

  -- Metadata
  confidence NUMERIC(5,2),
  source_url TEXT,
  item_metadata JSONB DEFAULT '{}',

  -- Workflow tracking
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  reviewed_at TIMESTAMP WITH TIME ZONE,
  reviewed_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
  resolution VARCHAR(50), -- 'approved', 'rejected', 'deferred'
  resolution_notes TEXT
);

-- Add indexes for inbox queries
CREATE INDEX IF NOT EXISTS idx_inbox_items_type_status
  ON inbox_items(type, status);

CREATE INDEX IF NOT EXISTS idx_inbox_items_status
  ON inbox_items(status);

CREATE INDEX IF NOT EXISTS idx_inbox_items_created
  ON inbox_items(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_inbox_items_pending
  ON inbox_items(type, created_at DESC)
  WHERE status = 'PENDING';

-- Add foreign key for reviewed_by
ALTER TABLE inbox_items ADD CONSTRAINT fk_inbox_items_reviewed_by
  FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL;

-- ============================================================================
-- PART 5: Scraper Health Logs
-- ============================================================================

-- Create scraper health log table for tracking failures and recoveries
CREATE TABLE IF NOT EXISTS scraper_health_logs (
  id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
  jurisdiction_id VARCHAR(36) NOT NULL REFERENCES jurisdictions(id) ON DELETE CASCADE,
  event_type VARCHAR(50) NOT NULL, -- 'failure', 'recovery', 'config_update', 'rediscovery'
  error_message TEXT,
  scraper_config_version INTEGER NOT NULL,
  consecutive_failures INTEGER DEFAULT 0,
  event_metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scraper_health_logs_jurisdiction
  ON scraper_health_logs(jurisdiction_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_scraper_health_logs_event_type
  ON scraper_health_logs(event_type);

-- ============================================================================
-- PART 6: Add Comments for Documentation
-- ============================================================================

COMMENT ON COLUMN jurisdictions.scraper_config IS 'AI-discovered CSS selectors for web scraping (JSON)';
COMMENT ON COLUMN jurisdictions.auto_sync_enabled IS 'Enable automatic watchtower monitoring';
COMMENT ON COLUMN jurisdictions.sync_frequency IS 'How often to check for updates: DAILY, WEEKLY, MANUAL_ONLY';
COMMENT ON COLUMN jurisdictions.consecutive_scrape_failures IS 'Counter for self-healing pipeline (auto-disable after 3)';
COMMENT ON COLUMN jurisdictions.scraper_config_version IS 'Increment when selectors are rediscovered';
COMMENT ON COLUMN jurisdictions.discovery_source IS 'How this jurisdiction was found (claude_web_search, manual)';
COMMENT ON COLUMN jurisdictions.discovery_score IS 'AI confidence in discovered jurisdiction (0-100)';

COMMENT ON COLUMN authority_rules.complexity IS 'Rule complexity score (1-10) for tiered AI processing';
COMMENT ON COLUMN authority_rules.version IS 'Version number for change tracking';
COMMENT ON COLUMN authority_rules.previous_raw_text IS 'Previous version of rule text for diff generation';

COMMENT ON TABLE watchtower_hashes IS 'Content hashes for watchtower change detection';
COMMENT ON TABLE inbox_items IS 'Unified approval workflow for all pending items';
COMMENT ON TABLE scraper_health_logs IS 'Audit trail for scraper health and self-healing';

-- ============================================================================
-- PART 7: Create Helper Functions
-- ============================================================================

-- Function to increment scraper failure counter
CREATE OR REPLACE FUNCTION increment_scraper_failure(p_jurisdiction_id VARCHAR(36), p_error_message TEXT)
RETURNS VOID AS $$
BEGIN
  UPDATE jurisdictions
  SET
    consecutive_scrape_failures = consecutive_scrape_failures + 1,
    last_scrape_error = p_error_message
  WHERE id = p_jurisdiction_id;

  -- Auto-disable after 3 consecutive failures
  UPDATE jurisdictions
  SET auto_sync_enabled = FALSE
  WHERE id = p_jurisdiction_id
    AND consecutive_scrape_failures >= 3;
END;
$$ LANGUAGE plpgsql;

-- Function to reset scraper failure counter on success
CREATE OR REPLACE FUNCTION reset_scraper_failures(p_jurisdiction_id VARCHAR(36))
RETURNS VOID AS $$
BEGIN
  UPDATE jurisdictions
  SET
    consecutive_scrape_failures = 0,
    last_scrape_error = NULL,
    last_successful_scrape = NOW()
  WHERE id = p_jurisdiction_id;
END;
$$ LANGUAGE plpgsql;

-- Function to create inbox item for scraper failure
CREATE OR REPLACE FUNCTION create_scraper_failure_inbox_item(
  p_jurisdiction_id VARCHAR(36),
  p_error_message TEXT
)
RETURNS VARCHAR(36) AS $$
DECLARE
  v_inbox_id VARCHAR(36);
  v_jurisdiction_name VARCHAR(255);
BEGIN
  -- Get jurisdiction name
  SELECT name INTO v_jurisdiction_name
  FROM jurisdictions
  WHERE id = p_jurisdiction_id;

  -- Create inbox item
  INSERT INTO inbox_items (
    type,
    status,
    title,
    description,
    jurisdiction_id,
    item_metadata
  ) VALUES (
    'SCRAPER_FAILURE',
    'PENDING',
    'Scraper Failure: ' || v_jurisdiction_name,
    'Scraper has failed 3 consecutive times. Manual intervention required.',
    p_jurisdiction_id,
    jsonb_build_object(
      'error_message', p_error_message,
      'timestamp', NOW()
    )
  )
  RETURNING id INTO v_inbox_id;

  RETURN v_inbox_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- PART 8: Data Migration - Link Existing Proposals to Inbox
-- ============================================================================

-- Create inbox items for pending rule proposals (only if table exists)
DO $$
BEGIN
  IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'rule_proposals') THEN
    INSERT INTO inbox_items (
      type,
      status,
      title,
      description,
      rule_id,
      confidence,
      source_url,
      item_metadata,
      created_at
    )
    SELECT
      'RULE_VERIFICATION' as type,
      CASE
        WHEN p.status = 'pending' THEN 'PENDING'::inbox_status
        WHEN p.status = 'approved' THEN 'REVIEWED'::inbox_status
        ELSE 'REVIEWED'::inbox_status
      END as status,
      'Rule Proposal: ' || COALESCE(p.proposed_rule_data->>'rule_name', 'Unknown Rule') as title,
      p.extraction_notes as description,
      p.approved_rule_id as rule_id,
      p.confidence_score as confidence,
      p.source_url,
      jsonb_build_object(
        'proposal_id', p.id,
        'jurisdiction_id', p.jurisdiction_id,
        'rule_code', COALESCE(p.proposed_rule_data->>'rule_code', '')
      ) as item_metadata,
      p.created_at
    FROM rule_proposals p
    WHERE NOT EXISTS (
      SELECT 1 FROM inbox_items i
      WHERE i.item_metadata->>'proposal_id' = p.id
    )
    ON CONFLICT DO NOTHING;

    RAISE NOTICE 'Migrated existing rule proposals to inbox';
  ELSE
    RAISE NOTICE 'Skipped rule_proposals migration - table does not exist';
  END IF;
END $$;

-- ============================================================================
-- PART 9: Grants and Permissions
-- ============================================================================

-- Grant permissions on new tables (adjust role as needed)
GRANT SELECT, INSERT, UPDATE, DELETE ON watchtower_hashes TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON inbox_items TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON scraper_health_logs TO authenticated;

-- ============================================================================
-- PART 10: Success Message
-- ============================================================================

DO $$
BEGIN
  RAISE NOTICE '✅ Migration 020 complete: Rules Harvester Integration';
  RAISE NOTICE '   - Added scraper configuration to jurisdictions';
  RAISE NOTICE '   - Added complexity scoring to authority_rules';
  RAISE NOTICE '   - Created watchtower_hashes table';
  RAISE NOTICE '   - Created inbox_items table (unified approval workflow)';
  RAISE NOTICE '   - Created scraper_health_logs table';
  RAISE NOTICE '   - Added helper functions for scraper health tracking';
  RAISE NOTICE '   - Migrated existing proposals to inbox';
END $$;
