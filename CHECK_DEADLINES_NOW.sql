-- Run this in Supabase SQL Editor NOW
-- Check if deadlines exist for case 'd468534b-e883-4790-b7a7-61e09a25b9dd'
SELECT
    id,
    title,
    deadline_date,
    status,
    is_archived,
    created_at
FROM deadlines
WHERE case_id = 'd468534b-e883-4790-b7a7-61e09a25b9dd'
ORDER BY created_at DESC;
