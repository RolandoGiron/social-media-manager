# Phase 5: Campaign Blast - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

The admin can send a WhatsApp broadcast to a patient segment safely. This covers: segment + template selection, recipient preview, mandatory confirmation gate, rate-limited delivery via n8n, real-time progress monitoring, and cancellation of in-progress broadcasts.

Phase 4 chatbot workflows and Phase 6 social publishing are NOT in scope. This phase only delivers outbound mass messaging to patient segments.

</domain>

<decisions>
## Implementation Decisions

### UI Location
- **D-01:** New sidebar page `7_Campañas.py` — dedicated broadcast workflow. Admin selects segment, selects template, sees rendered message preview + recipient count, confirms, then monitors progress in the same page.
- **D-02:** Navigation order in `app.py`: 7_Campañas is added after 6_Knowledge_Base. No changes to existing page order.

### Campaign Launch Flow (Streamlit)
- **D-03:** Step 1 — Admin picks segment (tag multiselect) and template (dropdown). The UI immediately shows recipient count ("X pacientes") and a rendered message preview with sample values substituted.
- **D-04:** Step 2 — Confirmation gate (WA-03): "Estás a punto de enviar a X pacientes. ¿Confirmar?" with patient count prominently displayed. Two buttons: "Confirmar y enviar" and "Cancelar". No message is sent before this confirmation.
- **D-05:** On confirm: Streamlit inserts a row into `campaign_log` (status='pending', total_recipients=N), inserts N rows into `campaign_recipients` (status='pending'), then fires an n8n webhook with the `campaign_id`. Page switches to progress view.
- **D-06:** Campaign name is auto-generated: "{tag_name} · {fecha}" (e.g., "acné · 12 abr 2026"). No manual naming required.

### n8n Broadcast Workflow
- **D-07:** New n8n workflow `campaign-blast.json`. Triggered by Streamlit webhook POST with `campaign_id`. Queries `campaign_recipients WHERE campaign_id = ? AND status = 'pending'`, iterates each recipient with a loop node.
- **D-08:** Rate limiting: 3-8 second delay with random jitter between each send (n8n Wait node or Code node with `await new Promise(r => setTimeout(r, delay))`). Prevents Evolution API banning.
- **D-09:** Before each send, n8n checks `campaign_log.status`. If status is `'cancelled'`, the loop exits immediately — no further messages are sent (implements WA-04 cancellation).
- **D-10:** After each successful send: UPDATE `campaign_recipients SET status='sent', wa_message_id=?, sent_at=now()` and UPDATE `campaign_log SET sent_count = sent_count + 1`. On failure: UPDATE `campaign_recipients SET status='failed', error_message=?`, increment `failed_count`.
- **D-11:** On loop completion: UPDATE `campaign_log SET status='completed', completed_at=now()`.

### Progress Monitoring (Streamlit)
- **D-12:** After launch, the Campañas page switches to progress view (session state flag). Auto-refreshes every 5 seconds (consistent with inbox polling pattern from Phase 2/4) by polling `campaign_log` for `sent_count`, `failed_count`, `total_recipients`, `status`.
- **D-13:** Progress display: Streamlit progress bar (`st.progress`) showing sent_count/total_recipients, label "X / N enviados", and a "Cancelar campaña" button visible while status is `in_progress`.
- **D-14:** Cancel button: Streamlit sets `campaign_log.status = 'cancelled'`, `cancelled_at = now()`. n8n picks this up on next iteration check (D-09). Page shows "Campaña cancelada" and stops polling.
- **D-15:** Campaign history table below the active progress section: shows all past campaigns ordered by `created_at DESC` with columns: Nombre, Segmento, Enviados, Estado, Fecha. Allows the admin to see history without navigating away.

### Claude's Discretion
- Exact jitter implementation in n8n (random integer between 3000 and 8000 ms)
- Evolution API endpoint for sending messages (reuse pattern from Phase 4 chatbot sub-workflow `sub-send-wa-message.json`)
- Streamlit session state variable names for multi-step flow
- Error state visual treatment in the progress bar (failed_count shown in red)
- Estimated time remaining calculation (approximate: remaining * avg_delay)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Database Schema
- `postgres/init/001_schema.sql` — `campaign_log` table (id, campaign_name, template_id, segment_tags UUID[], total_recipients, sent_count, failed_count, status, cancelled_at, started_at, completed_at, created_at) and `campaign_recipients` table (id, campaign_id, patient_id, status, wa_message_id, sent_at, delivered_at, read_at, error_message). Both tables already exist — no migration needed.

### Requirements
- `.planning/REQUIREMENTS.md` §WA — WA-02 (broadcast with rate limiting), WA-03 (confirmation gate), WA-04 (cancellation)
- `.planning/ROADMAP.md` §Phase 5 — 3 success criteria define done

### Existing Admin UI (extend)
- `admin-ui/src/app.py` — `st.navigation()` entrypoint; add `7_Campañas.py` here
- `admin-ui/src/components/sidebar.py` — `render_sidebar()` must be called at top of new page
- `admin-ui/src/components/database.py` — DB connection pattern; follow for campaign queries
- `admin-ui/src/pages/3_Pacientes.py` — pattern for tag multiselect filter (reuse for segment selection)
- `admin-ui/src/pages/4_Plantillas.py` — pattern for template list and variable preview rendering

### Existing n8n Workflows (reference)
- `n8n/workflows/sub-send-wa-message.json` — Evolution API send-message sub-workflow; reuse or call from campaign-blast workflow
- `n8n/workflows/whatsapp-chatbot.json` — Reference for n8n webhook trigger pattern and PostgreSQL node usage

### Prior Phase Context
- `.planning/phases/03-crm-core/03-CONTEXT.md` — Tag/segment data model: `tags` table, `patient_tags` join table, tag assignment patterns
- `.planning/phases/04-ai-chatbot-appointment-booking/04-CONTEXT.md` — n8n sub-workflow pattern (D-12), Evolution API HTTP call patterns, n8n webhook trigger structure

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `admin-ui/src/components/database.py`: DB connection via `DATABASE_URL` — follow for campaign_log insert, update, and poll queries
- `admin-ui/src/components/sidebar.py`: `render_sidebar()` — import at top of 7_Campañas.py
- `admin-ui/src/components/templates.py`: `extract_variables()` and `render_preview()` — reuse directly for message preview in campaign flow
- `n8n/workflows/sub-send-wa-message.json`: Evolution API send-message call — campaign-blast workflow calls this or replicates the HTTP Request node pattern
- `postgres/init/001_schema.sql` §campaign_log + §campaign_recipients: both tables fully defined with proper indexes

### Established Patterns
- Streamlit pages: `admin-ui/src/pages/N_PageName.py` naming convention (next: `7_Campañas.py`)
- Multi-step Streamlit flow via `session_state` mode toggle (established in Pacientes: `pacientes_mode`, and Plantillas: `plantillas_mode`)
- Auto-refresh polling via `st_autorefresh` with fallback (established in Phase 4 Inbox page)
- n8n webhook trigger from Streamlit: HTTP POST to n8n webhook URL (pattern to establish in this phase)
- No ORM — direct psycopg2 queries following `database.py` pattern

### Integration Points
- Streamlit → PostgreSQL: INSERT into campaign_log + campaign_recipients on confirm; SELECT to poll progress; UPDATE to cancel
- Streamlit → n8n: POST to campaign-blast webhook with `{"campaign_id": "uuid"}` after DB insert
- n8n → PostgreSQL: SELECT pending recipients, UPDATE sent/failed status per recipient, UPDATE campaign_log counters and status
- n8n → Evolution API: send-message call per recipient (reuse sub-send-wa-message pattern)
- `patients` JOIN `patient_tags` JOIN `tags` WHERE `tag_id IN (selected_tags)` — established join pattern from Phase 3
- `message_templates.variables TEXT[]` + body — template rendering with `{{variable}}` substitution (established in Phase 3/4)

</code_context>

<specifics>
## Specific Ideas

- Confirmation gate text (Spanish): "Estás a punto de enviar a **N pacientes**. ¿Confirmar?" — matches REQUIREMENTS WA-03 exactly
- Progress label: "Enviando... X / N mensajes" with Streamlit `st.progress(sent/total)` bar
- Campaign auto-name format: "{tag_name} · {dd mmm yyyy}" (e.g., "acné · 12 abr 2026")
- Cancel button only visible while campaign status is `in_progress` — hidden for completed/cancelled/failed

</specifics>

<deferred>
## Deferred Ideas

- Per-recipient delivery status (delivered/read tracking via Evolution API webhooks) — DASH-02 requirement, Phase 7
- Scheduled future send (set a date/time for the blast) — not in Phase 5 success criteria; defer to v2
- Opt-in/opt-out exclusion filter — v2 requirement (PRIV-01); campaigns in v1 send to all patients in segment
- Campaign template preview with multiple sample recipients (rotating preview) — UX enhancement, not required for MVP

### Reviewed Todos
None — no pending todos matched Phase 5 scope.

</deferred>

---

*Phase: 05-campaign-blast*
*Context gathered: 2026-04-12*
