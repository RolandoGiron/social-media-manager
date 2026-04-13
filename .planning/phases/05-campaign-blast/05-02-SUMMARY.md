---
phase: 05-campaign-blast
plan: 02
subsystem: ui
tags: [streamlit, campaign, broadcast, whatsapp, postgresql]

# Dependency graph
requires:
  - phase: 05-01
    provides: insert_campaign, insert_campaign_recipients, fetch_campaign_status, cancel_campaign, fetch_patients_by_tags, fetch_campaign_history in components/database.py
  - phase: 03-crm-core
    provides: fetch_tags_with_counts, fetch_templates, render_preview, render_sidebar, tag multiselect pattern
  - phase: 04-ai-chatbot-appointment-booking
    provides: st_autorefresh ImportError fallback pattern (5_Inbox.py)
provides:
  - Streamlit 7_Campañas.py page with setup/confirmation/progress/history views
  - Navigation entry in app.py under new "Campañas" section between Chatbot and Conexion
  - WA-03 confirmation gate enforced before any DB write
  - WA-04 cancel_campaign() wired to Cancelar campaña button
affects:
  - 05-03 (n8n campaign-blast.json — reads campaign_id from webhook triggered here)
  - Phase 6 social publishing (navigation pattern extended)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Multi-step Streamlit flow via campanas_mode session_state toggle (setup -> progress)"
    - "st_autorefresh with ImportError fallback for auto-polling every 5s"
    - "Locked insert order: insert_campaign -> insert_campaign_recipients -> _trigger_n8n_webhook"
    - "N8N_WEBHOOK_BASE_URL env var with http://n8n:5678 default for internal Docker network"

key-files:
  created:
    - admin-ui/src/pages/7_Campañas.py
  modified:
    - admin-ui/src/app.py

key-decisions:
  - "Campaign auto-name format: {tag_name} · {dd mmm yyyy} (e.g. acne · 13 abr 2026) — no manual naming required per D-06"
  - "Confirmation gate enforced via can_confirm guard (no DB write path exists without it) — implements WA-03 and T-05-04"
  - "History section always rendered below active view so admin sees past campaigns without navigating away — per D-15"
  - "Zero-division guard on progress_val for campaigns with total_recipients = 0 — RESEARCH Pitfall 4"

patterns-established:
  - "campanas_mode session_state toggle: follows pacientes_mode and plantillas_mode convention"
  - "st_autorefresh(interval=5000) for campaign progress polling — consistent with inbox 10s polling"

requirements-completed: [WA-02, WA-03, WA-04]

# Metrics
duration: 2min
completed: 2026-04-13
---

# Phase 5 Plan 02: Campañas Streamlit UI Summary

**Broadcast launch page with tag-segment selection, mandatory confirmation gate, real-time progress monitoring, and campaign history — wired into app.py navigation under new Campañas section**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-13T19:44:05Z
- **Completed:** 2026-04-13T19:46:18Z
- **Tasks:** 2 completed (Task 3 is pending human verification checkpoint)
- **Files modified:** 2

## Accomplishments
- Created `admin-ui/src/pages/7_Campañas.py` (284 lines) implementing all D-01..D-06 and D-12..D-15 decisions
- Setup view: tag multiselect + template dropdown + live recipient count + rendered message preview
- Confirmation gate with exact copy per UI-SPEC: "Estás a punto de enviar a **N pacientes**. ¿Confirmar?" — button disabled unless segment + template + count > 0
- On confirm: insert_campaign → insert_campaign_recipients → _trigger_n8n_webhook (locked order per RESEARCH Pitfall 2)
- Progress view: st.progress bar, "Enviando... X / N mensajes" label, Cancelar campaña button while in_progress, auto-refresh every 5s
- History table always visible below active view with Nombre/Segmento/Enviados/Fallidos/Estado/Fecha columns
- Wired navigation in app.py: new "Campañas" section between "Chatbot" and "Conexion" using :material/send: icon

## Task Commits

Each task was committed atomically:

1. **Task 1: Create 7_Campañas.py page** - `bf9fcc8` (feat)
2. **Task 2: Wire into app.py navigation** - `ba426f7` (feat)
3. **Task 3: Visual + functional verification** - PENDING HUMAN CHECKPOINT

## Files Created/Modified
- `admin-ui/src/pages/7_Campañas.py` - New broadcast launch page (284 lines, WA-02/03/04)
- `admin-ui/src/app.py` - Added campanhas page entry and "Campañas" nav section

## Decisions Made
- Campaign auto-name format uses {tag_name} · {dd mmm yyyy} (D-06) with Spanish month abbreviations
- Confirmation gate `can_confirm` guard ensures no DB write path exists without it (implements WA-03 + T-05-04)
- History section rendered after both setup and progress views (D-15)
- Zero-division guard: `progress_val = (sent_count / total_recipients) if total_recipients > 0 else 0.0`
- Error handling shows generic Spanish copy; raw exception detail in st.caption (T-05-07 InfoDisclosure mitigation)

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None — all Plan-01 DB functions were available in components/database.py, all patterns from existing pages were consistent with the plan spec.

## User Setup Required

None - no external service configuration required. N8N_WEBHOOK_BASE_URL defaults to `http://n8n:5678` (internal Docker network). The webhook endpoint `/webhook/campaign-blast` is implemented by Plan 03.

## Next Phase Readiness

- Task 3 (human verification checkpoint) is pending — operator must visit http://localhost:8501 and verify the Campañas page renders correctly
- Plan 03 (campaign-blast.json n8n workflow) must be deployed before the "Confirmar y enviar" button can complete a full end-to-end flow
- All UI surface is built and wired; n8n is the only missing piece for Phase 5 to be fully functional

---
*Phase: 05-campaign-blast*
*Completed: 2026-04-13*
