# Phase 2: WhatsApp Core - Research

**Researched:** 2026-03-28
**Domain:** Evolution API v2 WhatsApp session management + Streamlit multipage UI + n8n webhook workflows
**Confidence:** MEDIUM

## Summary

This phase connects the clinic's WhatsApp number via Evolution API, displays session status in Streamlit, and alerts the admin on disconnection via an n8n workflow. The technical surface is narrow: one REST API (Evolution API), one UI framework (Streamlit multipage), and two n8n workflows (connection monitor + message stub).

The primary risk is the QR code scanning UX. The user decided to embed Evolution API's manager page via `st.components.v1.iframe`. However, research reveals the Manager UI is a **separate Docker container** (`evolution_frontend` on port 3000), NOT bundled in the `atendai/evolution-api:v2.2.3` image. Two viable paths exist: (1) add the manager container to docker-compose and iframe it, or (2) call the `/instance/connect/{instance}` REST endpoint directly from Streamlit to get a base64 QR code and render it natively with `st.image()`. Option 2 is simpler, avoids a new container, and avoids cross-origin iframe issues.

The Evolution API REST endpoints for this phase are well-documented: `/instance/create`, `/instance/connect/{instance}` (returns base64 QR), `/instance/connectionState/{instance}`, and `/message/sendText/{instance}`. Webhook events `CONNECTION_UPDATE` and `MESSAGES_UPSERT` route to separate n8n webhook URLs when `WEBHOOK_GLOBAL_WEBHOOK_BY_EVENTS=true` (already configured in docker-compose).

**Primary recommendation:** Use the Evolution API REST endpoints directly from Streamlit for QR display and status polling. Use separate n8n webhook URLs per event type. Keep the `atendai/evolution-api:v2.2.3` image pinned per Phase 1 decisions.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Embed Evolution API's built-in QR/manager page as an `st.components.v1.iframe` inside Streamlit's "Connect WhatsApp" page. Zero custom QR rendering code.
- **D-02:** The Connect WhatsApp page is accessible from the Streamlit sidebar navigation. Only needed on first connect or after session drop.
- **D-03:** Colored dot + label in Streamlit sidebar on every page. Green = "Conectado", Red = "Desconectado".
- **D-04:** Streamlit polls Evolution API `/instance/connectionState/{instance}` every 60 seconds. No websocket.
- **D-05:** Sidebar shows clinic WhatsApp number (from .env `CLINIC_WHATSAPP_NUMBER`) when connected.
- **D-06:** On disconnection, n8n sends WhatsApp message to admin's personal number (`ADMIN_WHATSAPP_NUMBER`).
- **D-07:** Alert includes timestamp, link to admin panel, reconnection instructions in Spanish.
- **D-08:** Alert fires once per disconnection event.
- **D-09:** If clinic number is disconnected, alert WhatsApp fails silently. Accepted limitation.
- **D-10:** Two n8n workflows: `whatsapp-connection-update` and `whatsapp-message-stub`.
- **D-11:** Separate webhook URLs per event for simplicity.

### Claude's Discretion
- Exact polling interval tuning (60s default)
- Streamlit sidebar color codes and label wording
- n8n error handling and retry logic for alert send
- How to store/display last-connected timestamp

### Deferred Ideas (OUT OF SCOPE)
- Secondary alert channel (email fallback)
- Automatic reconnect retry without admin intervention
- Multiple WhatsApp instances / multi-clinic
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | Admin can connect/reconnect WhatsApp session scanning QR from UI | Evolution API `/instance/create` + `/instance/connect/{instance}` endpoints return base64 QR; Streamlit iframe or `st.image()` renders it |
| INFRA-02 | System shows WhatsApp session status (connected/disconnected) visible at all times | Evolution API `/instance/connectionState/{instance}` returns `state: "open"/"close"/"connecting"`; Streamlit sidebar polling pattern |
| INFRA-03 | System detects disconnection and sends alert to admin | Evolution API `CONNECTION_UPDATE` webhook + n8n workflow + `/message/sendText/{instance}` to alert admin |
</phase_requirements>

## Standard Stack

### Core
| Library/Service | Version | Purpose | Why Standard |
|-----------------|---------|---------|--------------|
| Evolution API | v2.2.3 (pinned in docker-compose) | WhatsApp session management, messaging | Already deployed in Phase 1; REST API for QR, connection state, send message |
| Streamlit | >=1.35 (in requirements.txt) | Admin UI with multipage navigation | Already scaffolded in Phase 1; `st.navigation` for multipage, `st.sidebar` for status |
| n8n | latest (in docker-compose) | Webhook receiver, alert workflow orchestrator | Already deployed; native Webhook node + HTTP Request node for Evolution API calls |
| PostgreSQL | 16-alpine (in docker-compose) | Event logging (workflow_errors table exists) | Already deployed; schema includes `workflow_errors` table |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| requests | bundled with Python | HTTP calls from Streamlit to Evolution API | Polling connectionState, creating instances, fetching QR |
| streamlit.components.v1 | bundled with Streamlit | iframe embedding | If using manager iframe approach (D-01) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| iframe for QR (D-01) | Direct REST API call + `st.image()` for QR | Simpler, no extra container, but contradicts D-01 -- see Pitfall 1 below |
| 60s polling (D-04) | `st_autorefresh` component | Adds dependency but enables cleaner auto-refresh without `time.sleep` hacks |

**New env vars needed (add to .env.example):**
```bash
EVOLUTION_INSTANCE_NAME=clinic-main
ADMIN_WHATSAPP_NUMBER=+521234567890
CLINIC_WHATSAPP_NUMBER=+529876543210
EVOLUTION_API_URL=http://evolution-api:8080
```

## Architecture Patterns

### Recommended Project Structure
```
admin-ui/src/
  app.py                    # Entrypoint: st.navigation + sidebar status component
  pages/
    1_Dashboard.py          # Home/placeholder (existing info message)
    2_WhatsApp.py           # QR scanning page (INFRA-01)
  components/
    sidebar.py              # Shared sidebar: status dot + phone number display
    evolution_api.py         # HTTP client wrapper for Evolution API calls
```

### Pattern 1: Streamlit Multipage with st.navigation
**What:** Use `st.Page` + `st.navigation` in `app.py` as the router. Shared elements (sidebar status) go in `app.py` before `pg.run()`.
**When to use:** Always -- this is the current Streamlit recommended approach (replaces `pages/` directory auto-detection).
**Example:**
```python
# app.py
import streamlit as st
from components.sidebar import render_sidebar

st.set_page_config(page_title="Clinica CRM", page_icon="", layout="wide")

# Shared sidebar -- appears on every page
render_sidebar()

# Page routing
dashboard = st.Page("pages/1_Dashboard.py", title="Dashboard", icon=":material/dashboard:")
whatsapp = st.Page("pages/2_WhatsApp.py", title="WhatsApp", icon=":material/chat:")

pg = st.navigation({"Principal": [dashboard], "Conexion": [whatsapp]})
pg.run()
```
Source: https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation

### Pattern 2: Sidebar Status Polling
**What:** Call Evolution API connectionState on every page load (via shared sidebar component), cache result in `st.session_state`, auto-refresh with `st_autorefresh` or manual `time.sleep` + `st.rerun`.
**When to use:** INFRA-02 requirement.
**Example:**
```python
# components/sidebar.py
import streamlit as st
import requests
import os
import time

def render_sidebar():
    instance = os.environ.get("EVOLUTION_INSTANCE_NAME", "clinic-main")
    api_url = os.environ.get("EVOLUTION_API_URL", "http://evolution-api:8080")
    api_key = os.environ.get("EVOLUTION_API_KEY", "")

    # Poll every 60s using session_state timestamp
    now = time.time()
    last_check = st.session_state.get("wa_last_check", 0)

    if now - last_check > 60:
        try:
            resp = requests.get(
                f"{api_url}/instance/connectionState/{instance}",
                headers={"apikey": api_key},
                timeout=5
            )
            data = resp.json()
            st.session_state["wa_state"] = data.get("instance", {}).get("state", "close")
            st.session_state["wa_last_check"] = now
        except Exception:
            st.session_state["wa_state"] = "unknown"

    state = st.session_state.get("wa_state", "unknown")

    with st.sidebar:
        if state == "open":
            st.markdown(":green_circle: **Conectado**")
            clinic_number = os.environ.get("CLINIC_WHATSAPP_NUMBER", "")
            if clinic_number:
                st.caption(f"Numero: {clinic_number}")
        elif state == "close":
            st.markdown(":red_circle: **Desconectado**")
        else:
            st.markdown(":orange_circle: **Conectando...**")

        st.session_state.setdefault("wa_last_connected", None)
        if st.session_state.get("wa_last_connected"):
            st.caption(f"Ultima conexion: {st.session_state['wa_last_connected']}")
```

### Pattern 3: n8n Webhook with Event Routing
**What:** Evolution API sends webhooks with `WEBHOOK_GLOBAL_WEBHOOK_BY_EVENTS=true`, which appends the event name as a hyphenated suffix to the base URL. Each event gets its own n8n Webhook node at a dedicated path.
**When to use:** D-10 and D-11 -- separate workflows per event type.
**Details:**
- Base URL in docker-compose: `http://n8n:5678/webhook/whatsapp-inbound`
- With `WEBHOOK_BY_EVENTS=true`, events route to:
  - `CONNECTION_UPDATE` -> `http://n8n:5678/webhook/whatsapp-inbound/connection-update`
  - `MESSAGES_UPSERT` -> `http://n8n:5678/webhook/whatsapp-inbound/messages-upsert`
  - `QRCODE_UPDATED` -> `http://n8n:5678/webhook/whatsapp-inbound/qrcode-updated`
- Each n8n workflow has its own Webhook node listening on the specific path.

### Pattern 4: n8n Alert Workflow
**What:** `whatsapp-connection-update` workflow receives CONNECTION_UPDATE webhook, checks if `data.state == "close"`, and sends WhatsApp alert to admin.
**Flow:**
1. Webhook node receives POST at `/webhook/whatsapp-inbound/connection-update`
2. IF node checks `{{ $json.data.state }}` equals `"close"` or `"connecting"`
3. HTTP Request node POSTs to Evolution API `/message/sendText/{instance}` with alert message
4. On `state == "open"`, optionally log reconnection to `workflow_errors` or a new `system_events` table.

### Anti-Patterns to Avoid
- **Polling from n8n for connection state:** Don't create a scheduled n8n workflow that polls connectionState. Use webhooks (push) instead -- that's what CONNECTION_UPDATE events are for.
- **Single mega-workflow:** Don't put all webhook handling in one workflow with complex Switch nodes. Use separate webhook paths and workflows per event type (per D-11).
- **Storing session state in Streamlit only:** Don't rely on `st.session_state` for persistent connection state. It resets on browser refresh. If persistence is needed, write to PostgreSQL.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| QR code generation | Custom QR library in Python | Evolution API `/instance/connect/{instance}` returns base64 QR | Evolution handles QR rotation, expiry, and WhatsApp protocol |
| WhatsApp protocol | Baileys/websocket code | Evolution API REST endpoints | Evolution wraps Baileys; direct Baileys usage is fragile |
| Webhook event routing | Custom HTTP server or n8n Switch node routing | `WEBHOOK_GLOBAL_WEBHOOK_BY_EVENTS=true` URL routing | Evolution appends event name to URL automatically |
| Auto-refresh in Streamlit | `while True: time.sleep(); st.rerun()` loop | `st_autorefresh` component or `time.time()` check in session_state | Cleaner, no blocking sleep in the UI thread |

## Common Pitfalls

### Pitfall 1: Manager UI Iframe Assumption (CRITICAL)
**What goes wrong:** D-01 assumes Evolution API has a built-in QR/manager page accessible via iframe. The Manager UI is actually a SEPARATE Docker container (`evolution-manager-v2`, port 3000) NOT bundled in `atendai/evolution-api:v2.2.3`.
**Why it happens:** Evolution API v1 had a simpler built-in manager. v2 extracted it into a separate React app.
**How to avoid:** Two options:
  1. **Add evolution-manager container** to docker-compose and iframe it. Adds ~256MB RAM, requires `atendai/evolution-manager` image, and may have cross-origin/X-Frame-Options issues.
  2. **Use REST API directly** -- call `/instance/connect/{instance}` from Streamlit, get base64 QR, display with `st.image()`. Simpler, no extra container, no iframe issues. This technically deviates from D-01's "zero custom QR rendering code" but is only 5-10 lines of Python wrapping a single API call.
**Recommendation:** Planner should present option 2 as the pragmatic approach. The spirit of D-01 (no custom QR protocol code) is preserved -- we're just displaying an image the API already generates. If the user insists on D-01 literally, option 1 works but adds complexity.

### Pitfall 2: Evolution API Instance Must Be Created Before Connect
**What goes wrong:** Calling `/instance/connect/{instance}` on a non-existent instance returns 404.
**Why it happens:** The instance must first be created via POST `/instance/create` with `{"instanceName": "...", "integration": "WHATSAPP-BAILEYS", "qrcode": true}`.
**How to avoid:** The WhatsApp page should first check if the instance exists (via `/instance/fetchInstances`), create it if missing, then show QR.
**Warning signs:** 404 errors on connect endpoint.

### Pitfall 3: Webhook URL Path with WEBHOOK_BY_EVENTS
**What goes wrong:** Webhooks don't arrive at n8n because the URL path doesn't match.
**Why it happens:** When `WEBHOOK_GLOBAL_WEBHOOK_BY_EVENTS=true`, Evolution API transforms event names: `CONNECTION_UPDATE` becomes `/connection-update` (lowercase, hyphen-separated). The n8n webhook path must match exactly.
**How to avoid:** Set n8n Webhook node paths to:
  - `/webhook/whatsapp-inbound/connection-update`
  - `/webhook/whatsapp-inbound/messages-upsert`
**Warning signs:** n8n shows no executions for the webhook workflow.

### Pitfall 4: Streamlit Reruns Reset State
**What goes wrong:** Connection status flickers or disappears on page interaction.
**Why it happens:** Every Streamlit widget interaction triggers a full script rerun. If the API call is slow or fails, the sidebar shows stale/missing data.
**How to avoid:** Cache the connection state in `st.session_state` with a timestamp. Only re-poll when 60+ seconds have elapsed. Handle exceptions gracefully with a fallback "unknown" state.

### Pitfall 5: Alert Fires When Clinic Number Is Disconnected
**What goes wrong:** The alert tries to send via the disconnected clinic number and silently fails (D-09 accepted limitation).
**Why it happens:** The same Evolution API instance that just disconnected is used to send the alert.
**How to avoid:** This is accepted per D-09. Document it clearly. In the future (deferred), add email fallback.

### Pitfall 6: Evolution API v2.2.3 Is Behind Latest
**What goes wrong:** QR code flow may have bugs fixed in later versions (v2.3.x).
**Why it happens:** Phase 1 pinned `atendai/evolution-api:v2.2.3`. Latest is v2.3.7 under `evoapicloud/evolution-api`.
**How to avoid:** Stick with v2.2.3 for stability. If QR issues arise during implementation, upgrading to v2.3.x is a valid escape hatch (requires changing docker image to `evoapicloud/evolution-api:v2.3.7`). Do NOT upgrade preemptively.

### Pitfall 7: Streamlit Environment Variables in Docker
**What goes wrong:** Streamlit can't reach Evolution API because env vars are missing.
**Why it happens:** The current docker-compose passes `DATABASE_URL` and `N8N_WEBHOOK_BASE_URL` to the Streamlit service, but does NOT pass `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCE_NAME`, or `EVOLUTION_API_URL`.
**How to avoid:** Add these env vars to the `streamlit` service in `docker-compose.yml`:
```yaml
EVOLUTION_API_URL: http://evolution-api:8080
EVOLUTION_API_KEY: ${EVOLUTION_API_KEY}
EVOLUTION_INSTANCE_NAME: ${EVOLUTION_INSTANCE_NAME:-clinic-main}
ADMIN_WHATSAPP_NUMBER: ${ADMIN_WHATSAPP_NUMBER}
CLINIC_WHATSAPP_NUMBER: ${CLINIC_WHATSAPP_NUMBER}
```

## Code Examples

### Evolution API: Create Instance
```python
# Source: https://doc.evolution-api.com/v2/api-reference (verified via web research)
import requests

def create_instance(api_url, api_key, instance_name):
    resp = requests.post(
        f"{api_url}/instance/create",
        headers={"apikey": api_key, "Content-Type": "application/json"},
        json={
            "instanceName": instance_name,
            "integration": "WHATSAPP-BAILEYS",
            "qrcode": True
        },
        timeout=10
    )
    resp.raise_for_status()
    return resp.json()
    # Response includes: {"instance": {...}, "hash": {...}, "qrcode": {"base64": "data:image/png;base64,..."}}
```

### Evolution API: Get QR Code (Connect)
```python
# Source: https://deepwiki.com/EvolutionAPI/evolution-api/7-api-reference
def get_qr_code(api_url, api_key, instance_name):
    resp = requests.get(
        f"{api_url}/instance/connect/{instance_name}",
        headers={"apikey": api_key},
        timeout=10
    )
    resp.raise_for_status()
    data = resp.json()
    # Returns base64 QR image string
    return data.get("base64", "")
```

### Evolution API: Check Connection State
```python
# Source: https://deepwiki.com/EvolutionAPI/evolution-api/7-api-reference
def get_connection_state(api_url, api_key, instance_name):
    resp = requests.get(
        f"{api_url}/instance/connectionState/{instance_name}",
        headers={"apikey": api_key},
        timeout=5
    )
    resp.raise_for_status()
    return resp.json()
    # Returns: {"instance": {"instanceName": "...", "state": "open|close|connecting"}}
```

### Evolution API: Send Text Message (for alert)
```python
# Source: https://doc.evolution-api.com/v2/api-reference/message-controller/send-text
def send_text_message(api_url, api_key, instance_name, number, text):
    resp = requests.post(
        f"{api_url}/message/sendText/{instance_name}",
        headers={"apikey": api_key, "Content-Type": "application/json"},
        json={"number": number, "text": text},
        timeout=10
    )
    resp.raise_for_status()
    return resp.json()
```

### CONNECTION_UPDATE Webhook Payload
```json
// Source: Evolution API SDK + GitHub issues analysis
// Delivered to: POST http://n8n:5678/webhook/whatsapp-inbound/connection-update
{
  "event": "CONNECTION_UPDATE",
  "instance": "clinic-main",
  "data": {
    "instance": "clinic-main",
    "state": "close",
    "statusReason": 401
  }
}
// Possible state values: "open", "close", "connecting"
```

### MESSAGES_UPSERT Webhook Payload (stub)
```json
// Delivered to: POST http://n8n:5678/webhook/whatsapp-inbound/messages-upsert
{
  "event": "MESSAGES_UPSERT",
  "instance": "clinic-main",
  "data": {
    "key": {
      "remoteJid": "5531982968XX@s.whatsapp.net",
      "fromMe": false,
      "id": "BAE594145F4C59B4"
    },
    "message": {
      "conversation": "Hola, quiero agendar una cita"
    },
    "messageTimestamp": "1717689097"
  }
}
```

### n8n Alert Message Template
```
// Used in HTTP Request node body for /message/sendText/{instance}
{
  "number": "{{ $env.ADMIN_WHATSAPP_NUMBER }}",
  "text": "La sesion de WhatsApp se desconecto a las {{ $now.format('yyyy-MM-dd HH:mm') }}. Escanea el QR para reconectar: https://admin.{{ $env.DOMAIN }}/WhatsApp"
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Evolution API v1 built-in manager | v2 separate manager container | v2.0 (2024) | Manager must be deployed separately if iframe approach is desired |
| `atendai/evolution-api` Docker image | `evoapicloud/evolution-api` for v2.3+ | v2.3.0 (Sep 2024) | Different Docker Hub publisher; v2.2.3 still under `atendai` |
| Streamlit pages/ directory auto-detect | `st.Page` + `st.navigation` | Streamlit 1.36+ (2024) | Preferred multipage approach; pages/ still works but navigation is more flexible |
| Evolution API REST paths without /api/v1 | Paths include /api/v1 prefix | v2.x | Some docs show paths without prefix; always use full path in code |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (Python, for Streamlit components) + n8n manual execution |
| Config file | none -- Wave 0 creates pytest.ini |
| Quick run command | `docker compose exec streamlit pytest tests/ -x --tb=short` |
| Full suite command | `docker compose exec streamlit pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | QR code retrieval from Evolution API | integration | `pytest tests/test_evolution_api.py::test_get_qr_code -x` | No -- Wave 0 |
| INFRA-01 | Instance creation when missing | integration | `pytest tests/test_evolution_api.py::test_create_instance -x` | No -- Wave 0 |
| INFRA-02 | Connection state polling returns valid state | unit | `pytest tests/test_sidebar.py::test_connection_state_display -x` | No -- Wave 0 |
| INFRA-02 | Sidebar renders correct status indicator | unit | `pytest tests/test_sidebar.py::test_sidebar_connected -x` | No -- Wave 0 |
| INFRA-03 | n8n workflow receives CONNECTION_UPDATE | manual | Send test webhook via curl to n8n endpoint | N/A |
| INFRA-03 | Alert message sent on disconnect | manual | Trigger workflow manually in n8n UI, verify message sent | N/A |

### Sampling Rate
- **Per task commit:** `docker compose exec streamlit pytest tests/ -x --tb=short`
- **Per wave merge:** Full test suite + manual n8n workflow test
- **Phase gate:** All automated tests green + manual verification of 4 success criteria

### Wave 0 Gaps
- [ ] `admin-ui/src/tests/test_evolution_api.py` -- covers INFRA-01 (API client tests with mocked responses)
- [ ] `admin-ui/src/tests/test_sidebar.py` -- covers INFRA-02 (sidebar rendering logic)
- [ ] `admin-ui/src/tests/conftest.py` -- shared fixtures (mock Evolution API responses)
- [ ] `admin-ui/src/pytest.ini` or `pyproject.toml` test config
- [ ] Framework install: add `pytest` and `pytest-mock` to `admin-ui/requirements.txt`

## Open Questions

1. **Manager iframe vs. direct QR rendering**
   - What we know: Manager UI is a separate container not bundled in `atendai/evolution-api:v2.2.3`. D-01 specifies iframe approach.
   - What's unclear: Whether user will accept the pragmatic alternative (REST API + st.image) or insists on literal D-01.
   - Recommendation: Plan for REST API approach (option 2) as primary, note D-01 deviation, let user decide during review.

2. **Evolution API endpoint path prefix**
   - What we know: DeepWiki says paths use `/api/v1/` prefix. Some docs show without prefix.
   - What's unclear: Whether v2.2.3 requires the `/api/v1/` prefix or uses bare paths like `/instance/connectionState/{name}`.
   - Recommendation: Test both during implementation. Start without prefix (matches most v2 examples), fall back to `/api/v1/` prefix.

3. **connectionState response shape**
   - What we know: Expected `{"instance": {"instanceName": "...", "state": "open"}}` but exact schema may vary by version.
   - What's unclear: Exact response JSON structure for v2.2.3.
   - Recommendation: Log raw response during first implementation, adapt parser accordingly.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker Compose | All services | Yes (Phase 1) | v2.x | -- |
| Evolution API | WhatsApp session | Yes (Phase 1) | v2.2.3 | -- |
| n8n | Webhook workflows | Yes (Phase 1) | latest | -- |
| PostgreSQL | Event logging | Yes (Phase 1) | 16-alpine | -- |
| Streamlit | Admin UI | Yes (Phase 1) | >=1.35 | -- |
| requests (Python) | API calls from Streamlit | Yes (bundled with Python) | stdlib | -- |
| pytest | Test framework | No | -- | Add to requirements.txt (Wave 0) |

**Missing dependencies with no fallback:** None -- all core infrastructure deployed in Phase 1.

**Missing dependencies with fallback:**
- pytest: Add to `admin-ui/requirements.txt` in Wave 0.

## Project Constraints (from CLAUDE.md)

- **Infrastructure:** VPS Hostinger with limited resources -- avoid adding unnecessary containers (relevant to manager iframe decision)
- **WhatsApp:** Evolution API is non-official -- risk of WhatsApp Web protocol changes; pin version
- **Concurrency:** 100+ concurrent users on bot -- not relevant for this phase (single admin)
- **Privacy:** Medical data encrypted at rest -- not directly relevant for session management, but logs should be anonymized
- **Solo developer:** Keep implementation simple -- prefer REST API approach over managing additional containers
- **Docker Compose:** All services in single compose file on one VPS
- **Evolution API:** Pin to specific release tag (v2.2.3), update deliberately after testing
- **Streamlit:** Must have Caddy basic auth in front (already configured in Phase 1 Caddyfile)

## Sources

### Primary (HIGH confidence)
- Evolution API official docs (https://doc.evolution-api.com/v2/) -- webhook events, send text endpoint
- Streamlit official docs (https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation) -- multipage app patterns
- DeepWiki Evolution API reference (https://deepwiki.com/EvolutionAPI/evolution-api/7-api-reference) -- instance controller endpoints
- Phase 1 codebase -- docker-compose.yml, .env.example, admin-ui scaffold, database schema

### Secondary (MEDIUM confidence)
- DeepWiki Manager UI guide (https://deepwiki.com/EvolutionAPI/evolution-api/8-development-guide) -- manager is separate container
- Evolution API GitHub issues #2380, #2216 -- QR flow documentation gaps in v2.2.3
- Postman collection (https://www.postman.com/agenciadgcode/evolution-api/documentation/gqr041s/evolution-api-v2-0) -- endpoint schemas
- Evolution API SDK (https://github.com/gusnips/evolution-api-sdk) -- webhook payload structures

### Tertiary (LOW confidence)
- CONNECTION_UPDATE payload schema -- reconstructed from SDK code and GitHub issues, not from official docs. Needs validation during implementation.
- MESSAGES_UPSERT payload schema -- same; exact field names should be verified against actual webhook deliveries.
- Evolution API path prefix (`/api/v1/` vs bare) -- conflicting sources; needs runtime verification.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all services already deployed in Phase 1, versions known
- Architecture: MEDIUM -- Streamlit multipage pattern is well-documented, but Evolution API endpoint shapes need runtime verification
- Pitfalls: HIGH -- manager iframe issue is well-researched and critical for planning
- Webhook payloads: LOW -- reconstructed from indirect sources, needs validation

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (30 days -- Evolution API is actively developed, monitor for breaking changes)
