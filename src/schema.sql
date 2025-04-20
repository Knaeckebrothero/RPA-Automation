/*
 Database Schema for the application database.
*/


-- Client table
CREATE TABLE IF NOT EXISTS client (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    institute TEXT,
    bafin_id INTEGER NOT NULL,
    address TEXT,
    city TEXT,
    contact_person TEXT,
    phone TEXT,
    fax TEXT,
    email TEXT NOT NULL,
    p033 INTEGER,
    p034 INTEGER,
    p035 INTEGER,
    p036 INTEGER,
    ab2s1n01 INTEGER,
    ab2s1n02 INTEGER,
    ab2s1n03 INTEGER,
    ab2s1n04 INTEGER,
    ab2s1n05 INTEGER,
    ab2s1n06 INTEGER,
    ab2s1n07 INTEGER,
    ab2s1n08 INTEGER,
    ab2s1n09 INTEGER,
    ab2s1n10 INTEGER,
    ab2s1n11 INTEGER,
    ratio FLOAT
);

/* TODO: Refactor the stage table to become something like a "document verification process" table that holds data for
    the verification of the company for a particular year. Meaning this also includes a date and stuff! */
-- Stage Table
CREATE TABLE IF NOT EXISTS audit_case (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL UNIQUE,
    email_id INTEGER,  -- TODO: This attribute is depricated and should be removed at some point! 
    stage INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    comments TEXT,
    FOREIGN KEY (client_id) REFERENCES client(id)
);

-- Document table
CREATE TABLE IF NOT EXISTS document (
    document_hash TEXT NOT NULL,
    audit_case_id INTEGER NOT NULL,
    email_id INTEGER,
    document_filename TEXT,
    document_path TEXT,
    processed BOOLEAN DEFAULT FALSE,  -- This is unnecessary, we can just check if processing_date is not null
    processing_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (document_hash, audit_case_id),
    FOREIGN KEY (audit_case_id) REFERENCES audit_case(id) ON DELETE CASCADE
);

-- User table
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username_email TEXT NOT NULL UNIQUE, -- Should be email
    password_hash TEXT NOT NULL,
    password_salt TEXT NOT NULL,
    role TEXT NOT NULL UNIQUE,  -- 'admin' or 'auditor'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Session keys table with composite primary key
CREATE TABLE IF NOT EXISTS session_key (
    -- Ensure that each user can only have one active session key at a time
    user_id INTEGER NOT NULL,
    session_key TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    PRIMARY KEY (user_id, session_key),
    -- Ensure that if a user is deleted, their session keys are also deleted (to avoid orphaned session keys).
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
);

-- Login attempts tracking table
CREATE TABLE IF NOT EXISTS login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address TEXT NOT NULL,
    attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    successful BOOLEAN NOT NULL DEFAULT 0,
    username_attempted TEXT
);

-- Indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_client_bafin_id ON client(bafin_id);
CREATE INDEX IF NOT EXISTS idx_stage_client_id ON audit_case(client_id);
CREATE INDEX IF NOT EXISTS idx_stage_email_id ON audit_case(email_id);
CREATE INDEX IF NOT EXISTS idx_stage_created_at ON audit_case(created_at);
CREATE INDEX IF NOT EXISTS idx_document_email_id ON document(email_id);
CREATE INDEX IF NOT EXISTS idx_document_hash ON document(document_hash);
CREATE INDEX IF NOT EXISTS idx_session_key_session_key ON session_key(session_key);
CREATE INDEX IF NOT EXISTS idx_user_role ON user(role);
CREATE INDEX IF NOT EXISTS idx_login_attempts_ip_time ON login_attempts(ip_address, attempt_time);

-- Trigger to update the last_updated_at timestamp when a stage record is updated
CREATE TRIGGER IF NOT EXISTS update_stage_last_updated
    AFTER UPDATE ON audit_case
BEGIN
    UPDATE audit_case SET last_updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
