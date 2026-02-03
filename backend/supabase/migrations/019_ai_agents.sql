-- Migration: 019_ai_agents.sql
-- Description: Add AI agent system for specialized chat personas
-- Date: 2024

-- ============================================================================
-- AI AGENTS TABLE
-- Stores definitions for specialized AI personas (Deadline Sentinel, etc.)
-- ============================================================================

CREATE TABLE IF NOT EXISTS ai_agents (
    id VARCHAR(36) PRIMARY KEY,
    slug VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    system_prompt_additions TEXT NOT NULL,
    primary_tools JSONB DEFAULT '[]'::jsonb,
    context_enhancers JSONB DEFAULT '[]'::jsonb,
    triggering_phrases JSONB DEFAULT '[]'::jsonb,
    icon VARCHAR(50),
    color VARCHAR(20),
    is_active BOOLEAN DEFAULT true,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for ai_agents
CREATE INDEX IF NOT EXISTS idx_ai_agents_slug ON ai_agents(slug);
CREATE INDEX IF NOT EXISTS idx_ai_agents_active ON ai_agents(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_ai_agents_display_order ON ai_agents(display_order);

-- ============================================================================
-- USER AGENT PREFERENCES TABLE
-- Stores per-user agent preferences (default agent, settings)
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_agent_preferences (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    default_agent_id VARCHAR(36) REFERENCES ai_agents(id) ON DELETE SET NULL,
    agent_settings JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Indexes for user_agent_preferences
CREATE INDEX IF NOT EXISTS idx_user_agent_preferences_user ON user_agent_preferences(user_id);

-- ============================================================================
-- AGENT ANALYTICS TABLE
-- Tracks agent usage for analytics and optimization
-- ============================================================================

CREATE TABLE IF NOT EXISTS agent_analytics (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    agent_slug VARCHAR(50),
    case_id VARCHAR(36) REFERENCES cases(id) ON DELETE SET NULL,
    session_id VARCHAR(100),
    message_count INTEGER DEFAULT 1,
    tools_used JSONB DEFAULT '[]'::jsonb,
    tokens_used INTEGER DEFAULT 0,
    response_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for agent_analytics
CREATE INDEX IF NOT EXISTS idx_agent_analytics_user ON agent_analytics(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_analytics_agent ON agent_analytics(agent_slug);
CREATE INDEX IF NOT EXISTS idx_agent_analytics_case ON agent_analytics(case_id);
CREATE INDEX IF NOT EXISTS idx_agent_analytics_created ON agent_analytics(created_at);

-- ============================================================================
-- MODIFY CHAT_MESSAGES TABLE
-- Add agent tracking columns
-- ============================================================================

-- Add agent_id column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'chat_messages' AND column_name = 'agent_id'
    ) THEN
        ALTER TABLE chat_messages
        ADD COLUMN agent_id VARCHAR(36) REFERENCES ai_agents(id) ON DELETE SET NULL;
    END IF;
END $$;

-- Add agent_slug column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'chat_messages' AND column_name = 'agent_slug'
    ) THEN
        ALTER TABLE chat_messages
        ADD COLUMN agent_slug VARCHAR(50);
    END IF;
END $$;

-- Add index for agent lookups on chat_messages
CREATE INDEX IF NOT EXISTS idx_chat_messages_agent ON chat_messages(agent_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_agent_slug ON chat_messages(agent_slug);

-- ============================================================================
-- TRIGGERS FOR updated_at
-- ============================================================================

-- Trigger for ai_agents
DROP TRIGGER IF EXISTS update_ai_agents_updated_at ON ai_agents;
CREATE TRIGGER update_ai_agents_updated_at
    BEFORE UPDATE ON ai_agents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for user_agent_preferences
DROP TRIGGER IF EXISTS update_user_agent_preferences_updated_at ON user_agent_preferences;
CREATE TRIGGER update_user_agent_preferences_updated_at
    BEFORE UPDATE ON user_agent_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SEED INITIAL AI AGENTS
-- ============================================================================

INSERT INTO ai_agents (id, slug, name, description, system_prompt_additions, primary_tools, triggering_phrases, icon, color, display_order)
VALUES
    -- Deadline Sentinel
    (
        'agent-deadline-sentinel-001',
        'deadline_sentinel',
        'Deadline Sentinel',
        'Ultra-focused deadline tracking specialist. Monitors fatal/critical deadlines, countdown tracking, and cascade impact analysis.',
        E'You are the Deadline Sentinel - an ultra-focused deadline tracking specialist.\nYour PRIMARY mission is to ensure no deadline is ever missed.\n\nWhen responding:\n- Lead with urgency for any deadline within 7 days\n- Always show days until/overdue prominently\n- Proactively warn about cascade impacts\n- Use countdown language ("3 days remaining", "OVERDUE by 2 days")\n- Prioritize FATAL and CRITICAL deadlines in every response\n- If asked about anything other than deadlines, briefly answer then redirect to deadline status',
        '["query_deadlines", "calculate_deadline", "preview_cascade_update", "get_dependency_tree", "export_deadlines"]'::jsonb,
        '["what''s due", "deadlines", "calendar", "urgent", "overdue", "upcoming"]'::jsonb,
        'clock',
        'red',
        1
    ),
    -- Rules Oracle
    (
        'agent-rules-oracle-002',
        'rules_oracle',
        'Rules Oracle',
        'Definitive source for procedural rules. Court rule lookup, citation explanation, and jurisdiction guidance.',
        E'You are the Rules Oracle - the definitive source for procedural rules.\nYour mission is to provide accurate, citable rule guidance.\n\nWhen responding:\n- Always include full citations (e.g., "Fla. R. Civ. P. 1.140(a)(1)")\n- Distinguish Florida State from Federal rules clearly\n- Note service method extensions with citations\n- Explain calculation methods (calendar vs business days)\n- When uncertain, say so and recommend consulting the actual rule text\n- Cross-reference related rules when relevant',
        '["lookup_court_rule", "get_available_templates", "calculate_deadline", "search_court_rules", "get_rule_details"]'::jsonb,
        '["rule", "citation", "how long do I have", "what does the rule say", "FRCP", "Florida Rule"]'::jsonb,
        'book',
        'blue',
        2
    ),
    -- Document Analyst
    (
        'agent-document-analyst-003',
        'document_analyst',
        'Document Analyst',
        'Expert at extracting intelligence from legal documents. Document analysis, deadline extraction, and classification.',
        E'You are the Document Analyst - expert at extracting intelligence from legal documents.\n\nWhen analyzing documents:\n- Distinguish FILING DATE from SERVICE DATE (response deadlines run from SERVICE)\n- Extract all key dates (hearing, trial, mediation, deposition)\n- Identify document type for proper trigger mapping\n- Flag confidence levels for extracted dates\n- Note any ambiguities that require attorney review\n- Suggest deadline creation based on document type',
        '["search_documents", "rename_document", "create_deadline", "create_trigger_deadline"]'::jsonb,
        '["analyze", "what does this document say", "extract deadlines", "document", "filing", "motion"]'::jsonb,
        'file-search',
        'purple',
        3
    ),
    -- Case Strategist
    (
        'agent-case-strategist-004',
        'case_strategist',
        'Case Strategist',
        'Focused on procedural posture and next steps. Action planning, case overview, and strategic recommendations.',
        E'You are the Case Strategist - focused on procedural posture and next steps.\n\nWhen advising:\n- Prioritize by urgency (critical → high → medium → low)\n- Include consequences if ignored\n- Suggest specific tools for each action\n- Reference applicable rules for procedural steps\n- Consider the big picture of case progression\n- Identify potential procedural pitfalls',
        '["get_case_statistics", "query_deadlines", "get_dependency_tree", "update_case_info"]'::jsonb,
        '["what should I do next", "strategy", "action plan", "case overview", "next steps", "priorities"]'::jsonb,
        'target',
        'green',
        4
    ),
    -- Opposition Tracker
    (
        'agent-opposition-tracker-005',
        'opposition_tracker',
        'Opposition Tracker',
        'Monitoring all parties and their obligations. Party management, opposing counsel deadlines, and service tracking.',
        E'You are the Opposition Tracker - monitoring all parties and their obligations.\n\nWhen tracking:\n- Distinguish plaintiff vs defendant deadlines\n- Track response deadlines to opposing filings\n- Monitor discovery obligations by party\n- Flag deadlines triggered by opponent actions\n- Note service requirements for each party\n- Alert when opposing party deadlines create opportunities',
        '["add_party", "remove_party", "query_deadlines", "create_trigger_deadline"]'::jsonb,
        '["opposing counsel", "defense deadline", "plaintiff deadline", "parties", "opponent", "other side"]'::jsonb,
        'users',
        'orange',
        5
    )
ON CONFLICT (slug) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    system_prompt_additions = EXCLUDED.system_prompt_additions,
    primary_tools = EXCLUDED.primary_tools,
    triggering_phrases = EXCLUDED.triggering_phrases,
    icon = EXCLUDED.icon,
    color = EXCLUDED.color,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE ai_agents IS 'Specialized AI agent personas for the chat interface';
COMMENT ON TABLE user_agent_preferences IS 'Per-user preferences for AI agent selection';
COMMENT ON TABLE agent_analytics IS 'Usage analytics for AI agents';
COMMENT ON COLUMN ai_agents.slug IS 'URL-safe unique identifier for the agent';
COMMENT ON COLUMN ai_agents.system_prompt_additions IS 'Text appended to system prompt when this agent is active';
COMMENT ON COLUMN ai_agents.primary_tools IS 'JSON array of tool names this agent primarily uses';
COMMENT ON COLUMN ai_agents.triggering_phrases IS 'JSON array of phrases that suggest this agent should be used';
COMMENT ON COLUMN ai_agents.context_enhancers IS 'JSON array of context enhancement strategies';
