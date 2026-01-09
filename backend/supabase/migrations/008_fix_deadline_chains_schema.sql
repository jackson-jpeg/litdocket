-- Migration: Fix deadline_chains and deadline_dependencies table schemas
-- Add missing columns that the ORM expects

-- ============================================
-- DEADLINE CHAINS TABLE
-- ============================================

-- First, check if deadline_chains table exists, create if not
CREATE TABLE IF NOT EXISTS deadline_chains (
    id VARCHAR(36) PRIMARY KEY,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    parent_deadline_id VARCHAR(36) NOT NULL REFERENCES deadlines(id) ON DELETE CASCADE,
    trigger_code VARCHAR(10),
    trigger_type VARCHAR(50),
    template_id VARCHAR(36),
    children_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- If table already existed, add missing columns
DO $$
BEGIN
    -- Add trigger_code if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'deadline_chains' AND column_name = 'trigger_code'
    ) THEN
        ALTER TABLE deadline_chains ADD COLUMN trigger_code VARCHAR(10);
    END IF;

    -- Add trigger_type if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'deadline_chains' AND column_name = 'trigger_type'
    ) THEN
        ALTER TABLE deadline_chains ADD COLUMN trigger_type VARCHAR(50);
    END IF;

    -- Add template_id if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'deadline_chains' AND column_name = 'template_id'
    ) THEN
        ALTER TABLE deadline_chains ADD COLUMN template_id VARCHAR(36);
    END IF;

    -- Add children_count if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'deadline_chains' AND column_name = 'children_count'
    ) THEN
        ALTER TABLE deadline_chains ADD COLUMN children_count INTEGER DEFAULT 0;
    END IF;

    -- Add created_at if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'deadline_chains' AND column_name = 'created_at'
    ) THEN
        ALTER TABLE deadline_chains ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW();
    END IF;
END $$;

-- Add indexes for deadline_chains
CREATE INDEX IF NOT EXISTS idx_deadline_chains_case_id ON deadline_chains(case_id);
CREATE INDEX IF NOT EXISTS idx_deadline_chains_parent_deadline_id ON deadline_chains(parent_deadline_id);

-- Add foreign key for template_id if deadline_templates table exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'deadline_templates') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_name = 'fk_deadline_chains_template_id'
            AND table_name = 'deadline_chains'
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

-- Create deadline_dependencies table if not exists
CREATE TABLE IF NOT EXISTS deadline_dependencies (
    id VARCHAR(36) PRIMARY KEY,
    chain_id VARCHAR(36),
    deadline_id VARCHAR(36) NOT NULL,
    depends_on_deadline_id VARCHAR(36) NOT NULL,
    offset_days INTEGER NOT NULL,
    offset_direction VARCHAR(10) NOT NULL,
    add_service_days BOOLEAN DEFAULT FALSE,
    auto_recalculate BOOLEAN DEFAULT TRUE,
    last_recalculated TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- If table already existed, add missing columns
DO $$
BEGIN
    -- Add chain_id if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'deadline_dependencies' AND column_name = 'chain_id'
    ) THEN
        ALTER TABLE deadline_dependencies ADD COLUMN chain_id VARCHAR(36);
    END IF;

    -- Add offset_days if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'deadline_dependencies' AND column_name = 'offset_days'
    ) THEN
        ALTER TABLE deadline_dependencies ADD COLUMN offset_days INTEGER;
    END IF;

    -- Add offset_direction if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'deadline_dependencies' AND column_name = 'offset_direction'
    ) THEN
        ALTER TABLE deadline_dependencies ADD COLUMN offset_direction VARCHAR(10);
    END IF;

    -- Add add_service_days if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'deadline_dependencies' AND column_name = 'add_service_days'
    ) THEN
        ALTER TABLE deadline_dependencies ADD COLUMN add_service_days BOOLEAN DEFAULT FALSE;
    END IF;

    -- Add auto_recalculate if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'deadline_dependencies' AND column_name = 'auto_recalculate'
    ) THEN
        ALTER TABLE deadline_dependencies ADD COLUMN auto_recalculate BOOLEAN DEFAULT TRUE;
    END IF;

    -- Add last_recalculated if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'deadline_dependencies' AND column_name = 'last_recalculated'
    ) THEN
        ALTER TABLE deadline_dependencies ADD COLUMN last_recalculated TIMESTAMPTZ;
    END IF;

    -- Add created_at if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'deadline_dependencies' AND column_name = 'created_at'
    ) THEN
        ALTER TABLE deadline_dependencies ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW();
    END IF;
END $$;

-- Add foreign keys for deadline_dependencies
DO $$
BEGIN
    -- Foreign key to deadline_chains
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_deadline_dependencies_chain_id'
        AND table_name = 'deadline_dependencies'
    ) THEN
        ALTER TABLE deadline_dependencies
        ADD CONSTRAINT fk_deadline_dependencies_chain_id
        FOREIGN KEY (chain_id)
        REFERENCES deadline_chains(id)
        ON DELETE CASCADE;
    END IF;

    -- Foreign key to deadlines (child)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_deadline_dependencies_deadline_id'
        AND table_name = 'deadline_dependencies'
    ) THEN
        ALTER TABLE deadline_dependencies
        ADD CONSTRAINT fk_deadline_dependencies_deadline_id
        FOREIGN KEY (deadline_id)
        REFERENCES deadlines(id)
        ON DELETE CASCADE;
    END IF;

    -- Foreign key to deadlines (parent)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_deadline_dependencies_depends_on_id'
        AND table_name = 'deadline_dependencies'
    ) THEN
        ALTER TABLE deadline_dependencies
        ADD CONSTRAINT fk_deadline_dependencies_depends_on_id
        FOREIGN KEY (depends_on_deadline_id)
        REFERENCES deadlines(id)
        ON DELETE CASCADE;
    END IF;
END $$;

-- Add indexes for deadline_dependencies
CREATE INDEX IF NOT EXISTS idx_deadline_dependencies_chain_id ON deadline_dependencies(chain_id);
CREATE INDEX IF NOT EXISTS idx_deadline_dependencies_deadline_id ON deadline_dependencies(deadline_id);
CREATE INDEX IF NOT EXISTS idx_deadline_dependencies_depends_on_deadline_id ON deadline_dependencies(depends_on_deadline_id);
