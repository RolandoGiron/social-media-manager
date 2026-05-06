-- Knowledge Base table for AI chatbot FAQ responses
-- Phase 4: AI Chatbot & Appointment Booking
-- Executed after 001_schema.sql (update_updated_at function must exist)

CREATE TABLE knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pregunta TEXT NOT NULL,
    respuesta TEXT NOT NULL,
    categoria TEXT NOT NULL DEFAULT 'general'
        CHECK (categoria IN ('horarios', 'ubicacion', 'precios', 'servicios', 'general', 'promocion')),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_knowledge_base_updated_at
    BEFORE UPDATE ON knowledge_base
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE INDEX idx_knowledge_base_categoria ON knowledge_base (categoria);
CREATE INDEX idx_knowledge_base_is_active ON knowledge_base (is_active);
