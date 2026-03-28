# Phase 2: WhatsApp Core - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Connect the clinic's WhatsApp number via Evolution API, display session status in the Streamlit admin UI, and automatically alert the admin when the session disconnects. Covers the full session lifecycle: initial QR scan, persistent status visibility, disconnect detection, and alert delivery.

Message routing and chatbot logic are NOT in scope — those are Phase 4. This phase only ensures the connection is up and the admin knows when it's not.

</domain>

<decisions>
## Implementation Decisions

### QR Scanning UX
- **D-01:** Embed Evolution API's built-in QR/manager page as an `st.components.v1.iframe` inside Streamlit's "Connect WhatsApp" page. Zero custom QR rendering code — Evolution handles QR rotation, expiry countdown, and connection confirmation feedback natively.
- **D-02:** The Connect WhatsApp page is accessible from the Streamlit sidebar navigation. It is only needed on first connect or after a session drop requiring manual reconnection.

### Session Status Display
- **D-03:** A colored dot + label lives in the Streamlit sidebar, visible on every page without layout changes. Green dot = "Conectado", red dot = "Desconectado".
- **D-04:** Streamlit polls Evolution API's `/instance/connectionState/{instance}` endpoint every 60 seconds to refresh the sidebar status. No websocket, no push — polling is sufficient for a single-admin tool.
- **D-05:** The sidebar also shows the clinic's WhatsApp number (from .env `CLINIC_WHATSAPP_NUMBER`) when connected, so admin can confirm which number is active.

### Disconnection Alert
- **D-06:** When disconnection is detected, n8n sends a WhatsApp message to the admin's personal number (`ADMIN_WHATSAPP_NUMBER` env var) via the same Evolution API instance using the clinic's number.
- **D-07:** Alert message includes: timestamp of detection, a direct link to the admin panel's Connect WhatsApp page (`https://admin.DOMAIN/WhatsApp`), and the message "La sesión de WhatsApp se desconectó. Escanea el QR para reconectar."
- **D-08:** Alert fires once per disconnection event — no repeated reminders. If admin re-scans and reconnects, subsequent disconnections will trigger a new alert.
- **D-09:** Edge case awareness: if the clinic's WhatsApp number itself is disconnected, the alert WhatsApp message will fail silently. This is an accepted limitation for v1 — no secondary fallback channel in this phase.

### n8n Workflow Structure
- **D-10:** Separate n8n workflows per event type. For this phase, two workflows:
  - `whatsapp-connection-update`: Receives `CONNECTION_UPDATE` webhook events from Evolution API. On `state: close` or `state: connecting`, triggers the alert flow. On `state: open`, logs reconnection.
  - `whatsapp-message-stub`: Receives `MESSAGES_UPSERT` events. Logs to DB only (no bot logic yet). This stub is required so Evolution API's webhook doesn't error on message events — chatbot logic is wired in Phase 4.
- **D-11:** Both workflows share the same webhook base path (`/webhook/whatsapp-inbound`) with event routing via the `event` field in the Evolution API payload. A Switch node at the top of a root workflow routes to the appropriate sub-workflow via Execute Workflow nodes, OR each webhook has its own URL — use separate URLs for simplicity in this phase.

### Claude's Discretion
- Exact polling interval tuning (60s default, can adjust if too noisy)
- Streamlit sidebar color codes and label wording
- n8n error handling and retry logic for the alert message send
- How to store/display last-connected timestamp

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Infrastructure (Phase 1 outputs)
- `docker-compose.yml` — Evolution API service config, internal network, env vars
- `.env.example` — All environment variable names; add `ADMIN_WHATSAPP_NUMBER` and `EVOLUTION_INSTANCE_NAME`
- `admin-ui/src/app.py` — Existing Streamlit scaffold to extend

### Requirements
- `.planning/REQUIREMENTS.md` §INFRA — INFRA-01, INFRA-02, INFRA-03 are the full scope of this phase
- `.planning/ROADMAP.md` §Phase 2 — Success criteria (4 items) define done

### Evolution API
- No external spec committed yet — downstream agents should check Evolution API v2 REST docs for `/instance/connectionState`, `/instance/connect`, and webhook payload schema (`CONNECTION_UPDATE`, `MESSAGES_UPSERT` event structures)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `admin-ui/src/app.py`: Streamlit scaffold with `st.set_page_config(layout="wide")` — extend with multipage structure (Streamlit pages/ directory) and sidebar component
- `docker-compose.yml` evolution-api service: `WEBHOOK_GLOBAL_URL` already points to n8n; `SERVER_URL` is set to `https://${EVOLUTION_SUBDOMAIN}.${DOMAIN}` — iframe can use this URL

### Established Patterns
- All inter-service communication is on `clinic-net` Docker network using service names as hostnames
- Streamlit has `N8N_WEBHOOK_BASE_URL: http://n8n:5678` env var available for triggering n8n flows
- Streamlit has `DATABASE_URL` env var — can store/read WhatsApp session state in PostgreSQL `system_events` or a dedicated `whatsapp_sessions` table
- Evolution API instance name will be set via `EVOLUTION_INSTANCE_NAME` env var (to be added to .env.example)

### Integration Points
- Streamlit → Evolution API: HTTP call to `http://evolution-api:8080/instance/connectionState/{instance}` for status polling
- Streamlit → Evolution API: iframe pointing to `https://${EVOLUTION_SUBDOMAIN}.${DOMAIN}/manager` for QR page
- Evolution API → n8n: webhook events delivered to `http://n8n:5678/webhook/whatsapp-inbound`
- n8n → Evolution API: HTTP POST to send alert WhatsApp message to admin

</code_context>

<specifics>
## Specific Ideas

- The QR page should be a dedicated Streamlit page (pages/WhatsApp.py) linked from the sidebar, not a modal or overlay
- Alert message text (Spanish): "La sesión de WhatsApp se desconectó. Escanea el QR para reconectar: https://admin.DOMAIN/WhatsApp"
- Sidebar status component should be defined in a shared `components/sidebar.py` helper so every page imports it once

</specifics>

<deferred>
## Deferred Ideas

- Secondary alert channel (email fallback when WhatsApp itself is down) — valid concern, defer to v2 ops hardening
- Automatic reconnect retry without admin intervention — out of scope for Phase 2; admin reconnects manually
- Multiple WhatsApp instances / multi-clinic — v2 scope (single-tenant v1 constraint)

</deferred>

---

*Phase: 02-whatsapp-core*
*Context gathered: 2026-03-28*
