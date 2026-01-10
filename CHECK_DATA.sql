-- Run this in Supabase SQL Editor to check your deadlines
SELECT id, title, deadline_date, status, created_at
FROM deadlines
WHERE user_id = 'cc0d8b5b-ee54-4a1f-96a0-50bb3027e05f'
ORDER BY created_at DESC
LIMIT 20;
