-- ============================================
-- LitDocket Seed Data - Jurisdictions & Rule Sets
-- CompuLaw-style Florida & Federal Rules
-- ============================================
-- Run this AFTER 001_jurisdiction_system.sql

-- ============================================
-- JURISDICTIONS
-- ============================================

-- Federal
INSERT INTO jurisdictions (id, code, name, description, jurisdiction_type, state, is_active)
VALUES
    ('00000000-0000-0000-0000-000000000001', 'FED', 'Federal', 'United States Federal Courts', 'federal', NULL, TRUE)
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

-- Federal District Courts (Florida)
INSERT INTO jurisdictions (id, code, name, description, jurisdiction_type, parent_jurisdiction_id, state, is_active)
VALUES
    ('00000000-0000-0000-0000-000000000010', 'FED-USDC-SD-FL', 'U.S. District Court - Southern District of Florida', 'Federal district court for Southern Florida', 'federal', '00000000-0000-0000-0000-000000000001', 'FL', TRUE),
    ('00000000-0000-0000-0000-000000000011', 'FED-USDC-MD-FL', 'U.S. District Court - Middle District of Florida', 'Federal district court for Middle Florida', 'federal', '00000000-0000-0000-0000-000000000001', 'FL', TRUE),
    ('00000000-0000-0000-0000-000000000012', 'FED-USDC-ND-FL', 'U.S. District Court - Northern District of Florida', 'Federal district court for Northern Florida', 'federal', '00000000-0000-0000-0000-000000000001', 'FL', TRUE)
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

-- Federal Bankruptcy Courts (Florida)
INSERT INTO jurisdictions (id, code, name, description, jurisdiction_type, parent_jurisdiction_id, state, is_active)
VALUES
    ('00000000-0000-0000-0000-000000000020', 'FED-BK-SD-FL', 'U.S. Bankruptcy Court - Southern District of Florida', 'Federal bankruptcy court for Southern Florida', 'bankruptcy', '00000000-0000-0000-0000-000000000010', 'FL', TRUE),
    ('00000000-0000-0000-0000-000000000021', 'FED-BK-MD-FL', 'U.S. Bankruptcy Court - Middle District of Florida', 'Federal bankruptcy court for Middle Florida', 'bankruptcy', '00000000-0000-0000-0000-000000000011', 'FL', TRUE),
    ('00000000-0000-0000-0000-000000000022', 'FED-BK-ND-FL', 'U.S. Bankruptcy Court - Northern District of Florida', 'Federal bankruptcy court for Northern Florida', 'bankruptcy', '00000000-0000-0000-0000-000000000012', 'FL', TRUE)
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

-- Florida State
INSERT INTO jurisdictions (id, code, name, description, jurisdiction_type, state, is_active)
VALUES
    ('00000000-0000-0000-0000-000000000100', 'FL', 'Florida', 'State of Florida Courts', 'state', 'FL', TRUE)
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

-- Florida District Courts of Appeal
INSERT INTO jurisdictions (id, code, name, description, jurisdiction_type, parent_jurisdiction_id, state, is_active)
VALUES
    ('00000000-0000-0000-0000-000000000110', 'FL-DCA-1', 'First District Court of Appeal', 'Florida 1st DCA - Tallahassee', 'appellate', '00000000-0000-0000-0000-000000000100', 'FL', TRUE),
    ('00000000-0000-0000-0000-000000000111', 'FL-DCA-2', 'Second District Court of Appeal', 'Florida 2nd DCA - Lakeland', 'appellate', '00000000-0000-0000-0000-000000000100', 'FL', TRUE),
    ('00000000-0000-0000-0000-000000000112', 'FL-DCA-3', 'Third District Court of Appeal', 'Florida 3rd DCA - Miami', 'appellate', '00000000-0000-0000-0000-000000000100', 'FL', TRUE),
    ('00000000-0000-0000-0000-000000000113', 'FL-DCA-4', 'Fourth District Court of Appeal', 'Florida 4th DCA - West Palm Beach', 'appellate', '00000000-0000-0000-0000-000000000100', 'FL', TRUE),
    ('00000000-0000-0000-0000-000000000114', 'FL-DCA-5', 'Fifth District Court of Appeal', 'Florida 5th DCA - Daytona Beach', 'appellate', '00000000-0000-0000-0000-000000000100', 'FL', TRUE),
    ('00000000-0000-0000-0000-000000000115', 'FL-DCA-6', 'Sixth District Court of Appeal', 'Florida 6th DCA - Tampa', 'appellate', '00000000-0000-0000-0000-000000000100', 'FL', TRUE)
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

-- ============================================
-- RULE SETS - Federal
-- ============================================

-- Federal Rules of Civil Procedure
INSERT INTO rule_sets (id, code, name, description, jurisdiction_id, court_type, is_local, is_active)
VALUES
    ('10000000-0000-0000-0000-000000000001', 'FRCP', 'Federal Rules of Civil Procedure', 'Primary rules for federal civil litigation', '00000000-0000-0000-0000-000000000001', 'district', FALSE, TRUE)
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

-- Federal Rules of Appellate Procedure
INSERT INTO rule_sets (id, code, name, description, jurisdiction_id, court_type, is_local, is_active)
VALUES
    ('10000000-0000-0000-0000-000000000002', 'FRAP', 'Federal Rules of Appellate Procedure', 'Rules for federal appellate courts', '00000000-0000-0000-0000-000000000001', 'appellate_federal', FALSE, TRUE)
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

-- Federal Rules of Bankruptcy Procedure
INSERT INTO rule_sets (id, code, name, description, jurisdiction_id, court_type, is_local, is_active)
VALUES
    ('10000000-0000-0000-0000-000000000003', 'FRBP', 'Federal Rules of Bankruptcy Procedure', 'Rules for federal bankruptcy courts', '00000000-0000-0000-0000-000000000001', 'bankruptcy', FALSE, TRUE)
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

-- ============================================
-- RULE SETS - Florida State
-- ============================================

-- Florida Rules of Civil Procedure
INSERT INTO rule_sets (id, code, name, description, jurisdiction_id, court_type, is_local, is_active)
VALUES
    ('20000000-0000-0000-0000-000000000001', 'FL:RCP', 'Florida Rules of Civil Procedure', 'Primary rules for Florida civil litigation', '00000000-0000-0000-0000-000000000100', 'circuit', FALSE, TRUE)
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

-- Florida Rules of Criminal Procedure
INSERT INTO rule_sets (id, code, name, description, jurisdiction_id, court_type, is_local, is_active)
VALUES
    ('20000000-0000-0000-0000-000000000002', 'FL:CPP', 'Florida Rules of Criminal Procedure', 'Rules for Florida criminal cases', '00000000-0000-0000-0000-000000000100', 'circuit', FALSE, TRUE)
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

-- Florida Rules of Appellate Procedure
INSERT INTO rule_sets (id, code, name, description, jurisdiction_id, court_type, is_local, is_active)
VALUES
    ('20000000-0000-0000-0000-000000000003', 'FL:RAP', 'Florida Rules of Appellate Procedure', 'Rules for Florida appellate courts', '00000000-0000-0000-0000-000000000100', 'appellate_state', FALSE, TRUE)
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

-- Florida Probate Rules
INSERT INTO rule_sets (id, code, name, description, jurisdiction_id, court_type, is_local, is_active)
VALUES
    ('20000000-0000-0000-0000-000000000004', 'FL:PB-FPR', 'Florida Probate Rules', 'Rules for Florida probate proceedings', '00000000-0000-0000-0000-000000000100', 'circuit', FALSE, TRUE)
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

-- Florida Family Law Rules
INSERT INTO rule_sets (id, code, name, description, jurisdiction_id, court_type, is_local, is_active)
VALUES
    ('20000000-0000-0000-0000-000000000005', 'FL:FAM', 'Florida Family Law Rules of Procedure', 'Rules for Florida family law cases', '00000000-0000-0000-0000-000000000100', 'circuit', FALSE, TRUE)
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

-- Florida Small Claims Rules
INSERT INTO rule_sets (id, code, name, description, jurisdiction_id, court_type, is_local, is_active)
VALUES
    ('20000000-0000-0000-0000-000000000006', 'FL:SCR', 'Florida Small Claims Rules', 'Rules for Florida small claims court', '00000000-0000-0000-0000-000000000100', 'county', FALSE, TRUE)
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

-- ============================================
-- RULE SETS - Bankruptcy (Chapter-Specific)
-- ============================================

-- Southern District Bankruptcy - Chapter 7
INSERT INTO rule_sets (id, code, name, description, jurisdiction_id, court_type, is_local, is_active)
VALUES
    ('30000000-0000-0000-0000-000000000001', 'FL:BRSD-7', 'S.D. Florida Bankruptcy Local Rules - Chapter 7', 'Local bankruptcy rules for Chapter 7 liquidation', '00000000-0000-0000-0000-000000000020', 'bankruptcy', TRUE, TRUE)
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

-- Southern District Bankruptcy - Chapter 11
INSERT INTO rule_sets (id, code, name, description, jurisdiction_id, court_type, is_local, is_active)
VALUES
    ('30000000-0000-0000-0000-000000000002', 'FL:BRSD-11', 'S.D. Florida Bankruptcy Local Rules - Chapter 11', 'Local bankruptcy rules for Chapter 11 reorganization', '00000000-0000-0000-0000-000000000020', 'bankruptcy', TRUE, TRUE)
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

-- Southern District Bankruptcy - Chapter 13
INSERT INTO rule_sets (id, code, name, description, jurisdiction_id, court_type, is_local, is_active)
VALUES
    ('30000000-0000-0000-0000-000000000003', 'FL:BRSD-13', 'S.D. Florida Bankruptcy Local Rules - Chapter 13', 'Local bankruptcy rules for Chapter 13 wage earner plan', '00000000-0000-0000-0000-000000000020', 'bankruptcy', TRUE, TRUE)
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

-- Middle District Bankruptcy - Chapter 7
INSERT INTO rule_sets (id, code, name, description, jurisdiction_id, court_type, is_local, is_active)
VALUES
    ('30000000-0000-0000-0000-000000000011', 'FL:BRMD-7', 'M.D. Florida Bankruptcy Local Rules - Chapter 7', 'Local bankruptcy rules for Chapter 7 liquidation', '00000000-0000-0000-0000-000000000021', 'bankruptcy', TRUE, TRUE)
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

-- Middle District Bankruptcy - Chapter 11
INSERT INTO rule_sets (id, code, name, description, jurisdiction_id, court_type, is_local, is_active)
VALUES
    ('30000000-0000-0000-0000-000000000012', 'FL:BRMD-11', 'M.D. Florida Bankruptcy Local Rules - Chapter 11', 'Local bankruptcy rules for Chapter 11 reorganization', '00000000-0000-0000-0000-000000000021', 'bankruptcy', TRUE, TRUE)
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

-- Middle District Bankruptcy - Chapter 13
INSERT INTO rule_sets (id, code, name, description, jurisdiction_id, court_type, is_local, is_active)
VALUES
    ('30000000-0000-0000-0000-000000000013', 'FL:BRMD-13', 'M.D. Florida Bankruptcy Local Rules - Chapter 13', 'Local bankruptcy rules for Chapter 13 wage earner plan', '00000000-0000-0000-0000-000000000021', 'bankruptcy', TRUE, TRUE)
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

-- ============================================
-- RULE SET DEPENDENCIES
-- ============================================
-- Bankruptcy local rules require FRCP and FRBP to load concurrently

-- S.D. Florida Bankruptcy rules require FRCP
INSERT INTO rule_set_dependencies (rule_set_id, required_rule_set_id, dependency_type, priority, notes)
VALUES
    ('30000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 'concurrent', 1, 'FRCP applies in bankruptcy'),
    ('30000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000003', 'concurrent', 2, 'FRBP is primary bankruptcy rules'),
    ('30000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000001', 'concurrent', 1, 'FRCP applies in bankruptcy'),
    ('30000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000003', 'concurrent', 2, 'FRBP is primary bankruptcy rules'),
    ('30000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000001', 'concurrent', 1, 'FRCP applies in bankruptcy'),
    ('30000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000003', 'concurrent', 2, 'FRBP is primary bankruptcy rules')
ON CONFLICT (rule_set_id, required_rule_set_id) DO NOTHING;

-- M.D. Florida Bankruptcy rules require FRCP
INSERT INTO rule_set_dependencies (rule_set_id, required_rule_set_id, dependency_type, priority, notes)
VALUES
    ('30000000-0000-0000-0000-000000000011', '10000000-0000-0000-0000-000000000001', 'concurrent', 1, 'FRCP applies in bankruptcy'),
    ('30000000-0000-0000-0000-000000000011', '10000000-0000-0000-0000-000000000003', 'concurrent', 2, 'FRBP is primary bankruptcy rules'),
    ('30000000-0000-0000-0000-000000000012', '10000000-0000-0000-0000-000000000001', 'concurrent', 1, 'FRCP applies in bankruptcy'),
    ('30000000-0000-0000-0000-000000000012', '10000000-0000-0000-0000-000000000003', 'concurrent', 2, 'FRBP is primary bankruptcy rules'),
    ('30000000-0000-0000-0000-000000000013', '10000000-0000-0000-0000-000000000001', 'concurrent', 1, 'FRCP applies in bankruptcy'),
    ('30000000-0000-0000-0000-000000000013', '10000000-0000-0000-0000-000000000003', 'concurrent', 2, 'FRBP is primary bankruptcy rules')
ON CONFLICT (rule_set_id, required_rule_set_id) DO NOTHING;

-- ============================================
-- COURT LOCATIONS
-- ============================================

-- Southern District of Florida Courts
INSERT INTO court_locations (id, jurisdiction_id, name, short_name, court_type, district, detection_patterns, case_number_pattern, default_rule_set_id)
VALUES
    ('40000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000010',
     'U.S. District Court - Southern District of Florida - Miami', 'FLSD-Miami',
     'district', 'Southern',
     '["UNITED STATES DISTRICT COURT.*SOUTHERN DISTRICT OF FLORIDA", "S\\.?D\\.? ?FL", "FLSD"]'::JSONB,
     '[0-9]{1,2}:[0-9]{2}-[a-zA-Z]{2,4}-[0-9]+',
     '10000000-0000-0000-0000-000000000001')
ON CONFLICT DO NOTHING;

-- Middle District of Florida Courts
INSERT INTO court_locations (id, jurisdiction_id, name, short_name, court_type, district, detection_patterns, case_number_pattern, default_rule_set_id)
VALUES
    ('40000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000011',
     'U.S. District Court - Middle District of Florida - Tampa', 'FLMD-Tampa',
     'district', 'Middle',
     '["UNITED STATES DISTRICT COURT.*MIDDLE DISTRICT OF FLORIDA", "M\\.?D\\.? ?FL", "FLMD"]'::JSONB,
     '[0-9]{1,2}:[0-9]{2}-[a-zA-Z]{2,4}-[0-9]+',
     '10000000-0000-0000-0000-000000000001')
ON CONFLICT DO NOTHING;

-- Bankruptcy Courts
INSERT INTO court_locations (id, jurisdiction_id, name, short_name, court_type, district, detection_patterns, case_number_pattern, default_rule_set_id)
VALUES
    ('40000000-0000-0000-0000-000000000010', '00000000-0000-0000-0000-000000000020',
     'U.S. Bankruptcy Court - Southern District of Florida', 'FLSB',
     'bankruptcy', 'Southern',
     '["UNITED STATES BANKRUPTCY COURT.*SOUTHERN DISTRICT OF FLORIDA", "BANKRUPTCY.*S\\.?D\\.? ?FL", "FLSB"]'::JSONB,
     '[0-9]{1,2}-[0-9]{5}',
     '30000000-0000-0000-0000-000000000001'),
    ('40000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000021',
     'U.S. Bankruptcy Court - Middle District of Florida', 'FLMB',
     'bankruptcy', 'Middle',
     '["UNITED STATES BANKRUPTCY COURT.*MIDDLE DISTRICT OF FLORIDA", "BANKRUPTCY.*M\\.?D\\.? ?FL", "FLMB"]'::JSONB,
     '[0-9]{1,2}-[0-9]{5}',
     '30000000-0000-0000-0000-000000000011')
ON CONFLICT DO NOTHING;

-- ============================================
-- RULE TEMPLATES - FRCP Complaint Served
-- ============================================

INSERT INTO rule_templates (id, rule_set_id, rule_code, name, description, trigger_type, citation, is_active)
VALUES
    ('50000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001',
     'FRCP-4-12', 'Federal Civil - Complaint Service',
     'Deadlines triggered when complaint is served under FRCP',
     'complaint_served', 'Fed. R. Civ. P. 4, 12', TRUE)
ON CONFLICT (rule_set_id, rule_code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

-- FRCP Complaint Served Deadlines
INSERT INTO rule_template_deadlines (rule_template_id, name, description, days_from_trigger, priority, party_responsible, action_required, calculation_method, add_service_days, rule_citation, display_order)
VALUES
    ('50000000-0000-0000-0000-000000000001', 'Answer Due', 'Defendant must file answer to complaint', 21, 'critical', 'defendant', 'File Answer or Motion to Dismiss', 'calendar_days', TRUE, 'Fed. R. Civ. P. 12(a)(1)(A)(i)', 1),
    ('50000000-0000-0000-0000-000000000001', 'Motion to Dismiss Deadline', 'Last day to file Rule 12(b) motion', 21, 'critical', 'defendant', 'File Motion to Dismiss if applicable', 'calendar_days', TRUE, 'Fed. R. Civ. P. 12(b)', 2),
    ('50000000-0000-0000-0000-000000000001', 'Rule 26(f) Conference', 'Parties must confer regarding discovery plan', 21, 'important', 'both', 'Schedule and conduct Rule 26(f) conference', 'calendar_days', FALSE, 'Fed. R. Civ. P. 26(f)', 3)
ON CONFLICT DO NOTHING;

-- ============================================
-- RULE TEMPLATES - Florida RCP Complaint Served
-- ============================================

INSERT INTO rule_templates (id, rule_set_id, rule_code, name, description, trigger_type, citation, is_active)
VALUES
    ('50000000-0000-0000-0000-000000000010', '20000000-0000-0000-0000-000000000001',
     'FL-RCP-1.140', 'Florida Civil - Complaint Service',
     'Deadlines triggered when complaint is served under Florida Rules',
     'complaint_served', 'Fla. R. Civ. P. 1.140', TRUE)
ON CONFLICT (rule_set_id, rule_code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

-- Florida RCP Complaint Served Deadlines
INSERT INTO rule_template_deadlines (rule_template_id, name, description, days_from_trigger, priority, party_responsible, action_required, calculation_method, add_service_days, rule_citation, display_order)
VALUES
    ('50000000-0000-0000-0000-000000000010', 'Answer Due', 'Defendant must file answer to complaint', 20, 'critical', 'defendant', 'File Answer or Motion to Dismiss', 'calendar_days', TRUE, 'Fla. R. Civ. P. 1.140(a)(1)', 1),
    ('50000000-0000-0000-0000-000000000010', 'Motion to Dismiss Deadline', 'Last day to file motion to dismiss', 20, 'critical', 'defendant', 'File Motion to Dismiss if applicable', 'calendar_days', TRUE, 'Fla. R. Civ. P. 1.140(b)', 2),
    ('50000000-0000-0000-0000-000000000010', 'Affirmative Defenses Due', 'Defendant must raise affirmative defenses', 20, 'important', 'defendant', 'Include all affirmative defenses in answer', 'calendar_days', TRUE, 'Fla. R. Civ. P. 1.110(d)', 3)
ON CONFLICT DO NOTHING;

-- ============================================
-- RULE TEMPLATES - Trial Date Trigger
-- ============================================

INSERT INTO rule_templates (id, rule_set_id, rule_code, name, description, trigger_type, citation, is_active)
VALUES
    ('50000000-0000-0000-0000-000000000020', '10000000-0000-0000-0000-000000000001',
     'FRCP-TRIAL', 'Federal Civil - Trial Date Set',
     'Deadlines triggered when trial date is scheduled',
     'trial_date', 'Fed. R. Civ. P. 16, 26', TRUE),
    ('50000000-0000-0000-0000-000000000021', '20000000-0000-0000-0000-000000000001',
     'FL-RCP-TRIAL', 'Florida Civil - Trial Date Set',
     'Deadlines triggered when trial date is scheduled',
     'trial_date', 'Fla. R. Civ. P. 1.200, 1.440', TRUE)
ON CONFLICT (rule_set_id, rule_code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

-- Federal Trial Date Deadlines
INSERT INTO rule_template_deadlines (rule_template_id, name, description, days_from_trigger, priority, party_responsible, action_required, calculation_method, rule_citation, display_order)
VALUES
    ('50000000-0000-0000-0000-000000000020', 'Final Pretrial Conference', 'Attend final pretrial conference', -14, 'critical', 'both', 'Attend pretrial conference', 'calendar_days', 'Fed. R. Civ. P. 16', 1),
    ('50000000-0000-0000-0000-000000000020', 'Motions in Limine Due', 'File all motions in limine', -21, 'important', 'both', 'File motions in limine', 'calendar_days', 'Local Rules', 2),
    ('50000000-0000-0000-0000-000000000020', 'Proposed Jury Instructions', 'Submit proposed jury instructions', -14, 'important', 'both', 'File proposed jury instructions', 'calendar_days', 'Fed. R. Civ. P. 51', 3),
    ('50000000-0000-0000-0000-000000000020', 'Witness List Due', 'File final witness list', -30, 'important', 'both', 'File witness list', 'calendar_days', 'Fed. R. Civ. P. 26(a)(3)', 4),
    ('50000000-0000-0000-0000-000000000020', 'Exhibit List Due', 'File final exhibit list', -30, 'important', 'both', 'File exhibit list', 'calendar_days', 'Fed. R. Civ. P. 26(a)(3)', 5),
    ('50000000-0000-0000-0000-000000000020', 'Discovery Cutoff', 'All discovery must be completed', -60, 'critical', 'both', 'Complete all discovery', 'calendar_days', 'Fed. R. Civ. P. 26', 6),
    ('50000000-0000-0000-0000-000000000020', 'Expert Reports Due', 'File expert witness reports', -90, 'important', 'both', 'File expert reports', 'calendar_days', 'Fed. R. Civ. P. 26(a)(2)', 7),
    ('50000000-0000-0000-0000-000000000020', 'Dispositive Motions Due', 'File all dispositive motions', -60, 'critical', 'both', 'File summary judgment motions', 'calendar_days', 'Fed. R. Civ. P. 56', 8)
ON CONFLICT DO NOTHING;

-- Florida Trial Date Deadlines
INSERT INTO rule_template_deadlines (rule_template_id, name, description, days_from_trigger, priority, party_responsible, action_required, calculation_method, rule_citation, display_order)
VALUES
    ('50000000-0000-0000-0000-000000000021', 'Pretrial Conference', 'Attend pretrial conference', -10, 'critical', 'both', 'Attend pretrial conference', 'calendar_days', 'Fla. R. Civ. P. 1.200', 1),
    ('50000000-0000-0000-0000-000000000021', 'Motions in Limine Due', 'File all motions in limine', -15, 'important', 'both', 'File motions in limine', 'calendar_days', 'Local Rules', 2),
    ('50000000-0000-0000-0000-000000000021', 'Proposed Jury Instructions', 'Submit proposed jury instructions', -10, 'important', 'both', 'File proposed jury instructions', 'calendar_days', 'Fla. R. Civ. P. 1.470', 3),
    ('50000000-0000-0000-0000-000000000021', 'Witness List Due', 'File final witness list', -20, 'important', 'both', 'File witness list', 'calendar_days', 'Fla. R. Civ. P. 1.280', 4),
    ('50000000-0000-0000-0000-000000000021', 'Exhibit List Due', 'File final exhibit list', -20, 'important', 'both', 'File exhibit list', 'calendar_days', 'Fla. R. Civ. P. 1.280', 5),
    ('50000000-0000-0000-0000-000000000021', 'Discovery Cutoff', 'All discovery must be completed', -45, 'critical', 'both', 'Complete all discovery', 'calendar_days', 'Fla. R. Civ. P. 1.280', 6)
ON CONFLICT DO NOTHING;

-- Success message
SELECT 'Seed data inserted successfully' AS status;
