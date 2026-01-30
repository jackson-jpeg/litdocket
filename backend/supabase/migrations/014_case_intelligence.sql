-- Migration 014: Case Intelligence
-- AI-powered case analysis, health scoring, predictions, and timeline

-- ============================================================
-- Case Health Scores Table
-- ============================================================
CREATE TABLE IF NOT EXISTS case_health_scores (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    overall_score INTEGER NOT NULL,
    deadline_compliance_score INTEGER,
    document_completeness_score INTEGER,
    discovery_progress_score INTEGER,
    timeline_health_score INTEGER,
    risk_score INTEGER,
    risk_factors JSONB DEFAULT '[]',
    recommendations JSONB DEFAULT '[]',
    analysis_model VARCHAR(100),
    analysis_confidence NUMERIC(3, 2),
    calculated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_case_health_scores_case ON case_health_scores(case_id);
CREATE INDEX IF NOT EXISTS idx_case_health_scores_user ON case_health_scores(user_id);
CREATE INDEX IF NOT EXISTS idx_case_health_scores_calculated ON case_health_scores(calculated_at DESC);

-- ============================================================
-- Case Predictions Table
-- ============================================================
CREATE TABLE IF NOT EXISTS case_predictions (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    prediction_type VARCHAR(50) NOT NULL,
    predicted_value TEXT,
    confidence NUMERIC(3, 2),
    lower_bound TEXT,
    upper_bound TEXT,
    influencing_factors JSONB DEFAULT '[]',
    similar_cases JSONB DEFAULT '[]',
    model_version VARCHAR(50),
    predicted_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_case_predictions_case ON case_predictions(case_id);
CREATE INDEX IF NOT EXISTS idx_case_predictions_type ON case_predictions(prediction_type);

-- ============================================================
-- Judge Profiles Table
-- ============================================================
CREATE TABLE IF NOT EXISTS judge_profiles (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    name VARCHAR(255) NOT NULL,
    court VARCHAR(255),
    jurisdiction_id VARCHAR(36) REFERENCES jurisdictions(id) ON DELETE SET NULL,
    chambers_info JSONB DEFAULT '{}',
    motion_stats JSONB DEFAULT '{}',
    avg_ruling_time_days INTEGER,
    avg_case_duration_months INTEGER,
    preferences JSONB DEFAULT '{}',
    notable_rulings JSONB DEFAULT '[]',
    case_type_experience JSONB DEFAULT '{}',
    data_sources TEXT[] DEFAULT '{}',
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_judge_profiles_name ON judge_profiles(name);
CREATE INDEX IF NOT EXISTS idx_judge_profiles_jurisdiction ON judge_profiles(jurisdiction_id);

-- ============================================================
-- Case Events Table (Timeline)
-- ============================================================
CREATE TABLE IF NOT EXISTS case_events (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    event_subtype VARCHAR(50),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    event_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ,
    is_all_day BOOLEAN DEFAULT TRUE,
    status VARCHAR(50) DEFAULT 'scheduled',
    priority VARCHAR(20) DEFAULT 'standard',
    document_id VARCHAR(36) REFERENCES documents(id) ON DELETE SET NULL,
    deadline_id VARCHAR(36) REFERENCES deadlines(id) ON DELETE SET NULL,
    participants JSONB DEFAULT '[]',
    location TEXT,
    virtual_link TEXT,
    extra_data JSONB DEFAULT '{}',
    is_ai_generated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_case_events_case ON case_events(case_id);
CREATE INDEX IF NOT EXISTS idx_case_events_user ON case_events(user_id);
CREATE INDEX IF NOT EXISTS idx_case_events_date ON case_events(event_date);
CREATE INDEX IF NOT EXISTS idx_case_events_type ON case_events(event_type);

-- ============================================================
-- Discovery Requests Table
-- ============================================================
CREATE TABLE IF NOT EXISTS discovery_requests (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    request_type VARCHAR(50) NOT NULL,
    request_number INTEGER,
    direction VARCHAR(20) NOT NULL,
    from_party VARCHAR(255),
    to_party VARCHAR(255),
    title VARCHAR(500),
    description TEXT,
    items JSONB DEFAULT '[]',
    served_date DATE,
    response_due_date DATE,
    response_received_date DATE,
    status VARCHAR(50) DEFAULT 'pending',
    deadline_id VARCHAR(36) REFERENCES deadlines(id) ON DELETE SET NULL,
    request_document_id VARCHAR(36) REFERENCES documents(id) ON DELETE SET NULL,
    response_document_id VARCHAR(36) REFERENCES documents(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_discovery_requests_case ON discovery_requests(case_id);
CREATE INDEX IF NOT EXISTS idx_discovery_requests_due ON discovery_requests(response_due_date);
CREATE INDEX IF NOT EXISTS idx_discovery_requests_status ON discovery_requests(status);

-- ============================================================
-- Case Facts Table
-- ============================================================
CREATE TABLE IF NOT EXISTS case_facts (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    fact_type VARCHAR(50) NOT NULL,
    fact_text TEXT NOT NULL,
    normalized_value TEXT,
    importance VARCHAR(20) DEFAULT 'standard',
    is_disputed BOOLEAN DEFAULT FALSE,
    dispute_details TEXT,
    source_document_id VARCHAR(36) REFERENCES documents(id) ON DELETE SET NULL,
    source_page INTEGER,
    source_excerpt TEXT,
    extraction_confidence NUMERIC(3, 2),
    verified BOOLEAN DEFAULT FALSE,
    verified_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    related_fact_ids VARCHAR(36)[] DEFAULT '{}',
    extracted_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_case_facts_case ON case_facts(case_id);
CREATE INDEX IF NOT EXISTS idx_case_facts_type ON case_facts(fact_type);
CREATE INDEX IF NOT EXISTS idx_case_facts_importance ON case_facts(importance);

-- ============================================================
-- Brief Drafts Table
-- ============================================================
CREATE TABLE IF NOT EXISTS brief_drafts (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_type VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    sections JSONB DEFAULT '[]',
    content TEXT,
    generation_prompt TEXT,
    generation_context JSONB DEFAULT '{}',
    citations JSONB DEFAULT '[]',
    similar_filings JSONB DEFAULT '[]',
    status VARCHAR(50) DEFAULT 'draft',
    version INTEGER DEFAULT 1,
    parent_draft_id VARCHAR(36) REFERENCES brief_drafts(id) ON DELETE SET NULL,
    final_document_id VARCHAR(36) REFERENCES documents(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_brief_drafts_case ON brief_drafts(case_id);
CREATE INDEX IF NOT EXISTS idx_brief_drafts_status ON brief_drafts(status);
CREATE INDEX IF NOT EXISTS idx_brief_drafts_type ON brief_drafts(document_type);

-- ============================================================
-- Comments
-- ============================================================
COMMENT ON TABLE case_health_scores IS 'AI-generated health scores and risk assessments for cases';
COMMENT ON TABLE case_predictions IS 'AI predictions for case outcomes and milestones';
COMMENT ON TABLE judge_profiles IS 'Judge analytics and ruling patterns';
COMMENT ON TABLE case_events IS 'Unified case timeline events';
COMMENT ON TABLE discovery_requests IS 'Discovery request tracking';
COMMENT ON TABLE case_facts IS 'AI-extracted facts from case documents';
COMMENT ON TABLE brief_drafts IS 'AI-assisted brief and motion drafts';
