-- ============================================
-- THE SOVEREIGN DOCTRINE
-- Jurisdictional Graph Engine v1.0
-- ============================================
-- "Graph Theory, Not Code Lists"
--
-- This migration enhances the existing schema with:
-- 1. Canonical slug-based naming (us.federal.fl.middle.bankruptcy)
-- 2. Enhanced recursive CTEs for full graph traversal
-- 3. Rule conflict detection and resolution
-- 4. Holiday management for date calculations
-- 5. Service method handling (+3 days for mail, etc.)
-- ============================================

-- ============================================
-- PART 1: ENHANCE EXISTING TABLES WITH CANONICAL SLUGS
-- ============================================

-- Add canonical_slug to jurisdictions (the "clean room" identifier)
ALTER TABLE jurisdictions
ADD COLUMN IF NOT EXISTS canonical_slug TEXT UNIQUE;

-- Populate canonical slugs based on hierarchy
-- This creates slugs like: us.federal, us.federal.fl.southern, us.fl.state
DO $$
DECLARE
    rec RECORD;
    parent_slug TEXT;
    new_slug TEXT;
BEGIN
    -- First pass: Set root level slugs
    UPDATE jurisdictions SET canonical_slug = 'us.federal' WHERE code = 'FED';
    UPDATE jurisdictions SET canonical_slug = 'us.fl.state' WHERE code = 'FL';

    -- Federal district courts
    UPDATE jurisdictions SET canonical_slug = 'us.federal.fl.southern.district' WHERE code = 'FED-USDC-SD-FL';
    UPDATE jurisdictions SET canonical_slug = 'us.federal.fl.middle.district' WHERE code = 'FED-USDC-MD-FL';
    UPDATE jurisdictions SET canonical_slug = 'us.federal.fl.northern.district' WHERE code = 'FED-USDC-ND-FL';

    -- Bankruptcy courts
    UPDATE jurisdictions SET canonical_slug = 'us.federal.fl.southern.bankruptcy' WHERE code = 'FED-BK-SD-FL';
    UPDATE jurisdictions SET canonical_slug = 'us.federal.fl.middle.bankruptcy' WHERE code = 'FED-BK-MD-FL';
    UPDATE jurisdictions SET canonical_slug = 'us.federal.fl.northern.bankruptcy' WHERE code = 'FED-BK-ND-FL';

    -- Florida DCAs
    UPDATE jurisdictions SET canonical_slug = 'us.fl.appellate.dca1' WHERE code = 'FL-DCA-1';
    UPDATE jurisdictions SET canonical_slug = 'us.fl.appellate.dca2' WHERE code = 'FL-DCA-2';
    UPDATE jurisdictions SET canonical_slug = 'us.fl.appellate.dca3' WHERE code = 'FL-DCA-3';
    UPDATE jurisdictions SET canonical_slug = 'us.fl.appellate.dca4' WHERE code = 'FL-DCA-4';
    UPDATE jurisdictions SET canonical_slug = 'us.fl.appellate.dca5' WHERE code = 'FL-DCA-5';
    UPDATE jurisdictions SET canonical_slug = 'us.fl.appellate.dca6' WHERE code = 'FL-DCA-6';
END $$;

-- Add canonical_slug to rule_sets
ALTER TABLE rule_sets
ADD COLUMN IF NOT EXISTS canonical_slug TEXT UNIQUE;

-- Populate rule_set canonical slugs
DO $$
BEGIN
    -- Federal rules
    UPDATE rule_sets SET canonical_slug = 'rules.federal.civil' WHERE code = 'FRCP';
    UPDATE rule_sets SET canonical_slug = 'rules.federal.appellate' WHERE code = 'FRAP';
    UPDATE rule_sets SET canonical_slug = 'rules.federal.bankruptcy' WHERE code = 'FRBP';

    -- Florida state rules
    UPDATE rule_sets SET canonical_slug = 'rules.fl.civil' WHERE code = 'FL:RCP';
    UPDATE rule_sets SET canonical_slug = 'rules.fl.criminal' WHERE code = 'FL:CPP';
    UPDATE rule_sets SET canonical_slug = 'rules.fl.appellate' WHERE code = 'FL:RAP';
    UPDATE rule_sets SET canonical_slug = 'rules.fl.probate' WHERE code = 'FL:PB-FPR';
    UPDATE rule_sets SET canonical_slug = 'rules.fl.family' WHERE code = 'FL:FAM';
    UPDATE rule_sets SET canonical_slug = 'rules.fl.smallclaims' WHERE code = 'FL:SCR';

    -- Local bankruptcy rules - Southern District
    UPDATE rule_sets SET canonical_slug = 'rules.fl.southern.bankruptcy.ch7' WHERE code = 'FL:BRSD-7';
    UPDATE rule_sets SET canonical_slug = 'rules.fl.southern.bankruptcy.ch11' WHERE code = 'FL:BRSD-11';
    UPDATE rule_sets SET canonical_slug = 'rules.fl.southern.bankruptcy.ch13' WHERE code = 'FL:BRSD-13';

    -- Local bankruptcy rules - Middle District
    UPDATE rule_sets SET canonical_slug = 'rules.fl.middle.bankruptcy.ch7' WHERE code = 'FL:BRMD-7';
    UPDATE rule_sets SET canonical_slug = 'rules.fl.middle.bankruptcy.ch11' WHERE code = 'FL:BRMD-11';
    UPDATE rule_sets SET canonical_slug = 'rules.fl.middle.bankruptcy.ch13' WHERE code = 'FL:BRMD-13';
END $$;

-- Index for slug lookups
CREATE INDEX IF NOT EXISTS idx_jurisdictions_slug ON jurisdictions(canonical_slug);
CREATE INDEX IF NOT EXISTS idx_rule_sets_slug ON rule_sets(canonical_slug);

-- ============================================
-- PART 2: HOLIDAY MANAGEMENT SYSTEM
-- ============================================

-- Holiday types
CREATE TYPE holiday_type AS ENUM (
    'federal',      -- Federal holidays (all federal courts closed)
    'state',        -- State holidays (state courts closed)
    'court',        -- Court-specific closure
    'judicial'      -- Judicial holiday (some courts)
);

-- Holidays table - stores all court closures
CREATE TABLE IF NOT EXISTS holidays (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    holiday_date DATE NOT NULL,
    holiday_type holiday_type NOT NULL,
    jurisdiction_id UUID REFERENCES jurisdictions(id) ON DELETE CASCADE,
    -- NULL jurisdiction_id means applies to all (federal holidays)
    is_recurring BOOLEAN DEFAULT FALSE,
    recurring_month INTEGER CHECK (recurring_month >= 1 AND recurring_month <= 12),
    recurring_day INTEGER CHECK (recurring_day >= 1 AND recurring_day <= 31),
    recurring_weekday INTEGER CHECK (recurring_weekday >= 0 AND recurring_weekday <= 6),
    recurring_week INTEGER CHECK (recurring_week >= 1 AND recurring_week <= 5),
    -- For "nth weekday of month" rules (e.g., 4th Thursday)
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(holiday_date, jurisdiction_id)
);

CREATE INDEX idx_holidays_date ON holidays(holiday_date);
CREATE INDEX idx_holidays_jurisdiction ON holidays(jurisdiction_id);

-- Pre-populate federal holidays for 2024-2026
INSERT INTO holidays (name, holiday_date, holiday_type, jurisdiction_id, is_recurring, recurring_month, recurring_day, notes)
VALUES
    -- 2024
    ('New Year''s Day', '2024-01-01', 'federal', NULL, TRUE, 1, 1, 'January 1'),
    ('Martin Luther King Jr. Day', '2024-01-15', 'federal', NULL, FALSE, NULL, NULL, '3rd Monday of January'),
    ('Presidents'' Day', '2024-02-19', 'federal', NULL, FALSE, NULL, NULL, '3rd Monday of February'),
    ('Memorial Day', '2024-05-27', 'federal', NULL, FALSE, NULL, NULL, 'Last Monday of May'),
    ('Juneteenth', '2024-06-19', 'federal', NULL, TRUE, 6, 19, 'June 19'),
    ('Independence Day', '2024-07-04', 'federal', NULL, TRUE, 7, 4, 'July 4'),
    ('Labor Day', '2024-09-02', 'federal', NULL, FALSE, NULL, NULL, '1st Monday of September'),
    ('Columbus Day', '2024-10-14', 'federal', NULL, FALSE, NULL, NULL, '2nd Monday of October'),
    ('Veterans Day', '2024-11-11', 'federal', NULL, TRUE, 11, 11, 'November 11'),
    ('Thanksgiving Day', '2024-11-28', 'federal', NULL, FALSE, NULL, NULL, '4th Thursday of November'),
    ('Christmas Day', '2024-12-25', 'federal', NULL, TRUE, 12, 25, 'December 25'),
    -- 2025
    ('New Year''s Day', '2025-01-01', 'federal', NULL, TRUE, 1, 1, NULL),
    ('Martin Luther King Jr. Day', '2025-01-20', 'federal', NULL, FALSE, NULL, NULL, NULL),
    ('Presidents'' Day', '2025-02-17', 'federal', NULL, FALSE, NULL, NULL, NULL),
    ('Memorial Day', '2025-05-26', 'federal', NULL, FALSE, NULL, NULL, NULL),
    ('Juneteenth', '2025-06-19', 'federal', NULL, TRUE, 6, 19, NULL),
    ('Independence Day', '2025-07-04', 'federal', NULL, TRUE, 7, 4, NULL),
    ('Labor Day', '2025-09-01', 'federal', NULL, FALSE, NULL, NULL, NULL),
    ('Columbus Day', '2025-10-13', 'federal', NULL, FALSE, NULL, NULL, NULL),
    ('Veterans Day', '2025-11-11', 'federal', NULL, TRUE, 11, 11, NULL),
    ('Thanksgiving Day', '2025-11-27', 'federal', NULL, FALSE, NULL, NULL, NULL),
    ('Christmas Day', '2025-12-25', 'federal', NULL, TRUE, 12, 25, NULL),
    -- 2026
    ('New Year''s Day', '2026-01-01', 'federal', NULL, TRUE, 1, 1, NULL),
    ('Martin Luther King Jr. Day', '2026-01-19', 'federal', NULL, FALSE, NULL, NULL, NULL),
    ('Presidents'' Day', '2026-02-16', 'federal', NULL, FALSE, NULL, NULL, NULL),
    ('Memorial Day', '2026-05-25', 'federal', NULL, FALSE, NULL, NULL, NULL),
    ('Juneteenth', '2026-06-19', 'federal', NULL, TRUE, 6, 19, NULL),
    ('Independence Day', '2026-07-03', 'federal', NULL, TRUE, 7, 4, 'Observed on Friday July 3'),
    ('Labor Day', '2026-09-07', 'federal', NULL, FALSE, NULL, NULL, NULL),
    ('Columbus Day', '2026-10-12', 'federal', NULL, FALSE, NULL, NULL, NULL),
    ('Veterans Day', '2026-11-11', 'federal', NULL, TRUE, 11, 11, NULL),
    ('Thanksgiving Day', '2026-11-26', 'federal', NULL, FALSE, NULL, NULL, NULL),
    ('Christmas Day', '2026-12-25', 'federal', NULL, TRUE, 12, 25, NULL)
ON CONFLICT (holiday_date, jurisdiction_id) DO NOTHING;

-- ============================================
-- PART 3: SERVICE METHOD CALCULATIONS
-- ============================================

-- Service methods and their additional days
CREATE TYPE service_method AS ENUM (
    'personal',           -- 0 additional days
    'certified_mail',     -- +3 days
    'first_class_mail',   -- +3 days (federal), +5 days (some state)
    'electronic',         -- 0 additional days (if consented)
    'publication',        -- Varies by jurisdiction
    'secretary_of_state', -- +10 days typically
    'posting'             -- Varies
);

-- Service method rules by jurisdiction
CREATE TABLE IF NOT EXISTS service_method_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    jurisdiction_id UUID REFERENCES jurisdictions(id) ON DELETE CASCADE,
    service_method service_method NOT NULL,
    additional_days INTEGER NOT NULL DEFAULT 0,
    rule_citation VARCHAR(255),
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(jurisdiction_id, service_method)
);

-- Federal service rules (FRCP 6(d))
INSERT INTO service_method_rules (jurisdiction_id, service_method, additional_days, rule_citation, notes)
SELECT
    j.id,
    sm.method,
    sm.days,
    sm.citation,
    sm.notes
FROM jurisdictions j
CROSS JOIN (
    VALUES
        ('personal'::service_method, 0, 'Fed. R. Civ. P. 6(d)', 'No additional days for personal service'),
        ('certified_mail'::service_method, 3, 'Fed. R. Civ. P. 6(d)', '3 days added for mailing'),
        ('first_class_mail'::service_method, 3, 'Fed. R. Civ. P. 6(d)', '3 days added for mailing'),
        ('electronic'::service_method, 3, 'Fed. R. Civ. P. 6(d)', '3 days added for electronic service'),
        ('secretary_of_state'::service_method, 10, 'Varies', 'Typically 10 additional days')
) AS sm(method, days, citation, notes)
WHERE j.code = 'FED'
ON CONFLICT (jurisdiction_id, service_method) DO NOTHING;

-- Florida service rules (Fla. R. Civ. P. 1.090(e))
INSERT INTO service_method_rules (jurisdiction_id, service_method, additional_days, rule_citation, notes)
SELECT
    j.id,
    sm.method,
    sm.days,
    sm.citation,
    sm.notes
FROM jurisdictions j
CROSS JOIN (
    VALUES
        ('personal'::service_method, 0, 'Fla. R. Civ. P. 1.090(e)', 'No additional days for personal service'),
        ('certified_mail'::service_method, 5, 'Fla. R. Civ. P. 1.090(e)', '5 days added for mailing in Florida'),
        ('first_class_mail'::service_method, 5, 'Fla. R. Civ. P. 1.090(e)', '5 days added for mailing in Florida'),
        ('electronic'::service_method, 0, 'Fla. R. Jud. Admin. 2.516', 'No additional days for e-service'),
        ('publication'::service_method, 0, 'Fla. Stat. § 49.011', 'Service by publication - separate rules')
) AS sm(method, days, citation, notes)
WHERE j.code = 'FL'
ON CONFLICT (jurisdiction_id, service_method) DO NOTHING;

-- ============================================
-- PART 4: RULE CONFLICT DETECTION
-- ============================================

-- Table to store known rule conflicts and their resolutions
CREATE TABLE IF NOT EXISTS rule_conflicts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_set_a_id UUID NOT NULL REFERENCES rule_sets(id) ON DELETE CASCADE,
    rule_set_b_id UUID NOT NULL REFERENCES rule_sets(id) ON DELETE CASCADE,
    conflict_type VARCHAR(100) NOT NULL,
    -- 'deadline_days', 'service_method', 'filing_requirement', etc.
    description TEXT NOT NULL,
    resolution_strategy VARCHAR(50) NOT NULL DEFAULT 'strictest',
    -- 'strictest', 'local_prevails', 'federal_prevails', 'user_choice'
    resolution_notes TEXT,
    auto_resolve BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(rule_set_a_id, rule_set_b_id, conflict_type)
);

-- ============================================
-- PART 5: ENHANCED RECURSIVE CTEs
-- ============================================

-- Function to get full jurisdiction ancestry (from child to root)
CREATE OR REPLACE FUNCTION get_jurisdiction_ancestry(p_jurisdiction_id UUID)
RETURNS TABLE (
    id UUID,
    code VARCHAR(50),
    name VARCHAR(255),
    canonical_slug TEXT,
    jurisdiction_type jurisdiction_type,
    depth INTEGER,
    path TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE ancestry AS (
        -- Base case: the starting jurisdiction
        SELECT
            j.id,
            j.code,
            j.name,
            j.canonical_slug,
            j.jurisdiction_type,
            0 as depth,
            ARRAY[j.code]::TEXT[] as path
        FROM jurisdictions j
        WHERE j.id = p_jurisdiction_id

        UNION ALL

        -- Recursive case: parent jurisdictions
        SELECT
            parent.id,
            parent.code,
            parent.name,
            parent.canonical_slug,
            parent.jurisdiction_type,
            a.depth + 1,
            parent.code || a.path
        FROM jurisdictions parent
        INNER JOIN ancestry a ON parent.id = (
            SELECT parent_jurisdiction_id
            FROM jurisdictions
            WHERE jurisdictions.id = a.id
        )
        WHERE parent.id IS NOT NULL
    )
    SELECT * FROM ancestry ORDER BY depth DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to get full jurisdiction descendants (from parent to all children)
CREATE OR REPLACE FUNCTION get_jurisdiction_descendants(p_jurisdiction_id UUID)
RETURNS TABLE (
    id UUID,
    code VARCHAR(50),
    name VARCHAR(255),
    canonical_slug TEXT,
    jurisdiction_type jurisdiction_type,
    depth INTEGER,
    parent_id UUID
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE descendants AS (
        -- Base case: the starting jurisdiction
        SELECT
            j.id,
            j.code,
            j.name,
            j.canonical_slug,
            j.jurisdiction_type,
            0 as depth,
            j.parent_jurisdiction_id as parent_id
        FROM jurisdictions j
        WHERE j.id = p_jurisdiction_id

        UNION ALL

        -- Recursive case: child jurisdictions
        SELECT
            child.id,
            child.code,
            child.name,
            child.canonical_slug,
            child.jurisdiction_type,
            d.depth + 1,
            child.parent_jurisdiction_id
        FROM jurisdictions child
        INNER JOIN descendants d ON child.parent_jurisdiction_id = d.id
    )
    SELECT * FROM descendants ORDER BY depth, name;
END;
$$ LANGUAGE plpgsql;

-- Function to resolve all dependencies for a rule set (full DAG traversal)
CREATE OR REPLACE FUNCTION resolve_rule_dependencies(p_rule_set_id UUID)
RETURNS TABLE (
    rule_set_id UUID,
    code VARCHAR(50),
    name VARCHAR(255),
    canonical_slug TEXT,
    dependency_type dependency_type,
    priority INTEGER,
    depth INTEGER,
    is_root BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE rule_graph AS (
        -- Base case: the selected rule set
        SELECT
            rs.id as rule_set_id,
            rs.code,
            rs.name,
            rs.canonical_slug,
            'concurrent'::dependency_type as dependency_type,
            0 as priority,
            0 as depth,
            TRUE as is_root
        FROM rule_sets rs
        WHERE rs.id = p_rule_set_id AND rs.is_active = TRUE

        UNION

        -- Recursive case: dependencies
        SELECT
            dep_rs.id,
            dep_rs.code,
            dep_rs.name,
            dep_rs.canonical_slug,
            rsd.dependency_type,
            rsd.priority,
            rg.depth + 1,
            FALSE
        FROM rule_graph rg
        INNER JOIN rule_set_dependencies rsd ON rsd.rule_set_id = rg.rule_set_id
        INNER JOIN rule_sets dep_rs ON dep_rs.id = rsd.required_rule_set_id
        WHERE dep_rs.is_active = TRUE
          AND rg.depth < 10  -- Prevent infinite loops
    )
    SELECT DISTINCT ON (rule_graph.rule_set_id)
        rule_graph.rule_set_id,
        rule_graph.code,
        rule_graph.name,
        rule_graph.canonical_slug,
        rule_graph.dependency_type,
        rule_graph.priority,
        rule_graph.depth,
        rule_graph.is_root
    FROM rule_graph
    ORDER BY rule_graph.rule_set_id, rule_graph.depth;
END;
$$ LANGUAGE plpgsql;

-- Function to check if date is a holiday for given jurisdiction
CREATE OR REPLACE FUNCTION is_court_holiday(
    p_date DATE,
    p_jurisdiction_id UUID DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    is_holiday BOOLEAN;
BEGIN
    -- Check if date falls on a weekend
    IF EXTRACT(DOW FROM p_date) IN (0, 6) THEN
        RETURN TRUE;
    END IF;

    -- Check holidays table
    SELECT EXISTS (
        SELECT 1 FROM holidays h
        WHERE h.holiday_date = p_date
          AND (h.jurisdiction_id IS NULL OR h.jurisdiction_id = p_jurisdiction_id)
    ) INTO is_holiday;

    RETURN is_holiday;
END;
$$ LANGUAGE plpgsql;

-- Function to get next business day
CREATE OR REPLACE FUNCTION get_next_business_day(
    p_date DATE,
    p_jurisdiction_id UUID DEFAULT NULL
)
RETURNS DATE AS $$
DECLARE
    result_date DATE := p_date;
BEGIN
    WHILE is_court_holiday(result_date, p_jurisdiction_id) LOOP
        result_date := result_date + INTERVAL '1 day';
    END LOOP;
    RETURN result_date;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate deadline with all rules applied
CREATE OR REPLACE FUNCTION calculate_deadline(
    p_trigger_date DATE,
    p_days INTEGER,
    p_calculation_method calculation_method,
    p_service_method service_method DEFAULT 'personal',
    p_jurisdiction_id UUID DEFAULT NULL
)
RETURNS TABLE (
    deadline_date DATE,
    service_days_added INTEGER,
    holidays_skipped INTEGER,
    calculation_notes TEXT
) AS $$
DECLARE
    v_date DATE := p_trigger_date;
    v_service_days INTEGER := 0;
    v_holidays_skipped INTEGER := 0;
    v_days_remaining INTEGER;
    v_direction INTEGER;
    v_notes TEXT := '';
BEGIN
    -- Get service method additional days
    IF p_jurisdiction_id IS NOT NULL THEN
        SELECT COALESCE(smr.additional_days, 0) INTO v_service_days
        FROM service_method_rules smr
        WHERE smr.jurisdiction_id = p_jurisdiction_id
          AND smr.service_method = p_service_method;
    END IF;

    -- Determine direction (positive = forward, negative = backward)
    v_direction := SIGN(p_days);
    v_days_remaining := ABS(p_days);

    IF p_calculation_method = 'calendar_days' THEN
        -- Calendar days: just add the days
        v_date := v_date + (p_days * INTERVAL '1 day');
        v_notes := 'Calendar day calculation';

        -- Add service days
        IF v_service_days > 0 THEN
            v_date := v_date + (v_service_days * INTERVAL '1 day');
            v_notes := v_notes || ', +' || v_service_days || ' service days';
        END IF;

        -- If lands on weekend/holiday, roll to next business day
        IF is_court_holiday(v_date, p_jurisdiction_id) THEN
            v_date := get_next_business_day(v_date, p_jurisdiction_id);
            v_holidays_skipped := v_holidays_skipped + 1;
            v_notes := v_notes || ', rolled forward for holiday/weekend';
        END IF;

    ELSIF p_calculation_method = 'business_days' THEN
        -- Business days: skip weekends and holidays
        v_notes := 'Business day calculation';

        WHILE v_days_remaining > 0 LOOP
            v_date := v_date + (v_direction * INTERVAL '1 day');
            IF NOT is_court_holiday(v_date, p_jurisdiction_id) THEN
                v_days_remaining := v_days_remaining - 1;
            ELSE
                v_holidays_skipped := v_holidays_skipped + 1;
            END IF;
        END LOOP;

        -- Add service days (as calendar days, then adjust)
        IF v_service_days > 0 THEN
            v_date := v_date + (v_service_days * INTERVAL '1 day');
            v_notes := v_notes || ', +' || v_service_days || ' service days';
            IF is_court_holiday(v_date, p_jurisdiction_id) THEN
                v_date := get_next_business_day(v_date, p_jurisdiction_id);
            END IF;
        END IF;

    ELSIF p_calculation_method = 'court_days' THEN
        -- Court days: same as business days in most jurisdictions
        v_notes := 'Court day calculation';

        WHILE v_days_remaining > 0 LOOP
            v_date := v_date + (v_direction * INTERVAL '1 day');
            IF NOT is_court_holiday(v_date, p_jurisdiction_id) THEN
                v_days_remaining := v_days_remaining - 1;
            ELSE
                v_holidays_skipped := v_holidays_skipped + 1;
            END IF;
        END LOOP;

        IF v_service_days > 0 THEN
            v_date := v_date + (v_service_days * INTERVAL '1 day');
            v_notes := v_notes || ', +' || v_service_days || ' service days';
            IF is_court_holiday(v_date, p_jurisdiction_id) THEN
                v_date := get_next_business_day(v_date, p_jurisdiction_id);
            END IF;
        END IF;
    END IF;

    RETURN QUERY SELECT v_date, v_service_days, v_holidays_skipped, v_notes;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- PART 6: RULE DEFINITION ENHANCEMENTS
-- ============================================

-- Add source tracking to rule template deadlines
ALTER TABLE rule_template_deadlines
ADD COLUMN IF NOT EXISTS source_text TEXT,
ADD COLUMN IF NOT EXISTS source_url TEXT,
ADD COLUMN IF NOT EXISTS ai_extracted BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS extraction_confidence DECIMAL(3,2) CHECK (extraction_confidence >= 0 AND extraction_confidence <= 1),
ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS verified_by VARCHAR(255);

-- ============================================
-- PART 7: VIEWS FOR THE UI
-- ============================================

-- View: Jurisdiction tree with rule counts
CREATE OR REPLACE VIEW jurisdiction_tree_view AS
WITH rule_counts AS (
    SELECT
        jurisdiction_id,
        COUNT(*) as rule_set_count
    FROM rule_sets
    WHERE is_active = TRUE
    GROUP BY jurisdiction_id
)
SELECT
    j.id,
    j.code,
    j.name,
    j.canonical_slug,
    j.jurisdiction_type,
    j.parent_jurisdiction_id,
    j.state,
    j.is_active,
    COALESCE(rc.rule_set_count, 0) as rule_set_count,
    (
        SELECT COUNT(*)
        FROM jurisdictions children
        WHERE children.parent_jurisdiction_id = j.id
    ) as child_count
FROM jurisdictions j
LEFT JOIN rule_counts rc ON rc.jurisdiction_id = j.id
WHERE j.is_active = TRUE
ORDER BY j.name;

-- View: Rule sets with dependency counts
CREATE OR REPLACE VIEW rule_set_overview AS
SELECT
    rs.id,
    rs.code,
    rs.name,
    rs.canonical_slug,
    rs.description,
    rs.court_type,
    rs.is_local,
    j.name as jurisdiction_name,
    j.canonical_slug as jurisdiction_slug,
    (
        SELECT COUNT(*)
        FROM rule_set_dependencies rsd
        WHERE rsd.rule_set_id = rs.id
    ) as dependency_count,
    (
        SELECT COUNT(*)
        FROM rule_templates rt
        WHERE rt.rule_set_id = rs.id AND rt.is_active = TRUE
    ) as template_count,
    (
        SELECT COUNT(*)
        FROM rule_templates rt
        JOIN rule_template_deadlines rtd ON rtd.rule_template_id = rt.id
        WHERE rt.rule_set_id = rs.id AND rt.is_active = TRUE AND rtd.is_active = TRUE
    ) as deadline_count
FROM rule_sets rs
JOIN jurisdictions j ON j.id = rs.jurisdiction_id
WHERE rs.is_active = TRUE
ORDER BY j.name, rs.name;

-- ============================================
-- PART 8: RLS POLICIES FOR NEW TABLES
-- ============================================

-- Holidays are public
ALTER TABLE holidays ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Holidays are viewable by everyone" ON holidays
    FOR SELECT USING (true);
CREATE POLICY "Holidays are manageable by service role" ON holidays
    FOR ALL USING (auth.role() = 'service_role');

-- Service method rules are public
ALTER TABLE service_method_rules ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service rules are viewable by everyone" ON service_method_rules
    FOR SELECT USING (true);
CREATE POLICY "Service rules are manageable by service role" ON service_method_rules
    FOR ALL USING (auth.role() = 'service_role');

-- Rule conflicts are public
ALTER TABLE rule_conflicts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Rule conflicts are viewable by everyone" ON rule_conflicts
    FOR SELECT USING (true);
CREATE POLICY "Rule conflicts are manageable by service role" ON rule_conflicts
    FOR ALL USING (auth.role() = 'service_role');

-- ============================================
-- SUCCESS
-- ============================================
SELECT 'Sovereign Graph Engine v1.0 installed successfully' AS status;
