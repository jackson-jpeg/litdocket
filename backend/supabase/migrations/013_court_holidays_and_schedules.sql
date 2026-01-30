-- Migration 013: Court Holidays and Scheduled Harvesting
-- Creates tables for per-jurisdiction holiday calendars and automated rule harvesting

-- ============================================================
-- Court Holidays Table
-- ============================================================
CREATE TABLE IF NOT EXISTS court_holidays (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    jurisdiction_id VARCHAR(36) NOT NULL REFERENCES jurisdictions(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    holiday_date DATE NOT NULL,
    year INTEGER NOT NULL,
    is_observed BOOLEAN DEFAULT FALSE,
    actual_date DATE,
    holiday_type VARCHAR(50) DEFAULT 'federal',
    court_closed BOOLEAN DEFAULT TRUE,
    extra_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for court_holidays
CREATE INDEX IF NOT EXISTS idx_court_holidays_jurisdiction ON court_holidays(jurisdiction_id);
CREATE INDEX IF NOT EXISTS idx_court_holidays_date ON court_holidays(holiday_date);
CREATE INDEX IF NOT EXISTS idx_court_holidays_year ON court_holidays(year);
CREATE INDEX IF NOT EXISTS idx_court_holidays_jurisdiction_year ON court_holidays(jurisdiction_id, year);

-- ============================================================
-- Holiday Patterns Table (for recurring holidays)
-- ============================================================
CREATE TABLE IF NOT EXISTS holiday_patterns (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    jurisdiction_id VARCHAR(36) REFERENCES jurisdictions(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    pattern_type VARCHAR(50) NOT NULL,
    pattern_definition JSONB NOT NULL,
    observe_if_weekend BOOLEAN DEFAULT TRUE,
    federal_observation_rules BOOLEAN DEFAULT TRUE,
    court_closed BOOLEAN DEFAULT TRUE,
    holiday_type VARCHAR(50) DEFAULT 'federal',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for holiday_patterns
CREATE INDEX IF NOT EXISTS idx_holiday_patterns_jurisdiction ON holiday_patterns(jurisdiction_id);
CREATE INDEX IF NOT EXISTS idx_holiday_patterns_active ON holiday_patterns(is_active);

-- ============================================================
-- Harvest Schedules Table
-- ============================================================
CREATE TABLE IF NOT EXISTS harvest_schedules (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    jurisdiction_id VARCHAR(36) REFERENCES jurisdictions(id) ON DELETE SET NULL,
    url TEXT NOT NULL,
    name VARCHAR(255),
    frequency VARCHAR(50) NOT NULL,
    day_of_week INTEGER,
    day_of_month INTEGER,
    last_content_hash VARCHAR(64),
    last_checked_at TIMESTAMPTZ,
    last_change_detected_at TIMESTAMPTZ,
    use_extended_thinking BOOLEAN DEFAULT TRUE,
    auto_approve_high_confidence BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    error_count INTEGER DEFAULT 0,
    last_error TEXT,
    total_checks INTEGER DEFAULT 0,
    changes_detected INTEGER DEFAULT 0,
    rules_harvested INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    next_run_at TIMESTAMPTZ
);

-- Indexes for harvest_schedules
CREATE INDEX IF NOT EXISTS idx_harvest_schedules_user ON harvest_schedules(user_id);
CREATE INDEX IF NOT EXISTS idx_harvest_schedules_active ON harvest_schedules(is_active);
CREATE INDEX IF NOT EXISTS idx_harvest_schedules_next_run ON harvest_schedules(next_run_at);

-- ============================================================
-- Harvest Schedule Runs Table
-- ============================================================
CREATE TABLE IF NOT EXISTS harvest_schedule_runs (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    schedule_id VARCHAR(36) NOT NULL REFERENCES harvest_schedules(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,
    content_hash VARCHAR(64),
    content_changed BOOLEAN DEFAULT FALSE,
    rules_found INTEGER DEFAULT 0,
    proposals_created INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Indexes for harvest_schedule_runs
CREATE INDEX IF NOT EXISTS idx_harvest_schedule_runs_schedule ON harvest_schedule_runs(schedule_id);
CREATE INDEX IF NOT EXISTS idx_harvest_schedule_runs_status ON harvest_schedule_runs(status);

-- ============================================================
-- Seed Federal Holidays (patterns)
-- ============================================================
INSERT INTO holiday_patterns (id, jurisdiction_id, name, pattern_type, pattern_definition, holiday_type) VALUES
    -- New Year's Day - January 1
    (gen_random_uuid()::text, NULL, 'New Year''s Day', 'fixed', '{"month": 1, "day": 1}', 'federal'),
    -- Martin Luther King Jr. Day - 3rd Monday of January
    (gen_random_uuid()::text, NULL, 'Martin Luther King Jr. Day', 'floating', '{"month": 1, "weekday": 0, "occurrence": 3}', 'federal'),
    -- Presidents Day - 3rd Monday of February
    (gen_random_uuid()::text, NULL, 'Presidents Day', 'floating', '{"month": 2, "weekday": 0, "occurrence": 3}', 'federal'),
    -- Memorial Day - Last Monday of May
    (gen_random_uuid()::text, NULL, 'Memorial Day', 'floating', '{"month": 5, "weekday": 0, "occurrence": -1}', 'federal'),
    -- Juneteenth - June 19
    (gen_random_uuid()::text, NULL, 'Juneteenth National Independence Day', 'fixed', '{"month": 6, "day": 19}', 'federal'),
    -- Independence Day - July 4
    (gen_random_uuid()::text, NULL, 'Independence Day', 'fixed', '{"month": 7, "day": 4}', 'federal'),
    -- Labor Day - 1st Monday of September
    (gen_random_uuid()::text, NULL, 'Labor Day', 'floating', '{"month": 9, "weekday": 0, "occurrence": 1}', 'federal'),
    -- Columbus Day - 2nd Monday of October
    (gen_random_uuid()::text, NULL, 'Columbus Day', 'floating', '{"month": 10, "weekday": 0, "occurrence": 2}', 'federal'),
    -- Veterans Day - November 11
    (gen_random_uuid()::text, NULL, 'Veterans Day', 'fixed', '{"month": 11, "day": 11}', 'federal'),
    -- Thanksgiving Day - 4th Thursday of November
    (gen_random_uuid()::text, NULL, 'Thanksgiving Day', 'floating', '{"month": 11, "weekday": 3, "occurrence": 4}', 'federal'),
    -- Christmas Day - December 25
    (gen_random_uuid()::text, NULL, 'Christmas Day', 'fixed', '{"month": 12, "day": 25}', 'federal')
ON CONFLICT DO NOTHING;

-- ============================================================
-- Function to generate holidays for a year
-- ============================================================
CREATE OR REPLACE FUNCTION generate_court_holidays(target_year INTEGER, target_jurisdiction_id VARCHAR(36) DEFAULT NULL)
RETURNS INTEGER AS $$
DECLARE
    pattern RECORD;
    holiday_date DATE;
    observed_date DATE;
    count INTEGER := 0;
BEGIN
    FOR pattern IN
        SELECT * FROM holiday_patterns
        WHERE is_active = TRUE
        AND (jurisdiction_id IS NULL OR jurisdiction_id = target_jurisdiction_id)
    LOOP
        -- Calculate holiday date based on pattern type
        IF pattern.pattern_type = 'fixed' THEN
            holiday_date := make_date(
                target_year,
                (pattern.pattern_definition->>'month')::INTEGER,
                (pattern.pattern_definition->>'day')::INTEGER
            );
        ELSIF pattern.pattern_type = 'floating' THEN
            -- Calculate nth weekday of month
            DECLARE
                month_num INTEGER := (pattern.pattern_definition->>'month')::INTEGER;
                weekday_num INTEGER := (pattern.pattern_definition->>'weekday')::INTEGER;
                occurrence INTEGER := (pattern.pattern_definition->>'occurrence')::INTEGER;
                first_of_month DATE := make_date(target_year, month_num, 1);
                days_to_add INTEGER;
            BEGIN
                IF occurrence > 0 THEN
                    -- Nth occurrence (e.g., 3rd Monday)
                    days_to_add := (weekday_num - EXTRACT(DOW FROM first_of_month)::INTEGER + 7) % 7;
                    holiday_date := first_of_month + (days_to_add + (occurrence - 1) * 7);
                ELSE
                    -- Last occurrence (e.g., last Monday)
                    DECLARE
                        last_of_month DATE := (make_date(target_year, month_num, 1) + INTERVAL '1 month' - INTERVAL '1 day')::DATE;
                    BEGIN
                        days_to_add := (EXTRACT(DOW FROM last_of_month)::INTEGER - weekday_num + 7) % 7;
                        holiday_date := last_of_month - days_to_add;
                    END;
                END IF;
            END;
        ELSE
            CONTINUE;
        END IF;

        -- Calculate observed date if needed
        observed_date := holiday_date;
        IF pattern.federal_observation_rules THEN
            IF EXTRACT(DOW FROM holiday_date) = 6 THEN  -- Saturday
                observed_date := holiday_date - 1;  -- Observed Friday
            ELSIF EXTRACT(DOW FROM holiday_date) = 0 THEN  -- Sunday
                observed_date := holiday_date + 1;  -- Observed Monday
            END IF;
        END IF;

        -- Insert holiday (skip if already exists)
        INSERT INTO court_holidays (
            jurisdiction_id,
            name,
            holiday_date,
            year,
            is_observed,
            actual_date,
            holiday_type,
            court_closed
        )
        SELECT
            COALESCE(pattern.jurisdiction_id, target_jurisdiction_id),
            pattern.name,
            observed_date,
            target_year,
            observed_date != holiday_date,
            CASE WHEN observed_date != holiday_date THEN holiday_date ELSE NULL END,
            pattern.holiday_type,
            pattern.court_closed
        WHERE target_jurisdiction_id IS NOT NULL
        ON CONFLICT DO NOTHING;

        count := count + 1;
    END LOOP;

    RETURN count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- Comments
-- ============================================================
COMMENT ON TABLE court_holidays IS 'Per-jurisdiction court holiday calendar for business day calculations';
COMMENT ON TABLE holiday_patterns IS 'Recurring holiday patterns for automatic calendar generation';
COMMENT ON TABLE harvest_schedules IS 'Scheduled jobs for automatic rule harvesting from court websites';
COMMENT ON TABLE harvest_schedule_runs IS 'Execution history for harvest schedules';
COMMENT ON FUNCTION generate_court_holidays IS 'Generates court holidays for a given year based on patterns';
