-- Database Schema for the application database


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

-- TODO: Refactor the stage table to become something like a "document verification process" table that holds data
--  for the verification of the company for a particular year. Meaning this also includes a date and stuff!

-- Stage Table
CREATE TABLE IF NOT EXISTS audit_case (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL UNIQUE,
    email_id INTEGER,
    stage INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    comments TEXT,
    FOREIGN KEY (client_id) REFERENCES client(id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_client_bafin_id ON client(bafin_id);
CREATE INDEX IF NOT EXISTS idx_stage_client_id ON audit_case(client_id);
CREATE INDEX IF NOT EXISTS idx_stage_email_id ON audit_case(email_id);
CREATE INDEX IF NOT EXISTS idx_stage_created_at ON audit_case(created_at);

-- Trigger to update the last_updated_at timestamp when a stage record is updated
CREATE TRIGGER IF NOT EXISTS update_stage_last_updated
    AFTER UPDATE ON audit_case
BEGIN
    UPDATE audit_case SET last_updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
