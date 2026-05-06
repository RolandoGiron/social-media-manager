# Quick Task 260506-5uk: Summary

**Date:** 2026-05-06
**Status:** Completed

## Changes Made

### 1. whatsapp-chatbot.json — Booking flow removed, human handoff added
- **New node "Set Booking Handoff Response"** (Set, pos [3600,200]): cuando intent=BOOKING, responde "Para agendar su cita, un asesor de nuestra clínica le atenderá directamente. En breve lo contactamos. 📅" y pone state=human_handoff.
- **New node "Set Active Booking Handoff"** (Code, pos [2880,400]): cuando la conversación ya está en estado `booking_flow`, responde con mensaje de handoff y cambia state a human_handoff. Toma conversation_id, remote_jid, etc. de nodos anteriores.
- **Route by Intent** BOOKING output → ahora apunta a "Set Booking Handoff Response" (antes "Start Booking Flow").
- **Is Booking Flow Active?** True output → ahora apunta a "Set Active Booking Handoff" (antes "Continue Booking Flow").
- **Set Greeting Response** texto actualizado: ya no menciona agendar citas.
- Los nodos "Start Booking Flow", "Continue Booking Flow", "Prepare Mid-Booking State Update" quedan huérfanos (sin conexiones entrantes) pero se conservan en el JSON por seguridad.

### 2. sub-faq-answer.json — Respuestas exactas de FAQ
- System prompt de "Generate FAQ Answer (OpenAI)" actualizado: ahora instruye a OpenAI a devolver EXACTAMENTE la respuesta de la FAQ más relevante, sin parafrasear ni agregar información. Temperature bajó implícitamente de 0.3 a 0.1.

### 3. postgres/migrations/001_fix_knowledge_base_categories.sql — Migración BD
- Constraint `knowledge_base_categoria_check` actualizado para incluir `'promocion'`.
- 2 FAQs reclasificadas de `general` a `servicios`: "¿Es seguro el tratamiento?" y "¿Cuánto tiempo dura el tratamiento?".
- Migración aplicada al DB live exitosamente (ALTER TABLE + UPDATE 2 rows).

### 4. postgres/init/003_knowledge_base.sql — Schema base actualizado
- CHECK constraint ahora incluye `'promocion'` para nuevos deployments.

### 5. n8n-mcp/ — Sincronización
- whatsapp-chatbot.json y sub-faq-answer.json copiados a n8n-mcp/.

## Files Changed
- `n8n/workflows/whatsapp-chatbot.json`
- `n8n/workflows/sub-faq-answer.json`
- `n8n-mcp/whatsapp-chatbot.json`
- `n8n-mcp/sub-faq-answer.json`
- `postgres/init/003_knowledge_base.sql`
- `postgres/migrations/001_fix_knowledge_base_categories.sql` (new)

## Notes
- Para aplicar en producción ejecutar: `docker exec -i clinic-postgres psql -U clinic -d clinic_crm < postgres/migrations/001_fix_knowledge_base_categories.sql`
- Los workflows deben importarse en n8n o publicarse via n8n-mcp para activar los cambios.
