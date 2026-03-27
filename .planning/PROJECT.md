# AI Social Media Manager & CRM

## What This Is

Plataforma de automatización de marketing y atención al cliente para negocios físicos, comenzando con clínicas dermatológicas. Centraliza la gestión de WhatsApp (campañas masivas + chatbot IA), publicación en redes sociales, agendamiento de citas vía Google Calendar, y un CRM ligero para segmentar y activar bases de datos de pacientes. Construida por un solo developer sobre VPS Hostinger con n8n como orquestador central.

## Core Value

El dueño de la clínica puede lanzar una promoción dirigida — que llega a WhatsApp de los pacientes relevantes Y se publica en redes sociales — sin tocar ningún sistema manualmente.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Importación masiva de pacientes desde CSV/Excel
- [ ] Segmentación de pacientes por condición/interés
- [ ] Envío masivo de mensajes WhatsApp a segmentos seleccionados
- [ ] Chatbot en WhatsApp con respuestas automáticas (FAQ de la clínica)
- [ ] Escalada de conversación a humano cuando el bot no tiene respuesta
- [ ] Consulta de disponibilidad y agendamiento en Google Calendar vía chatbot
- [ ] Generación de copy e imágenes para promociones (IA)
- [ ] Publicación automática/programada en Facebook, Instagram, X y TikTok
- [ ] Dashboard con métricas: mensajes respondidos, citas agendadas, engagement
- [ ] Interfaz de administración web para gestión operativa

### Out of Scope

- Multi-tenant / SaaS multi-clínica — arquitectura single-tenant primero, expansión en v2
- App móvil — web-first para el administrador
- Historial clínico completo / expediente médico — solo datos de contacto y segmentación
- Pagos / facturación — fuera del MVP
- Integración con sistemas de gestión médica existentes — no requerido para v1

## Context

- **Vertical objetivo:** Clínicas dermatológicas; generalizable a otros negocios físicos en v2
- **Infraestructura:** VPS Hostinger con acceso root; todo self-hosted
- **Orquestación:** n8n self-hosted como motor de flujos y automatizaciones
- **Base de datos:** PostgreSQL para persistencia de pacientes, citas y estados de conversación
- **WhatsApp:** Evolution API (open-source, conecta número existente, sin aprobación de Meta requerida)
- **IA:** Flexible — Ollama local preferido para privacidad, pero GPT/Claude aceptables si la calidad del chatbot lo justifica
- **UI Admin:** Streamlit o interfaz low-code integrada con n8n
- **Arquitectura:** Single-tenant en v1, diseñada para evolucionar a multi-tenant en v2
- **Equipo:** Un solo developer
- **Criterios de éxito MVP:**
  1. 100 pacientes migrados de registros físicos al sistema
  2. Bot responde exitosamente el 80% de consultas frecuentes (ubicación, horarios, precios)
  3. Al menos una cita agendada via Google Calendar sin intervención humana
  4. Una promoción publicada en IG se replica automáticamente como mensaje WhatsApp a la base

## Constraints

- **Infraestructura:** VPS Hostinger (recursos limitados) — arquitectura debe ser eficiente; evitar servicios que requieran múltiples VPS
- **WhatsApp:** Evolution API es no-oficial — riesgo de cambios en la API de WhatsApp Web; aceptado conscientemente para arrancar rápido
- **Concurrencia:** Soporte para +100 usuarios concurrentes en el bot — procesamiento asíncrono obligatorio
- **Privacidad:** Datos médicos encriptados en reposo; logs de IA anonimizados aunque normativa local no lo exija
- **Disponibilidad:** 24/7 — el chatbot atiende fuera de horario de la clínica
- **Solo developer:** Scope de v1 debe ser ejecutable por una persona; priorizamos flujos mínimos viables sobre features completas

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Evolution API sobre Meta Business API o Twilio | Arranque rápido sin fricción de aprobación; costo cero por mensaje | — Pending |
| n8n como orquestador central | Low-code para flujos, reduce código custom, fácil integración con APIs externas | — Pending |
| IA flexible (local u cloud) | Ollama para privacidad si el hardware del VPS aguanta; cloud si la calidad conversacional no es suficiente | — Pending |
| Single-tenant v1 con diseño extensible | Reduce complejidad del MVP; el dueño es una sola clínica inicialmente | — Pending |

---

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-27 after initialization*
