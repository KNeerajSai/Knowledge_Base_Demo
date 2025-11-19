-- Healthcare Pipeline PostgreSQL Setup
-- Run this script as PostgreSQL admin (postgres user)

-- Create user
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'healthcare_user') THEN
        CREATE USER healthcare_user WITH PASSWORD '!Xm7t^@Be2OI@atk';
        RAISE NOTICE 'User healthcare_user created';
    ELSE
        ALTER USER healthcare_user WITH PASSWORD '!Xm7t^@Be2OI@atk';
        RAISE NOTICE 'User healthcare_user password updated';
    END IF;
END
$$;

-- Grant privileges
ALTER USER healthcare_user CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE postgres TO healthcare_user;

-- Create healthcare database
CREATE DATABASE healthcare_knowledge_base OWNER healthcare_user;

-- Connect to healthcare database and create schema
\c healthcare_knowledge_base

-- Healthcare schema
CREATE TABLE IF NOT EXISTS payers (
    payer_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    domain VARCHAR(255),
    provider_portal_url TEXT,
    market_share DECIMAL(5,2),
    priority VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    document_id SERIAL PRIMARY KEY,
    payer_id INTEGER REFERENCES payers(payer_id),
    filename VARCHAR(255) NOT NULL,
    file_path TEXT,
    file_size_bytes INTEGER,
    document_type VARCHAR(100),
    original_url TEXT,
    downloaded_at TIMESTAMP,
    processed_at TIMESTAMP,
    azure_document_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_intelligence_results (
    result_id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(document_id),
    azure_model_used VARCHAR(100),
    confidence_score DECIMAL(5,4),
    page_count INTEGER,
    processing_time_seconds DECIMAL(8,2),
    raw_response JSONB,
    structured_data JSONB,
    extraction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS healthcare_rules (
    rule_id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(document_id),
    rule_type VARCHAR(50),
    rule_title VARCHAR(500),
    rule_content TEXT,
    page_number INTEGER,
    confidence_score DECIMAL(5,4),
    geographic_scope VARCHAR(100),
    effective_date DATE,
    expiration_date DATE,
    extracted_entities JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_documents_payer_id ON documents(payer_id);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);
CREATE INDEX IF NOT EXISTS idx_rules_document_id ON healthcare_rules(document_id);
CREATE INDEX IF NOT EXISTS idx_rules_type ON healthcare_rules(rule_type);
CREATE INDEX IF NOT EXISTS idx_di_results_document_id ON document_intelligence_results(document_id);
CREATE INDEX IF NOT EXISTS idx_di_structured_data_gin ON document_intelligence_results USING GIN (structured_data);
CREATE INDEX IF NOT EXISTS idx_rules_entities_gin ON healthcare_rules USING GIN (extracted_entities);

-- Insert sample data
INSERT INTO payers (name, domain, provider_portal_url, priority) VALUES
('CountyCare Health Plan', 'countycare.com', 'https://countycare.com/providers/', 'medium'),
('United Healthcare', 'uhc.com', 'https://www.uhcprovider.com/', 'high'),
('Anthem/Elevance Health', 'anthem.com', 'https://providers.anthem.com/', 'high')
ON CONFLICT (name) DO NOTHING;

-- Grant all permissions to healthcare user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO healthcare_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO healthcare_user;

-- Show success
SELECT 'Healthcare database setup complete!' as status;
SELECT 'User: healthcare_user' as user_info;
SELECT 'Database: healthcare_knowledge_base' as db_info;
