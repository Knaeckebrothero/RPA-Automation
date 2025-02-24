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

-- Status Table
CREATE TABLE IF NOT EXISTS status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    email_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    comment TEXT,
    FOREIGN KEY (company_id) REFERENCES clients(id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_client_bafin_id ON client(bafin_id);
CREATE INDEX IF NOT EXISTS idx_status_company_id ON status(company_id);
CREATE INDEX IF NOT EXISTS idx_status_email_id ON status(email_id);

-- Trigger to update the last_updated_at timestamp when a status record is updated
CREATE TRIGGER IF NOT EXISTS update_status_last_updated
    AFTER UPDATE ON status
BEGIN
    UPDATE status SET last_updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
