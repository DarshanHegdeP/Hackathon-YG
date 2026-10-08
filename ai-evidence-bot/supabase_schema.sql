-- Run this inside Supabase SQL Editor:
-- Go to: Supabase Dashboard -> SQL Editor -> New query -> Paste and click Run

-- 1. Reviews Table
CREATE TABLE IF NOT EXISTS reviews (
    review_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    business_units TEXT[] DEFAULT '{}',
    description TEXT,
    status TEXT NOT NULL DEFAULT 'DRAFT',
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Controls Catalog Table
CREATE TABLE IF NOT EXISTS controls (
    control_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    domain TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    frequency TEXT NOT NULL,
    required_evidence_types TEXT[] DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Review Controls Table
CREATE TABLE IF NOT EXISTS review_controls (
    review_control_id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL REFERENCES reviews(review_id) ON DELETE CASCADE,
    control_id TEXT NOT NULL REFERENCES controls(control_id),
    owner_id TEXT,
    status TEXT NOT NULL DEFAULT 'NOT_STARTED',
    risk_level TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Users Directory Table
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    role TEXT NOT NULL,
    business_unit TEXT NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Audit Events (Append-only)
CREATE TABLE IF NOT EXISTS audit_events (
    audit_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    actor_type TEXT DEFAULT 'USER',
    actor_id TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Pre-seed Controls
INSERT INTO controls (control_id, name, description, domain, risk_level, frequency, required_evidence_types, status)
VALUES
  ('AML-001', 'Transaction Monitoring Review', 'Review of daily transaction alerts.', 'AML', 'HIGH', 'DAILY', ARRAY['ALERT_REPORT', 'INVESTIGATION_LOG'], 'ACTIVE'),
  ('AML-002', 'High Risk Customer Review', 'High-risk customers must undergo enhanced due diligence annually.', 'AML', 'HIGH', 'ANNUAL', ARRAY['CUSTOMER_POPULATION', 'REVIEW_REPORT'], 'ACTIVE'),
  ('AML-003', 'Sanctions Alert Investigation', 'Review sanctions alerts.', 'AML', 'CRITICAL', 'DAILY', ARRAY['SANCTIONS_LOG'], 'ACTIVE'),
  ('AML-004', 'Suspicious Activity Escalation', 'SAR escalations.', 'AML', 'HIGH', 'AD_HOC', ARRAY['SAR_FORM'], 'ACTIVE'),
  ('KYC-001', 'Customer Due Diligence', 'CDD for new customers.', 'KYC', 'MEDIUM', 'AD_HOC', ARRAY['ID_DOCUMENT', 'UTILITY_BILL'], 'ACTIVE'),
  ('KYC-002', 'Periodic KYC Refresh', 'Refresh KYC every 3 years.', 'KYC', 'MEDIUM', 'TRIENNIAL', ARRAY['REFRESH_REPORT'], 'ACTIVE'),
  ('ACCESS-001', 'Privileged Access Review', 'Review PAM.', 'IT_SECURITY', 'HIGH', 'QUARTERLY', ARRAY['ACCESS_LIST'], 'ACTIVE'),
  ('ACCESS-002', 'User Access Termination', 'Ensure access is revoked.', 'IT_SECURITY', 'MEDIUM', 'DAILY', ARRAY['TICKET_LOG'], 'ACTIVE'),
  ('VENDOR-001', 'Critical Vendor Review', 'Review vendor compliance.', 'VENDOR_MGMT', 'HIGH', 'ANNUAL', ARRAY['SOC2_REPORT'], 'ACTIVE'),
  ('BCP-001', 'Business Continuity Testing', 'Test BCP.', 'RESILIENCE', 'CRITICAL', 'ANNUAL', ARRAY['TEST_RESULTS'], 'ACTIVE')
ON CONFLICT (control_id) DO NOTHING;

-- Pre-seed Users
INSERT INTO users (user_id, name, email, role, business_unit, active)
VALUES
  ('USER-LOD2-001', 'LOD2 Reviewer', 'reviewer1@bank.local', 'LOD2_REVIEWER', 'COMPLIANCE', true),
  ('USER-LOD2-002', 'LOD2 Manager', 'manager1@bank.local', 'LOD2_MANAGER', 'COMPLIANCE', true),
  ('USER-AML-001', 'AML Operations', 'amlops@bank.local', 'BUSINESS_OWNER', 'AML', true),
  ('USER-AML-002', 'KYC Operations', 'kycops@bank.local', 'BUSINESS_OWNER', 'KYC', true),
  ('USER-IT-001', 'IT Security', 'itsec@bank.local', 'BUSINESS_OWNER', 'IT', true)
ON CONFLICT (user_id) DO NOTHING;
