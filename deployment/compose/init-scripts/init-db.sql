-- Initialize Local AI Agent Database
-- This script sets up the initial database schema and data

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS agents;
CREATE SCHEMA IF NOT EXISTS workflows;
CREATE SCHEMA IF NOT EXISTS mcp;
CREATE SCHEMA IF NOT EXISTS monitoring;

-- Auth Schema Tables
CREATE TABLE IF NOT EXISTS auth.tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    max_users INTEGER,
    max_agents INTEGER,
    allowed_features JSONB DEFAULT '[]',
    custom_settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS auth.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    tenant_id UUID REFERENCES auth.tenants(id) ON DELETE SET NULL,
    roles JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS auth.roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    permissions JSONB DEFAULT '{}',
    is_system_role BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Agents Schema Tables
CREATE TABLE IF NOT EXISTS agents.agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'idle',
    capabilities JSONB DEFAULT '[]',
    config JSONB DEFAULT '{}',
    tenant_id UUID REFERENCES auth.tenants(id) ON DELETE CASCADE,
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agents.executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents.agents(id) ON DELETE CASCADE,
    command VARCHAR(255) NOT NULL,
    parameters JSONB DEFAULT '{}',
    context JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'pending',
    result JSONB,
    error TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    execution_time INTERVAL,
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL
);

-- Workflows Schema Tables
CREATE TABLE IF NOT EXISTS workflows.workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    steps JSONB DEFAULT '[]',
    config JSONB DEFAULT '{}',
    tenant_id UUID REFERENCES auth.tenants(id) ON DELETE CASCADE,
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workflows.workflow_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID REFERENCES workflows.workflows(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    step_name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',
    input_data JSONB,
    output_data JSONB,
    error TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    execution_time INTERVAL
);

-- MCP Schema Tables
CREATE TABLE IF NOT EXISTS mcp.servers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    url VARCHAR(500) NOT NULL,
    status VARCHAR(50) DEFAULT 'inactive',
    capabilities JSONB DEFAULT '[]',
    config JSONB DEFAULT '{}',
    tenant_id UUID REFERENCES auth.tenants(id) ON DELETE CASCADE,
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Monitoring Schema Tables
CREATE TABLE IF NOT EXISTS monitoring.metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(255) NOT NULL,
    metric_value DECIMAL,
    labels JSONB DEFAULT '{}',
    tenant_id UUID REFERENCES auth.tenants(id) ON DELETE CASCADE,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS monitoring.audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    tenant_id UUID REFERENCES auth.tenants(id) ON DELETE CASCADE,
    action VARCHAR(255) NOT NULL,
    resource_type VARCHAR(100),
    resource_id UUID,
    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON auth.users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON auth.users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON auth.users(email);

CREATE INDEX IF NOT EXISTS idx_agents_tenant_id ON agents.agents(tenant_id);
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents.agents(status);
CREATE INDEX IF NOT EXISTS idx_agents_created_by ON agents.agents(created_by);

CREATE INDEX IF NOT EXISTS idx_executions_agent_id ON agents.executions(agent_id);
CREATE INDEX IF NOT EXISTS idx_executions_status ON agents.executions(status);
CREATE INDEX IF NOT EXISTS idx_executions_started_at ON agents.executions(started_at);

CREATE INDEX IF NOT EXISTS idx_workflows_tenant_id ON workflows.workflows(tenant_id);
CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows.workflows(status);
CREATE INDEX IF NOT EXISTS idx_workflows_created_by ON workflows.workflows(created_by);

CREATE INDEX IF NOT EXISTS idx_workflow_executions_workflow_id ON workflows.workflow_executions(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_status ON workflows.workflow_executions(status);

CREATE INDEX IF NOT EXISTS idx_mcp_servers_tenant_id ON mcp.servers(tenant_id);
CREATE INDEX IF NOT EXISTS idx_mcp_servers_status ON mcp.servers(status);

CREATE INDEX IF NOT EXISTS idx_metrics_tenant_id ON monitoring.metrics(tenant_id);
CREATE INDEX IF NOT EXISTS idx_metrics_recorded_at ON monitoring.metrics(recorded_at);
CREATE INDEX IF NOT EXISTS idx_metrics_name_recorded ON monitoring.metrics(metric_name, recorded_at);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON monitoring.audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_id ON monitoring.audit_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON monitoring.audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON monitoring.audit_logs(action);

-- Create update triggers for updated_at columns
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON auth.tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON auth.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_roles_updated_at BEFORE UPDATE ON auth.roles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON agents.agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workflows_updated_at BEFORE UPDATE ON workflows.workflows
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_mcp_servers_updated_at BEFORE UPDATE ON mcp.servers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default data
INSERT INTO auth.roles (name, description, permissions, is_system_role) VALUES
('superadmin', 'Full system access across all tenants', '{"system": ["admin"], "tenant": ["admin"], "user": ["admin"], "agent": ["admin"], "workflow": ["admin"], "mcp_server": ["admin"]}', true),
('tenant_admin', 'Full access within tenant scope', '{"user": ["admin"], "agent": ["admin"], "workflow": ["admin"], "mcp_server": ["admin"]}', true),
('agent_operator', 'Can operate and configure agents', '{"agent": ["read", "write", "execute"], "workflow": ["read", "execute"], "mcp_server": ["read"]}', true),
('workflow_designer', 'Can design and manage workflows', '{"workflow": ["read", "write", "execute"], "agent": ["read"], "mcp_server": ["read"]}', true),
('readonly_user', 'Read-only access to resources', '{"agent": ["read"], "workflow": ["read"], "mcp_server": ["read"]}', true)
ON CONFLICT (name) DO NOTHING;

-- Create default tenant
INSERT INTO auth.tenants (id, name, domain, max_users, max_agents, allowed_features) VALUES
('00000000-0000-0000-0000-000000000001', 'Default Tenant', 'localhost', 1000, 100, '["authentication", "graphql", "websockets", "monitoring"]')
ON CONFLICT (id) DO NOTHING;

-- Grant permissions
GRANT USAGE ON SCHEMA auth TO PUBLIC;
GRANT USAGE ON SCHEMA agents TO PUBLIC;
GRANT USAGE ON SCHEMA workflows TO PUBLIC;
GRANT USAGE ON SCHEMA mcp TO PUBLIC;
GRANT USAGE ON SCHEMA monitoring TO PUBLIC;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA auth TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA agents TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA workflows TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA mcp TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA monitoring TO PUBLIC;

-- Create database info
CREATE OR REPLACE VIEW monitoring.database_info AS
SELECT 
    'Local AI Agent Database' as database_name,
    version() as postgres_version,
    current_database() as current_db,
    current_timestamp as initialized_at;