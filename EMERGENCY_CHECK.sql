-- Run these queries in Supabase SQL Editor to investigate

-- 1. Check if ANY deadlines exist in the entire database
SELECT COUNT(*) as total_deadlines FROM deadlines;

-- 2. Check all cases for your user
SELECT id, case_number, title, created_at
FROM cases
WHERE user_id = 'cc0d8b5b-ee54-4a1f-96a0-50bb3027e05f'
ORDER BY created_at DESC;

-- 3. Check if there's an audit log of deleted deadlines
SELECT
    audit_id,
    table_name,
    record_id,
    action,
    changed_at,
    old_values
FROM audit_log
WHERE table_name = 'deadlines'
    AND action = 'DELETE'
ORDER BY changed_at DESC
LIMIT 20;

-- 4. Check deadline_history for traces of deleted deadlines
SELECT
    id,
    deadline_id,
    change_type,
    field_changed,
    old_value,
    new_value,
    created_at
FROM deadline_history
ORDER BY created_at DESC
LIMIT 20;
