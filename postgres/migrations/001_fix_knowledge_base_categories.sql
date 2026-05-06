-- Migration 001: Fix knowledge_base categories
-- 1. Add 'promocion' to the categoria CHECK constraint
-- 2. Reclassify general FAQs about treatments/safety/duration to 'servicios'
-- Run: docker exec -i clinic-postgres psql -U clinic -d clinic_crm < postgres/migrations/001_fix_knowledge_base_categories.sql

BEGIN;

-- Drop old constraint and recreate with 'promocion' included
ALTER TABLE knowledge_base
  DROP CONSTRAINT IF EXISTS knowledge_base_categoria_check;

ALTER TABLE knowledge_base
  ADD CONSTRAINT knowledge_base_categoria_check
  CHECK (categoria IN ('horarios', 'ubicacion', 'precios', 'servicios', 'general', 'promocion'));

-- Reclassify treatment/safety/duration FAQs from 'general' to 'servicios'
UPDATE knowledge_base
SET categoria = 'servicios'
WHERE pregunta IN (
  '¿Es seguro el tratamiento?',
  '¿Cuánto tiempo dura el tratamiento?'
)
AND categoria = 'general';

COMMIT;
