-- Clinic CRM Database Schema
-- Executed automatically on first PostgreSQL container start
-- via /docker-entrypoint-initdb.d volume mount

-- === Extensions ===
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- === Tables ===

-- patients: core CRM entity
CREATE TABLE patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    phone_normalized TEXT NOT NULL,
    email TEXT,
    notes TEXT,
    consent_status BOOLEAN NOT NULL DEFAULT false,
    source TEXT DEFAULT 'csv_import',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_patients_phone_normalized UNIQUE (phone_normalized)
);

CREATE INDEX idx_patients_phone_normalized ON patients (phone_normalized);
CREATE INDEX idx_patients_name ON patients USING gin (
    (first_name || ' ' || last_name) gin_trgm_ops
);
CREATE INDEX idx_patients_created_at ON patients (created_at);

-- tags: segmentation labels for patients
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    color TEXT DEFAULT '#6366f1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- patient_tags: many-to-many junction
CREATE TABLE patient_tags (
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (patient_id, tag_id)
);

CREATE INDEX idx_patient_tags_tag_id ON patient_tags (tag_id);

-- conversations: chatbot state machine (per ARCHITECTURE.md Pattern 2)
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE SET NULL,
    wa_contact_id TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'new'
        CHECK (state IN ('new', 'awaiting_intent', 'faq_flow', 'booking_flow', 'human_handoff', 'closed')),
    context JSONB DEFAULT '{}',
    assigned_agent TEXT,
    last_message_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_conversations_wa_contact_active
    ON conversations (wa_contact_id) WHERE state != 'closed';
CREATE INDEX idx_conversations_state ON conversations (state);
CREATE INDEX idx_conversations_patient_id ON conversations (patient_id);

-- messages: conversation history for inbox
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    direction TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    sender TEXT NOT NULL CHECK (sender IN ('patient', 'bot', 'agent')),
    content TEXT NOT NULL,
    media_url TEXT,
    media_type TEXT,
    wa_message_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_messages_conversation_id ON messages (conversation_id);
CREATE INDEX idx_messages_created_at ON messages (created_at);
CREATE INDEX idx_messages_wa_message_id ON messages (wa_message_id);

-- appointments: calendar bookings
CREATE TABLE appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    google_event_id TEXT,
    appointment_type TEXT NOT NULL,
    scheduled_at TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER NOT NULL DEFAULT 30,
    status TEXT NOT NULL DEFAULT 'confirmed'
        CHECK (status IN ('confirmed', 'cancelled', 'completed', 'no_show')),
    reminder_24h_sent BOOLEAN NOT NULL DEFAULT false,
    reminder_1h_sent BOOLEAN NOT NULL DEFAULT false,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_appointments_patient_id ON appointments (patient_id);
CREATE INDEX idx_appointments_scheduled_at ON appointments (scheduled_at);
CREATE INDEX idx_appointments_status ON appointments (status);

-- message_templates: reusable WhatsApp message templates
CREATE TABLE message_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    body TEXT NOT NULL,
    variables TEXT[] DEFAULT '{}',
    category TEXT DEFAULT 'general',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- campaign_log: bulk campaign tracking
CREATE TABLE campaign_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_name TEXT NOT NULL,
    template_id UUID REFERENCES message_templates(id) ON DELETE SET NULL,
    segment_tags UUID[],
    total_recipients INTEGER NOT NULL DEFAULT 0,
    sent_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled', 'failed')),
    cancelled_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_campaign_log_status ON campaign_log (status);
CREATE INDEX idx_campaign_log_created_at ON campaign_log (created_at);

-- campaign_recipients: per-recipient delivery tracking
CREATE TABLE campaign_recipients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES campaign_log(id) ON DELETE CASCADE,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'sent', 'delivered', 'read', 'failed')),
    wa_message_id TEXT,
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    error_message TEXT
);

CREATE INDEX idx_campaign_recipients_campaign ON campaign_recipients (campaign_id);
CREATE INDEX idx_campaign_recipients_patient ON campaign_recipients (patient_id);
CREATE INDEX idx_campaign_recipients_status ON campaign_recipients (status);

-- workflow_errors: n8n error logging (per PITFALLS.md Pattern 8)
CREATE TABLE workflow_errors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_name TEXT NOT NULL,
    workflow_id TEXT,
    execution_id TEXT,
    node_name TEXT,
    error_message TEXT NOT NULL,
    error_details JSONB DEFAULT '{}',
    input_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_workflow_errors_workflow_name ON workflow_errors (workflow_name);
CREATE INDEX idx_workflow_errors_created_at ON workflow_errors (created_at);

-- social_posts: social media publishing (Phase 6 readiness)
CREATE TABLE social_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    caption TEXT NOT NULL,
    image_url TEXT,
    platforms TEXT[] NOT NULL DEFAULT '{}',
    scheduled_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'scheduled', 'publishing', 'published', 'failed')),
    platform_post_ids JSONB DEFAULT '{}',
    campaign_id UUID REFERENCES campaign_log(id) ON DELETE SET NULL,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_social_posts_status ON social_posts (status);
CREATE INDEX idx_social_posts_scheduled_at ON social_posts (scheduled_at);

-- === Trigger Function: auto-update updated_at ===

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_patients_updated_at BEFORE UPDATE ON patients FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_conversations_updated_at BEFORE UPDATE ON conversations FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_appointments_updated_at BEFORE UPDATE ON appointments FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_message_templates_updated_at BEFORE UPDATE ON message_templates FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_social_posts_updated_at BEFORE UPDATE ON social_posts FOR EACH ROW EXECUTE FUNCTION update_updated_at();
