-- Migration: Fix deadline_chains table schema
-- Add missing columns that the ORM expects

-- First, check if deadline_chains table exists, create if not
CREATE TABLE IF NOT EXISTS deadline_chains (
    id VARCHAR(36) PRIMARY KEY,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    parent_deadline_id VARCHAR(36) NOT NULL REFERENCES deadlines(id) ON DELETE CASCADE
);

-- Add missing columns to deadline_chains
ALTER TABLE deadline_chains
ADD COLUMN IF NOT EXISTS trigger_code VARCHAR(10),
ADD COLUMN IF NOT EXISTS trigger_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS template_id VARCHAR(36),
ADD COLUMN IF NOT EXISTS children_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_deadline_chains_case_id ON deadline_chains(case_id);
CREATE INDEX IF NOT EXISTS idx_deadline_chains_parent_deadline_id ON deadline_chains(parent_deadline_id);

-- Add foreign key for template_id if deadline_templates table exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'deadline_templates') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_name = 'fk_deadline_chains_template_id'
        ) THEN
            ALTER TABLE deadline_chains
            ADD CONSTRAINT fk_deadline_chains_template_id
            FOREIGN KEY (template_id)
            REFERENCES deadline_templates(id)
            ON DELETE SET NULL;
        END IF;
    END IF;
END $$;

-- ============================================
-- DEADLINE DEPENDENCIES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS deadline_dependencies (
    id VARCHAR(36) PRIMARY KEY,
    chain_id VARCHAR(36) REFERENCES deadline_chains(id) ON DELETE CASCADE,
    deadline_id VARCHAR(36) NOT NULL REFERENCES deadlines(id) ON DELETE CASCADE,
    depends_on_deadline_id VARCHAR(36) NOT NULL REFERENCES deadlines(id) ON DELETE CASCADE,
    offset_days INTEGER NOT NULL,
    offset_direction VARCHAR(10) NOT NULL,
    add_service_days BOOLEAN DEFAULT FALSE,
    auto_recalculate BOOLEAN DEFAULT TRUE,
    last_recalculated TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add indexes for deadline_dependencies
CREATE INDEX IF NOT EXISTS idx_deadline_dependencies_chain_id ON deadline_dependencies(chain_id);
CREATE INDEX IF NOT EXISTS idx_deadline_dependencies_deadline_id ON deadline_dependencies(deadline_id);
CREATE INDEX IF NOT EXISTS idx_deadline_dependencies_depends_on_deadline_id ON deadline_dependencies(depends_on_deadline_id);
