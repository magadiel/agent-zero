-- Audit Trail Schema for Agile AI Control Layer
-- This schema provides an immutable, cryptographically verifiable audit trail
-- for all agent decisions, actions, and system events

-- Create audit database (if using PostgreSQL)
-- CREATE DATABASE IF NOT EXISTS agile_ai_audit;

-- Use the audit database
-- USE agile_ai_audit;

-- Main audit log table
-- This table is append-only with no UPDATE or DELETE permissions
CREATE TABLE IF NOT EXISTS audit_log (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,
    
    -- Timestamp with microsecond precision
    timestamp TIMESTAMP(6) WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Event classification
    event_type VARCHAR(50) NOT NULL,  -- DECISION, ACTION, INTERVENTION, ERROR, WARNING, INFO
    event_category VARCHAR(100) NOT NULL,  -- ETHICS, SAFETY, RESOURCE, WORKFLOW, TEAM, etc.
    severity VARCHAR(20) NOT NULL DEFAULT 'INFO',  -- CRITICAL, HIGH, MEDIUM, LOW, INFO
    
    -- Actor information
    actor_type VARCHAR(50) NOT NULL,  -- AGENT, SYSTEM, HUMAN, TEAM
    actor_id VARCHAR(255) NOT NULL,
    actor_role VARCHAR(100),  -- PM, ARCHITECT, DEVELOPER, QA, etc.
    team_id VARCHAR(255),
    
    -- Event details
    event_id VARCHAR(255) UNIQUE NOT NULL,  -- UUID for the event
    event_description TEXT NOT NULL,
    event_data JSONB,  -- Structured event data
    
    -- Decision tracking (for DECISION events)
    decision_id VARCHAR(255),
    decision_type VARCHAR(100),  -- ETHICAL, RESOURCE_ALLOCATION, SAFETY, etc.
    decision_result VARCHAR(50),  -- APPROVED, REJECTED, MODIFIED, DEFERRED
    decision_reasoning TEXT,
    
    -- Resource tracking
    resource_type VARCHAR(50),  -- CPU, MEMORY, API_CALLS, etc.
    resource_amount DECIMAL(20, 4),
    resource_limit DECIMAL(20, 4),
    
    -- Compliance and ethics
    ethical_assessment JSONB,  -- Ethical scores and evaluations
    compliance_status VARCHAR(50),  -- COMPLIANT, NON_COMPLIANT, WAIVED
    compliance_details TEXT,
    
    -- Cryptographic integrity
    previous_hash VARCHAR(128),  -- SHA-512 hash of previous record
    current_hash VARCHAR(128) NOT NULL,  -- SHA-512 hash of current record
    signature VARCHAR(512),  -- Digital signature of the record
    
    -- Retention and archival
    retention_policy VARCHAR(50) DEFAULT 'STANDARD',  -- PERMANENT, LONG_TERM, STANDARD, SHORT_TERM
    retention_until DATE,
    archived BOOLEAN DEFAULT FALSE,
    archive_location VARCHAR(255),
    
    -- Indexes for performance
    INDEX idx_timestamp (timestamp),
    INDEX idx_event_type (event_type),
    INDEX idx_event_category (event_category),
    INDEX idx_severity (severity),
    INDEX idx_actor_id (actor_id),
    INDEX idx_team_id (team_id),
    INDEX idx_event_id (event_id),
    INDEX idx_decision_id (decision_id),
    INDEX idx_retention_until (retention_until),
    INDEX idx_archived (archived)
);

-- Audit metadata table
-- Tracks information about the audit system itself
CREATE TABLE IF NOT EXISTS audit_metadata (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255),
    INDEX idx_key (key)
);

-- Audit signatures table
-- Stores cryptographic signatures and verification data
CREATE TABLE IF NOT EXISTS audit_signatures (
    id BIGSERIAL PRIMARY KEY,
    audit_log_id BIGINT NOT NULL REFERENCES audit_log(id),
    signature_type VARCHAR(50) NOT NULL,  -- SHA512, RSA, ECDSA, etc.
    signature_value TEXT NOT NULL,
    public_key_id VARCHAR(255),
    signed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    verified_at TIMESTAMP WITH TIME ZONE,
    verification_status VARCHAR(50),  -- VALID, INVALID, PENDING
    INDEX idx_audit_log_id (audit_log_id),
    INDEX idx_signature_type (signature_type),
    INDEX idx_verification_status (verification_status)
);

-- Audit retention policies table
CREATE TABLE IF NOT EXISTS audit_retention_policies (
    id SERIAL PRIMARY KEY,
    policy_name VARCHAR(50) UNIQUE NOT NULL,
    event_category VARCHAR(100),
    retention_days INTEGER NOT NULL,
    archive_after_days INTEGER,
    delete_after_days INTEGER,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_policy_name (policy_name),
    INDEX idx_event_category (event_category),
    INDEX idx_active (active)
);

-- Audit query log
-- Tracks who queries the audit log and when
CREATE TABLE IF NOT EXISTS audit_query_log (
    id BIGSERIAL PRIMARY KEY,
    query_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    queried_by VARCHAR(255) NOT NULL,
    query_type VARCHAR(50) NOT NULL,  -- SELECT, EXPORT, REPORT, etc.
    query_parameters JSONB,
    result_count INTEGER,
    execution_time_ms INTEGER,
    ip_address INET,
    user_agent TEXT,
    INDEX idx_query_timestamp (query_timestamp),
    INDEX idx_queried_by (queried_by)
);

-- Create views for common queries

-- Recent critical events view
CREATE OR REPLACE VIEW recent_critical_events AS
SELECT 
    timestamp,
    event_type,
    event_category,
    actor_id,
    event_description,
    decision_result,
    compliance_status
FROM audit_log
WHERE severity IN ('CRITICAL', 'HIGH')
    AND timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;

-- Agent activity summary view
CREATE OR REPLACE VIEW agent_activity_summary AS
SELECT 
    actor_id,
    actor_role,
    team_id,
    COUNT(*) as total_events,
    COUNT(DISTINCT event_type) as event_types,
    COUNT(CASE WHEN decision_result = 'REJECTED' THEN 1 END) as rejected_decisions,
    COUNT(CASE WHEN compliance_status = 'NON_COMPLIANT' THEN 1 END) as non_compliant_events,
    MAX(timestamp) as last_activity
FROM audit_log
WHERE actor_type = 'AGENT'
GROUP BY actor_id, actor_role, team_id;

-- Resource usage summary view
CREATE OR REPLACE VIEW resource_usage_summary AS
SELECT 
    DATE_TRUNC('hour', timestamp) as hour,
    resource_type,
    actor_id,
    team_id,
    SUM(resource_amount) as total_usage,
    MAX(resource_amount) as peak_usage,
    AVG(resource_amount) as avg_usage,
    MAX(resource_limit) as resource_limit
FROM audit_log
WHERE resource_type IS NOT NULL
GROUP BY DATE_TRUNC('hour', timestamp), resource_type, actor_id, team_id;

-- Compliance status view
CREATE OR REPLACE VIEW compliance_status_overview AS
SELECT 
    DATE(timestamp) as date,
    event_category,
    compliance_status,
    COUNT(*) as event_count,
    COUNT(DISTINCT actor_id) as unique_actors,
    COUNT(DISTINCT team_id) as unique_teams
FROM audit_log
WHERE compliance_status IS NOT NULL
GROUP BY DATE(timestamp), event_category, compliance_status
ORDER BY date DESC, event_category;

-- Create functions for audit operations

-- Function to verify hash chain integrity
CREATE OR REPLACE FUNCTION verify_hash_chain()
RETURNS TABLE(
    id BIGINT,
    is_valid BOOLEAN,
    error_message TEXT
) AS $$
DECLARE
    rec RECORD;
    prev_hash VARCHAR(128) := '';
    expected_hash VARCHAR(128);
BEGIN
    FOR rec IN SELECT * FROM audit_log ORDER BY id ASC
    LOOP
        IF rec.id > 1 AND rec.previous_hash != prev_hash THEN
            RETURN QUERY SELECT rec.id, FALSE, 
                'Hash chain broken: expected ' || prev_hash || ' but got ' || rec.previous_hash;
        END IF;
        prev_hash := rec.current_hash;
    END LOOP;
    RETURN QUERY SELECT 0::BIGINT, TRUE, 'Hash chain valid'::TEXT;
END;
$$ LANGUAGE plpgsql;

-- Function to apply retention policies
CREATE OR REPLACE FUNCTION apply_retention_policies()
RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER := 0;
    rec RECORD;
BEGIN
    -- Archive old records based on retention policies
    FOR rec IN SELECT * FROM audit_retention_policies WHERE active = TRUE
    LOOP
        UPDATE audit_log
        SET archived = TRUE,
            archive_location = 'archive_' || TO_CHAR(NOW(), 'YYYY_MM')
        WHERE NOT archived
            AND event_category = rec.event_category
            AND timestamp < NOW() - (rec.archive_after_days || ' days')::INTERVAL;
        
        archived_count := archived_count + ROW_COUNT;
    END LOOP;
    
    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;

-- Create triggers

-- Trigger to prevent updates and deletes on audit_log
CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit log records cannot be modified or deleted';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER no_update_audit_log
BEFORE UPDATE ON audit_log
FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();

CREATE TRIGGER no_delete_audit_log
BEFORE DELETE ON audit_log
FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();

-- Trigger to update audit_metadata on certain operations
CREATE OR REPLACE FUNCTION update_audit_metadata()
RETURNS TRIGGER AS $$
BEGIN
    -- Update last audit entry timestamp
    INSERT INTO audit_metadata (key, value, updated_by)
    VALUES ('last_audit_entry', NOW()::TEXT, NEW.actor_id)
    ON CONFLICT (key) DO UPDATE
    SET value = NOW()::TEXT, updated_at = NOW(), updated_by = NEW.actor_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_metadata_on_insert
AFTER INSERT ON audit_log
FOR EACH ROW EXECUTE FUNCTION update_audit_metadata();

-- Default retention policies
INSERT INTO audit_retention_policies (policy_name, event_category, retention_days, archive_after_days, delete_after_days, description)
VALUES 
    ('PERMANENT', 'ETHICS', 36500, NULL, NULL, 'Permanent retention for ethical decisions'),
    ('PERMANENT', 'SAFETY', 36500, NULL, NULL, 'Permanent retention for safety events'),
    ('LONG_TERM', 'DECISION', 2555, 365, NULL, 'Seven year retention for decisions'),
    ('LONG_TERM', 'RESOURCE', 2555, 365, NULL, 'Seven year retention for resource allocations'),
    ('STANDARD', 'WORKFLOW', 365, 90, 730, 'One year active, two year total retention'),
    ('STANDARD', 'TEAM', 365, 90, 730, 'One year active, two year total retention'),
    ('SHORT_TERM', 'INFO', 90, 30, 180, 'Three month active, six month total retention')
ON CONFLICT (policy_name) DO NOTHING;

-- Initial metadata entries
INSERT INTO audit_metadata (key, value, updated_by)
VALUES 
    ('schema_version', '1.0.0', 'SYSTEM'),
    ('deployment_date', NOW()::TEXT, 'SYSTEM'),
    ('hash_algorithm', 'SHA-512', 'SYSTEM'),
    ('signature_algorithm', 'RSA-2048', 'SYSTEM')
ON CONFLICT (key) DO NOTHING;

-- Grant appropriate permissions (adjust based on your database system)
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO audit_reader;
-- GRANT INSERT ON audit_log TO audit_writer;
-- GRANT SELECT ON audit_log TO audit_writer;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO audit_writer;

-- Create indexes for optimized queries
CREATE INDEX IF NOT EXISTS idx_audit_log_composite_1 
ON audit_log(actor_id, timestamp DESC) 
WHERE archived = FALSE;

CREATE INDEX IF NOT EXISTS idx_audit_log_composite_2 
ON audit_log(event_category, severity, timestamp DESC) 
WHERE archived = FALSE;

CREATE INDEX IF NOT EXISTS idx_audit_log_composite_3 
ON audit_log(team_id, event_type, timestamp DESC) 
WHERE archived = FALSE AND team_id IS NOT NULL;

-- Add comments for documentation
COMMENT ON TABLE audit_log IS 'Immutable audit trail for all agent decisions, actions, and system events';
COMMENT ON COLUMN audit_log.current_hash IS 'SHA-512 hash of the current record for integrity verification';
COMMENT ON COLUMN audit_log.previous_hash IS 'SHA-512 hash of the previous record to form a hash chain';
COMMENT ON COLUMN audit_log.signature IS 'Digital signature of the record for non-repudiation';
COMMENT ON COLUMN audit_log.retention_policy IS 'Determines how long the record should be retained';

-- Success message
SELECT 'Audit schema created successfully' as status;