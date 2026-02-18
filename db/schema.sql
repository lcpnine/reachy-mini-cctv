-- Reachy Mini CCTV Database Schema
-- SQLite database for user registration and event logging

-- Users table: stores registered individuals
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Events table: logs all face detection events (both known and unknown)
CREATE TABLE IF NOT EXISTS events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(user_id),  -- NULL for unknown visitors
    confidence REAL NOT NULL,                    -- Recognition confidence score
    photo_path TEXT,                             -- Photo path (only for unknown visitors)
    occurred_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_events_occurred ON events(occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_user ON events(user_id);
CREATE INDEX IF NOT EXISTS idx_events_user_occurred ON events(user_id, occurred_at DESC);

-- Optional: Create a view for convenient querying
CREATE VIEW IF NOT EXISTS events_with_users AS
SELECT
    e.event_id,
    e.user_id,
    u.name AS user_name,
    e.confidence,
    e.photo_path,
    e.occurred_at,
    CASE WHEN e.user_id IS NULL THEN 1 ELSE 0 END AS is_unknown
FROM events e
LEFT JOIN users u ON e.user_id = u.user_id
ORDER BY e.occurred_at DESC;
