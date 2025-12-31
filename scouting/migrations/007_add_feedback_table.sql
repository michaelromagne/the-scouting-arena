-- Add feedback table for user feedback submissions
-- Migration: 007_add_feedback_table
-- Date: 2025-12-28

CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    sentiment INTEGER NOT NULL,
    comment TEXT,
    page VARCHAR NOT NULL,
    timestamp VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Add index on created_at for efficient querying by date
CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON feedback(created_at DESC);

-- Add index on page for filtering by page
CREATE INDEX IF NOT EXISTS idx_feedback_page ON feedback(page);
