---
phase: 02-whatsapp-core
verified: 2026-03-28T12:00:00Z
status: human_needed
score: 6/7 must-haves verified
re_verification: false
human_verification:
  - test: "QR scan and connect via admin UI"
    expected: "Admin opens https://admin.DOMAIN/WhatsApp, a QR code is displayed, scanning it with WhatsApp shows the session as Connected (green dot in sidebar)"
    why_human: "Requires live Evolution API container and a physical phone — cannot verify QR/session handshake programmatically"
  - test: "Sidebar status persistence across pages"
    expected: "After WhatsApp page shows connected, navigating to Dashboard still shows green dot with clinic number in sidebar"
    why_human: "Requires live Streamlit session with real Evolution API polling — browser state behavior cannot be verified without a running app"
  - test: "Disconnect alert delivery to admin"
    expected: "Simulating a disconnect (curl POST with state=close to n8n webhook) results in a WhatsApp message received on ADMIN_WHATSAPP_NUMBER within 5 minutes"
    why_human: "Requires live n8n + Evolution API + connected WhatsApp session — end-to-end HTTP chain cannot be verified statically"
  - test: "Send/receive validation (ROADMAP Success Criterion 4)"
    expected: "A message sent via n8n workflow is received on the clinic WhatsApp number; an inbound message from the clinic number triggers the messages-upsert webhook"
    why_human: "Requires a connected WhatsApp session — runtime integration test"
  - test: "ROADMAP plan checkbox for 02-02"
    expected: "ROADMAP.md shows [x] 02-02-PLAN.md after verifying files and commits exist"
    why_human: "ROADMAP shows [ ] for 02-02 despite code and commits existing — tracking discrepancy requires human to decide whether to mark complete"
---

# Phase 2: WhatsApp Core Verification Report

**Phase Goal:** Clinic admin can connect WhatsApp via Evolution API (QR scan), see live connection status in the Streamlit admin UI, and receive an automated alert if the session drops — with a working n8n stub ready for Phase 4 chatbot wiring.
**Verified:** 2026-03-28
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Streamlit container receives Evolution API env vars at runtime | VERIFIED | `docker-compose.yml` lines 123-129: `EVOLUTION_API_URL`, `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCE_NAME`, `ADMIN_WHATSAPP_NUMBER`, `CLINIC_WHATSAPP_NUMBER`, `DOMAIN`, `ADMIN_SUBDOMAIN` all injected into streamlit service |
| 2 | Evolution API client module can create instances, fetch QR, check connection state, and send text messages | VERIFIED | `evolution_api.py` exports `EvolutionAPIClient` with `create_instance`, `get_qr_code`, `get_connection_state`, `send_text_message`, `fetch_instances`; 9 tests pass |
| 3 | Test scaffolds exist and run green with mocked API responses | VERIFIED | 14 tests pass (9 API client + 5 sidebar); zero failures or skips |
| 4 | Admin can see WhatsApp connection status (green/red dot) in sidebar on every page | VERIFIED | `sidebar.py` implements `render_sidebar()` with `POLL_INTERVAL_SECONDS=60`; `app.py` calls `render_sidebar()` before `pg.run()` so it appears on every page |
| 5 | Admin can navigate to a dedicated WhatsApp page to scan QR and connect | VERIFIED | `2_WhatsApp.py` exists; calls `get_connection_state`, `create_instance`, `get_qr_code`, displays with `st.image`; handles instance-not-found (404) gracefully |
| 6 | When WhatsApp session disconnects, admin receives a WhatsApp alert within 5 minutes | HUMAN NEEDED | Workflow JSON correct (Webhook -> IF disconnect -> HTTP Request to sendText); requires live environment to confirm delivery |
| 7 | MESSAGES_UPSERT events are received and logged without errors | HUMAN NEEDED | `whatsapp-message-stub.json` has `active: true` and correct path `whatsapp-inbound/messages-upsert` with NoOp node; requires live n8n import to confirm no-error behavior |

**Score:** 5/7 truths fully verified by code inspection; 2 require human runtime testing

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `docker-compose.yml` | Streamlit env vars for Evolution API | VERIFIED | 7 env vars added to streamlit service; `evolution-api` added as dependency |
| `.env.example` | Documents new env vars | VERIFIED | `EVOLUTION_INSTANCE_NAME`, `ADMIN_WHATSAPP_NUMBER`, `CLINIC_WHATSAPP_NUMBER` present at lines 27-29 |
| `admin-ui/src/components/evolution_api.py` | HTTP client wrapper | VERIFIED | 113 lines; `EvolutionAPIClient` and `EvolutionAPIError` classes; all 5 required methods implemented |
| `admin-ui/src/tests/test_evolution_api.py` | Tests >= 50 lines with mocked responses | VERIFIED | 126 lines; 9 test functions; all pass |
| `admin-ui/src/tests/test_sidebar.py` | Tests >= 30 lines | VERIFIED | 61 lines; 5 test functions; all pass |
| `admin-ui/src/components/sidebar.py` | Shared sidebar with status dot | VERIFIED | 92 lines; `render_sidebar()`, `POLL_INTERVAL_SECONDS=60`, green/red/orange status dots, phone number caption |
| `admin-ui/src/pages/2_WhatsApp.py` | QR scanning page | VERIFIED | 84 lines; `st.image`, `create_instance`, `get_qr_code`, `get_connection_state`, D-01 comment, manual refresh button |
| `admin-ui/src/app.py` | Streamlit multipage app with st.navigation | VERIFIED | Uses `st.navigation`, imports `render_sidebar`, registers both pages |
| `admin-ui/src/pages/1_Dashboard.py` | Dashboard placeholder | VERIFIED | `st.title("Dashboard")` + `st.info(...)` |
| `n8n/workflows/whatsapp-connection-update.json` | n8n connection alert workflow >= 20 lines | VERIFIED | 137 lines; valid JSON; `active: true`; 4 nodes: Webhook, IF, HTTP Request, NoOp |
| `n8n/workflows/whatsapp-message-stub.json` | n8n message stub >= 10 lines | VERIFIED | 52 lines; valid JSON; `active: true`; 2 nodes: Webhook, NoOp |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `sidebar.py` | `evolution_api.py` | `from components.evolution_api import EvolutionAPIClient, EvolutionAPIError` | WIRED | Line 6 of sidebar.py; `client.get_connection_state()` called in `render_sidebar()` |
| `2_WhatsApp.py` | `evolution_api.py` | `from components.evolution_api import EvolutionAPIClient, EvolutionAPIError` | WIRED | Line 9 of 2_WhatsApp.py; `create_instance`, `get_qr_code`, `get_connection_state` all called |
| `app.py` | `sidebar.py` | `from components.sidebar import render_sidebar` | WIRED | Line 2 of app.py; `render_sidebar()` called on line 7 before `pg.run()` |
| `docker-compose.yml` streamlit | env vars | `EVOLUTION_API_URL`, `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCE_NAME` | WIRED | `evolution_api.py` reads via `os.environ.get(...)` |
| `evolution-api (docker)` | `n8n /webhook/whatsapp-inbound/connection-update` | `WEBHOOK_GLOBAL_URL + WEBHOOK_BY_EVENTS=true` | WIRED (config) | docker-compose.yml lines 104-106 configure routing; n8n workflow listens on correct path |
| `n8n connection-update workflow` | `evolution-api /message/sendText/{instance}` | HTTP Request node with `apikey` header and `ADMIN_WHATSAPP_NUMBER` body | WIRED (code) | workflow JSON line 61: `http://evolution-api:8080/message/sendText/...`; HUMAN NEEDED for runtime |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `sidebar.py` render_sidebar | `st.session_state["wa_state"]` | `client.get_connection_state()` -> HTTP GET `/instance/connectionState/{name}` -> parses `data.instance.state` | Yes — live API call (not static) | FLOWING |
| `2_WhatsApp.py` | `qr_base64` | `client.get_qr_code()` -> HTTP GET `/instance/connect/{name}` -> parses `data.base64` | Yes — live API call returning QR image | FLOWING |
| `n8n connection-update workflow` | alert text | `$json.data.state` from webhook payload; `$env.*` for env vars | Yes — reads webhook payload and env vars | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 14 tests pass | `python3 -m pytest admin-ui/src/tests/ -v --tb=short` | 14 passed in 0.17s | PASS |
| workflow JSONs are valid and parseable | `python3 -c "import json; json.load(open('n8n/workflows/whatsapp-connection-update.json'))"` | No exception | PASS |
| message-stub JSON valid | `python3 -c "import json; json.load(open('n8n/workflows/whatsapp-message-stub.json'))"` | No exception | PASS |
| git commits from summaries exist | `git log --oneline \| grep commit-hash` | All 7 hashes found (988e9e9, 3e54a86, 0c342dc, 45d68ac, 2986f40, 837f2d3, 0eb3952) | PASS |
| Live QR scan + session connect | Requires docker compose up + physical phone | Not runnable in static context | SKIP |
| Disconnect alert delivery | Requires live n8n + Evolution API + connected session | Not runnable in static context | SKIP |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| INFRA-01 | 02-01, 02-02 | Admin can connect/reconnect WhatsApp session by scanning QR from UI | SATISFIED (code) / HUMAN NEEDED (runtime) | `2_WhatsApp.py` displays QR via `st.image`; `create_instance` + `get_qr_code` wired; runtime QR scan requires human verification |
| INFRA-02 | 02-01, 02-02 | System shows WhatsApp session status (connected/disconnected) visible at all times | SATISFIED | `sidebar.py` `render_sidebar()` called from `app.py` before page routing; polls every 60s; green/red/orange status dots displayed |
| INFRA-03 | 02-03 | System automatically detects session disconnection and sends alert to admin | SATISFIED (code) / HUMAN NEEDED (runtime) | n8n workflow routes `state=close/connecting` to HTTP POST `sendText`; `active: true`; delivery requires live stack |

Note: REQUIREMENTS.md traceability table still shows all three INFRA requirements as "Pending". The table has not been updated to reflect completion — this is a tracking discrepancy only (the code fulfills the requirements).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `1_Dashboard.py` | All | `st.info("Sistema en construccion...")` | Info | Intentional placeholder page — not blocking; future phases will add content |
| `whatsapp-message-stub.json` | All | NoOp stub node — "Phase 4 wires chatbot here" | Info | Intentional by design — Phase 4 replaces this node; correctly documented |
| `ROADMAP.md` | Line 54 | `[ ] 02-02-PLAN.md` checkbox unchecked despite code and commits existing | Warning | Tracking discrepancy — ROADMAP shows 02-02 as incomplete but all files are created and committed (git: 2986f40, 837f2d3) |

No blocking anti-patterns found. The two "stub" entries are intentional scaffolding by design.

### Human Verification Required

#### 1. QR Scan and Session Connect (INFRA-01)

**Test:** Run `docker compose up -d` on the VPS. Open the admin UI at `https://admin.DOMAIN/`. Navigate to the WhatsApp page in the sidebar. A QR code should be displayed.

**Expected:** Scanning the QR code with WhatsApp (Menu > Linked Devices > Link a Device) results in the sidebar showing a green dot and "Conectado" label. The clinic phone number should appear under the dot.

**Why human:** Requires a live Evolution API container, a running Streamlit app, and a physical phone with WhatsApp installed.

#### 2. Sidebar Status Persistence Across Pages

**Test:** With WhatsApp connected (green dot on WhatsApp page), navigate to the Dashboard page.

**Expected:** Sidebar still shows green dot, "Conectado", and clinic phone number on the Dashboard page — demonstrating the shared sidebar works on all pages.

**Why human:** Requires a live Streamlit session with real session_state polling.

#### 3. Disconnect Alert Delivery (INFRA-03)

**Test:** Import `whatsapp-connection-update.json` into n8n (Settings > Import from File). Activate the workflow. Then run: `curl -X POST http://localhost:5678/webhook/whatsapp-inbound/connection-update -H "Content-Type: application/json" -d '{"event":"CONNECTION_UPDATE","instance":"clinic-main","data":{"instance":"clinic-main","state":"close","statusReason":401}}'`

**Expected:** Within 5 minutes, a WhatsApp message is received on the number set in `ADMIN_WHATSAPP_NUMBER` reading something like: "La sesion de WhatsApp se desconecto a las [timestamp]. Escanea el QR para reconectar: https://admin.DOMAIN/WhatsApp. Estado reportado: close"

**Why human:** Requires live n8n + Evolution API + a WhatsApp number already connected to send the alert.

#### 4. Send/Receive Validation (ROADMAP Success Criterion 4)

**Test:** From n8n, use an HTTP Request node to POST to `/message/sendText/clinic-main` and verify the message arrives on the clinic's physical WhatsApp. Then send a message to the clinic's WhatsApp number and verify the `messages-upsert` webhook fires in n8n.

**Expected:** Both directions of WhatsApp messaging work — outbound from n8n and inbound to n8n webhook.

**Why human:** Full end-to-end messaging requires a connected WhatsApp session and physical phone.

#### 5. ROADMAP Tracking Discrepancy

**Test:** Check whether `02-02-PLAN.md` should be marked complete in ROADMAP.md.

**Expected:** `[ ] 02-02-PLAN.md` on line 54 of ROADMAP.md should be `[x]` — all files exist (sidebar.py, 2_WhatsApp.py, app.py, 1_Dashboard.py) and commits 2986f40 and 837f2d3 are in git log.

**Why human:** The human-verify checkpoint in Plan 02-02 Task 3 records "approved" in the summary but the ROADMAP checkbox was not updated. A human should confirm 02-02 is done and update the checkbox.

### Gaps Summary

No blocking gaps found. All code artifacts are present, substantive, and wired. Tests pass. Workflow JSONs are valid, active, and structurally correct.

The 5 human verification items are runtime/integration tests that cannot be validated from code inspection alone. They are all expected outcomes of correctly wired code — not indicators of missing implementation.

The only actionable non-runtime item is the ROADMAP tracking discrepancy: `02-02-PLAN.md` should be marked `[x]` in ROADMAP.md.

---

_Verified: 2026-03-28_
_Verifier: Claude (gsd-verifier)_
