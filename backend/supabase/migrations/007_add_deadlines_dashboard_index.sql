-- Migration: Add composite index for deadline dashboard queries
-- This index optimizes queries that filter by case_id, date range, and status
-- Common dashboard queries: WHERE case_id = ? AND deadline_date BETWEEN ? AND ? AND status = ?

CREATE INDEX IF NOT EXISTS idx_deadlines_case_date_status 
ON deadlines(case_id, deadline_date, status);