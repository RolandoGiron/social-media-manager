# Phase 5: Campaign Blast - Research

**Researched:** 2026-04-12
**Domain:** Streamlit multi-step broadcast UI + n8n rate-limited send loop + PostgreSQL campaign tracking
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**UI Location**
- D-01: New sidebar page `7_Campañas.py` — dedicated broadcast workflow. Admin selects segment, selects template, sees rendered message preview + recipient count, confirms, then monitors progress in the same page.
- D-02: Navigation order in `app.py`: 7_Campañas is added after 6_Knowledge_Base. No changes to existing page order.

**Campaign Launch Flow (Streamlit)**
- D-03: Step 1 — Admin picks segment (tag multiselect) and template (dropdown). UI immediately shows recipient count ("X pacientes") and a rendered message preview with sample values substituted.
- D-04: Step 2 — Confirmation gate (WA-03): "Estás a punto de enviar a X pacientes. ¿Confirmar?" with patient count prominently displayed. Two buttons: "Confirmar y enviar" and "Cancelar". No message is sent before this confirmation.
- D-05: On confirm: Streamlit inserts a row into `campaign_log` (status='pending', total_recipients=N), inserts N rows into `campaign_recipients` (status='pending'), then fires an n8n webhook with the `campaign_id`. Page switches to progress view.
- D-06: Campaign name is auto-generated: "{tag_name} · {fecha}" (e.g., "acné · 12 abr 2026"). No manual naming required.

**n8n Broadcast Workflow**
- D-07: New n8n workflow `campaign-blast.json`. Triggered by Streamlit webhook POST with `campaign_id`. Queries `campaign_recipients WHERE campaign_id = ? AND status = 'pending'`, iterates each recipient with a loop node.
- D-08: Rate limiting: 3-8 second delay with random jitter between each send (n8n Wait node or Code node with `await new Promise(r => setTimeout(r, delay))`).
- D-09: Before each send, n8n checks `campaign_log.status`. If status is `'cancelled'`, the loop exits immediately.
- D-10: After each successful send: UPDATE `campaign_recipients SET status='sent', wa_message_id=?, sent_at=now()` and UPDATE `campaign_log SET sent_count = sent_count + 1`. On failure: UPDATE `campaign_recipients SET status='failed', error_message=?`, increment `failed_count`.
- D-11: On loop completion: UPDATE `campaign_log SET status='completed', completed_at=now()`.

**Progress Monitoring (Streamlit)**
- D-12: After launch, the Campañas page switches to progress view. Auto-refreshes every 5 seconds by polling `campaign_log` for `sent_count`, `failed_count`, `total_recipients`, `status`.
- D-13: Progress display: Streamlit progress bar (`st.progress`) showing sent_count/total_recipients, label "X / N enviados", and a "Cancelar campaña" button visible while status is `in_progress`.
- D-14: Cancel button: Streamlit sets `campaign_log.status = 'cancelled'`, `cancelled_at = now()`. n8n picks this up on next iteration check (D-09).
- D-15: Campaign history table below active progress section: shows all past campaigns ordered by `created_at DESC` with columns: Nombre, Segmento, Enviados, Estado, Fecha.

### Claude's Discretion
- Exact jitter implementation in n8n (random integer between 3000 and 8000 ms)
- Evolution API endpoint for sending messages (reuse pattern from `sub-send-wa-message.json`)
- Streamlit session state variable names for multi-step flow
- Error state visual treatment in the progress bar (failed_count shown in red)
- Estimated time remaining calculation (approximate: remaining * avg_delay)

### Deferred Ideas (OUT OF SCOPE)
- Per-recipient delivery status (delivered/read tracking via Evolution API webhooks) — DASH-02 requirement, Phase 7
- Scheduled future send (set a date/time for the blast) — not in Phase 5 success criteria; defer to v2
- Opt-in/opt-out exclusion filter — v2 requirement (PRIV-01); campaigns in v1 send to all patients in segment
- Campaign template preview with multiple sample recipients (rotating preview) — UX enhancement, not required for MVP
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WA-02 | Administrador puede enviar broadcast masivo a un segmento de pacientes seleccionado, con rate limiting automático (delays con jitter) para prevenir baneo de número | n8n Loop node + Wait/Code node with `Math.random()` jitter; Evolution API `/message/sendText/{instance}` endpoint confirmed in `sub-send-wa-message.json` |
| WA-03 | Sistema muestra paso de confirmación antes de envío masivo indicando número de destinatarios ("Estás a punto de enviar a N pacientes. ¿Confirmar?") | Streamlit multi-step flow via `session_state` — established pattern in `pacientes_mode` and `plantillas_mode`; confirmation gate UI specified in 05-UI-SPEC.md |
| WA-04 | Administrador puede cancelar un broadcast en progreso | Cancel pattern: Streamlit sets `campaign_log.status='cancelled'`; n8n reads this flag at top of each loop iteration and breaks; `campaign_recipients` rows remaining as `'pending'` — never sent |
</phase_requirements>

---

## Summary

Phase 5 builds a two-component feature: a Streamlit page (`7_Campañas.py`) and an n8n workflow (`campaign-blast.json`). The Streamlit side handles the full UX flow — segment + template selection, confirmation gate, DB writes, webhook trigger to n8n, and polling-based progress monitoring. The n8n side handles the rate-limited send loop against Evolution API.

All infrastructure is already running and healthy: PostgreSQL, n8n, Evolution API, Redis, and the Streamlit container are all up. The `campaign_log` and `campaign_recipients` tables exist in the schema (`001_schema.sql`), so no database migration is needed. The Evolution API send pattern is already proven in `sub-send-wa-message.json`. The autorefresh polling pattern is already proven in `5_Inbox.py`. The multi-step `session_state` mode pattern is proven in `3_Pacientes.py` and `4_Plantillas.py`.

The key planning risk is the n8n loop + cancellation pattern: n8n does not have a native "break-on-condition" in its Loop node — cancellation must be implemented by checking the DB status flag before each send (the IF-node approach described in D-09). This is a well-understood pattern in n8n; the planner should not hand-roll a custom cancellation mechanism.

**Primary recommendation:** Build `7_Campañas.py` by composing existing patterns (tag multiselect from Pacientes, template dropdown from Plantillas, autorefresh from Inbox, session_state mode toggle from Pacientes/Plantillas). Build `campaign-blast.json` using the Webhook Trigger → Postgres Select → Loop → IF(cancelled?) → Wait(jitter) → HTTP Request (Evolution API) → Postgres Update pattern.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Streamlit | >=1.35 (pinned in requirements.txt) | Admin UI pages, session state, progress bar, autorefresh | Project standard; all existing pages use it [VERIFIED: admin-ui/requirements.txt] |
| psycopg2-binary | installed | Direct PostgreSQL queries — no ORM | Established pattern in `database.py`; all DB functions use `psycopg2` with `RealDictCursor` [VERIFIED: admin-ui/src/components/database.py] |
| streamlit-autorefresh | installed | 5-second polling for progress view | Already installed and used in Phase 4 inbox with ImportError fallback pattern [VERIFIED: admin-ui/requirements.txt, admin-ui/src/pages/5_Inbox.py] |
| requests | installed | Streamlit → n8n webhook HTTP POST | Already in requirements.txt, used in evolution_api client [VERIFIED: admin-ui/requirements.txt] |
| n8n | 1.x (latest, running as clinic-n8n) | Workflow orchestrator: webhook trigger, loop, DB queries, Evolution API calls | Project standard; all automation lives here [VERIFIED: docker-compose.yml, docker ps] |
| Evolution API | v2.3.7 (pinned in docker-compose.yml) | WhatsApp send endpoint | Confirmed running as clinic-evolution; send pattern verified in `sub-send-wa-message.json` [VERIFIED: docker-compose.yml, n8n/workflows/sub-send-wa-message.json] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pandas | installed | Build history DataFrame for `st.dataframe` | Needed for campaign history table — same pattern as patient list in Pacientes page [VERIFIED: admin-ui/requirements.txt] |
| pytest + pytest-mock | installed | Unit tests for new DB functions and campaign logic | Already in requirements.txt and used in existing tests [VERIFIED: admin-ui/requirements.txt] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| n8n Wait node for jitter | Code node with `setTimeout` | Wait node is simpler, less error-prone; Code node gives finer control. Either works — Claude's discretion per D-08. |
| Direct n8n HTTP Request to Evolution API | Call `sub-send-wa-message.json` sub-workflow | Sub-workflow call adds overhead; direct HTTP node is simpler for campaign loop. Since campaign sends need `campaign_id` context, inlining the HTTP Request node is cleaner. |

**Installation:** No new packages required — all dependencies are already in `requirements.txt` and containers are running.

---

## Architecture Patterns

### Recommended Project Structure

New files to create:
```
admin-ui/src/
├── pages/
│   └── 7_Campañas.py           # New: campaign blast page
├── components/
│   └── database.py             # Extend: add campaign DB functions
│   └── templates.py            # No change needed (render_preview reused)
└── tests/
    └── test_campaigns.py       # New: unit tests for campaign DB functions

n8n/workflows/
└── campaign-blast.json         # New: n8n broadcast workflow
```

### Pattern 1: Streamlit Session-State Mode Toggle (established)

**What:** Multi-step page flow controlled by `st.session_state["campanas_mode"]` with values `"setup"` | `"progress"`. History table renders below progress view always (not a separate mode).

**When to use:** Any Streamlit page with mutually exclusive views that must survive reruns.

**Example:**
```python
# Source: admin-ui/src/pages/3_Pacientes.py (pacientes_mode pattern)
st.session_state.setdefault("campanas_mode", "setup")
st.session_state.setdefault("campanas_active_campaign_id", None)
st.session_state.setdefault("campanas_selected_tags", [])
st.session_state.setdefault("campanas_selected_template_id", None)
st.session_state.setdefault("campanas_recipient_count", 0)

if st.session_state.campanas_mode == "setup":
    # ... render setup view
elif st.session_state.campanas_mode == "progress":
    # ... render progress view
```

### Pattern 2: Auto-Refresh Polling with ImportError Fallback (established)

**What:** `st_autorefresh` at 5000ms interval; wrapped in try/except for when package not installed.

**When to use:** Any page that needs live updates by polling the database.

**Example:**
```python
# Source: admin-ui/src/pages/5_Inbox.py
try:
    from streamlit_autorefresh import st_autorefresh
    if st.session_state.campanas_mode == "progress":
        campaign = fetch_campaign_status(st.session_state.campanas_active_campaign_id)
        if campaign and campaign["status"] == "in_progress":
            st_autorefresh(interval=5000, key="campanas_refresh")
except ImportError:
    pass
```

### Pattern 3: Streamlit → n8n Webhook POST (new pattern for this phase)

**What:** After DB inserts, Streamlit fires a POST to n8n webhook URL to trigger the campaign workflow. Uses the `requests` library with `N8N_WEBHOOK_BASE_URL` env var.

**When to use:** Any server-side action that must trigger an n8n workflow asynchronously.

**Example:**
```python
# Source: docker-compose.yml (N8N_WEBHOOK_BASE_URL: http://n8n:5678)
import os
import requests

def trigger_campaign_workflow(campaign_id: str) -> bool:
    """POST campaign_id to n8n campaign-blast webhook. Returns True on success."""
    base_url = os.environ.get("N8N_WEBHOOK_BASE_URL", "http://n8n:5678")
    url = f"{base_url}/webhook/campaign-blast"
    try:
        resp = requests.post(url, json={"campaign_id": campaign_id}, timeout=5)
        return resp.status_code == 200
    except requests.RequestException:
        return False
```

### Pattern 4: n8n Loop with Cancellation Check (key pattern for this phase)

**What:** n8n Loop node iterates over recipient rows. At the top of each iteration, an IF node checks `campaign_log.status`. If `'cancelled'`, the IF node routes to a "Stop" path (no operation); otherwise routes to the send path.

**When to use:** Any n8n loop that needs mid-execution cancellation without relying on execution kill.

**Workflow structure:**
```
Webhook Trigger (POST /webhook/campaign-blast, body: {campaign_id})
  → Postgres: SELECT recipients WHERE campaign_id=? AND status='pending'
  → Postgres: UPDATE campaign_log SET status='in_progress', started_at=now()
  → Loop Over Items
      → Postgres: SELECT status FROM campaign_log WHERE id=? [cancellation check]
      → IF: campaign_log.status == 'cancelled'
          [true]  → No-Op (exits iteration, loop continues to next — but all remaining
                    are skipped because status check will keep returning 'cancelled')
          [false] → Code: delay = Math.floor(Math.random() * 5000) + 3000
                  → Wait: {{$json.delay}} milliseconds
                  → HTTP Request: POST http://evolution-api:8080/message/sendText/clinic-main
                  → IF: HTTP success?
                      [success] → Postgres: UPDATE campaign_recipients SET status='sent' ...
                                → Postgres: UPDATE campaign_log SET sent_count=sent_count+1
                      [failure] → Postgres: UPDATE campaign_recipients SET status='failed' ...
                                → Postgres: UPDATE campaign_log SET failed_count=failed_count+1
  → Postgres: UPDATE campaign_log SET status='completed', completed_at=now()
              (n8n always reaches this; if cancelled, sent_count reflects partial send)
```

**Cancellation nuance:** When status='cancelled', the loop does NOT break — it continues iterating but each iteration's IF check immediately routes to No-Op, so no more messages are sent. The final UPDATE sets status='completed' which would overwrite 'cancelled'. **Fix:** The final UPDATE must check: `UPDATE campaign_log SET status = CASE WHEN status = 'cancelled' THEN 'cancelled' ELSE 'completed' END, completed_at = now() WHERE id = ?`. [ASSUMED — n8n doesn't have a native "break loop" node; this pattern is the standard workaround]

### Pattern 5: Evolution API Send-Message (established)

**What:** HTTP POST to Evolution API `/message/sendText/{instance}` with `apikey` header.

**Example:**
```json
// Source: n8n/workflows/sub-send-wa-message.json
POST http://evolution-api:8080/message/sendText/clinic-main
Headers: { "apikey": "{{$env.EVOLUTION_API_KEY}}", "Content-Type": "application/json" }
Body: { "number": "{{$json.phone_normalized}}", "text": "{{$json.rendered_message}}" }
```

**Critical:** The `number` field must be the `phone_normalized` value from the `patients` table (E.164 format). The `clinic-main` instance name is set via `EVOLUTION_INSTANCE_NAME` env var.

### Pattern 6: DB Functions for Campaign (new additions to database.py)

**What:** Campaign-specific functions added to `database.py`, following the established `get_connection()` / `RealDictCursor` / `try/finally conn.close()` pattern.

**Functions needed:**
```python
# Source pattern: admin-ui/src/components/database.py
def fetch_patients_by_tags(tag_ids: list[str]) -> list[dict]:
    """SELECT patients with any of tag_ids. Returns id, first_name, last_name, phone_normalized."""

def insert_campaign(campaign_name: str, template_id: str, segment_tags: list[str],
                    total_recipients: int) -> dict:
    """INSERT into campaign_log, RETURNING id."""

def insert_campaign_recipients(campaign_id: str, patient_ids: list[str]) -> int:
    """Batch INSERT into campaign_recipients. Returns count."""

def fetch_campaign_status(campaign_id: str) -> dict | None:
    """SELECT campaign_log by id. Returns dict with sent_count, failed_count, total_recipients, status."""

def cancel_campaign(campaign_id: str) -> None:
    """UPDATE campaign_log SET status='cancelled', cancelled_at=now() WHERE id=?."""

def fetch_campaign_history() -> list[dict]:
    """SELECT all campaigns ordered by created_at DESC with tag names."""
```

### Anti-Patterns to Avoid

- **Sending messages before DB commit:** Always commit `campaign_log` + `campaign_recipients` INSERT before firing the n8n webhook. If the webhook fires first and n8n starts before the rows exist, it will find 0 recipients.
- **Polling while status != 'in_progress':** Only call `st_autorefresh` when `status == 'in_progress'`. Stop polling on completed/cancelled to avoid infinite refreshes.
- **Final n8n UPDATE overwriting 'cancelled' status:** Use conditional SQL (`CASE WHEN status = 'cancelled' THEN 'cancelled' ELSE 'completed' END`) to preserve the cancelled state.
- **Using the Loop node's "done" output for the final UPDATE:** The Loop node's "done" branch fires after all iterations including cancelled ones — so the conditional UPDATE must happen on the "done" branch.
- **Hard-coding the Evolution API key in workflow JSON:** Use `{{$env.EVOLUTION_API_KEY}}` expression; the key is already injected as an env var in n8n container (confirmed in docker-compose.yml line 64).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rate limiting between sends | Custom sleep/timer logic in Python | n8n Wait node or Code node `setTimeout` inside the workflow loop | n8n controls execution; Python-side delay would require a background thread and adds complexity to Streamlit's single-thread model |
| Message variable substitution | New regex/substitution code | `templates.render_preview()` in `components/templates.py` | Already handles `{{variable}}` pattern with sample value substitution [VERIFIED: admin-ui/src/components/templates.py] |
| Tag-based patient query | New JOIN logic from scratch | Follow `fetch_patients()` pattern in `database.py` — the `ANY(%s::uuid[])` array parameter pattern is already established [VERIFIED: admin-ui/src/components/database.py line 41] | Reuse the established psycopg2 UUID array pattern |
| Evolution API HTTP call in n8n | New HTTP client code | Replicate the HTTP Request node pattern from `sub-send-wa-message.json` | Already proven; apikey header format and endpoint path confirmed |
| Multi-step page flow | Custom router/state machine | `session_state` mode toggle (pacientes_mode pattern) | Established idiom for this project |
| Progress display | Custom HTML/JS widget | `st.progress()` built-in widget | Works with a 0.0–1.0 float value; zero division guard needed when total=0 |

**Key insight:** This phase is almost entirely composition — the DB schema, send pattern, UI patterns, and polling pattern all exist. The planner should identify the exact new code pieces (new DB functions, new page, new workflow JSON) rather than re-researching patterns that are locked.

---

## Common Pitfalls

### Pitfall 1: n8n Loop Does Not Have Native Break
**What goes wrong:** Admin cancels campaign; n8n loop keeps running through all remaining recipients even though the IF check routes them to No-Op, wasting execution time.
**Why it happens:** n8n's Loop Over Items node does not support early exit. Every item must be processed through some path.
**How to avoid:** The IF(cancelled) → No-Op path is fast (no HTTP call, no wait), so 500 pending recipients might take ~1-2 seconds to drain through the No-Op path. This is acceptable for MVP. Document this behavior in the plan so the executor doesn't misread it as a bug.
**Warning signs:** n8n execution log shows all items processed even after cancellation — this is expected behavior, not a bug.

### Pitfall 2: Streamlit Confirms Before DB Transaction Completes
**What goes wrong:** Streamlit shows "progress" view but n8n starts before `campaign_recipients` rows are inserted (race condition).
**Why it happens:** If the webhook POST happens before `conn.commit()`, n8n queries empty recipients.
**How to avoid:** Order of operations in Streamlit: (1) INSERT campaign_log, (2) INSERT campaign_recipients, (3) conn.commit(), (4) POST webhook, (5) switch to progress mode. Never reorder steps 1-4.

### Pitfall 3: final n8n UPDATE Overwrites 'cancelled' Status
**What goes wrong:** Admin cancels at message 30/100. n8n finishes draining the loop and runs `UPDATE campaign_log SET status='completed'`, overwriting `'cancelled'`.
**Why it happens:** The Loop node's "done" output always fires; the final UPDATE runs unconditionally.
**How to avoid:** Use `CASE WHEN` in the final UPDATE SQL (see Pattern 4 above). Alternatively: add an IF node after the loop that checks current status before updating.

### Pitfall 4: st.progress() Division by Zero
**What goes wrong:** If `total_recipients = 0` (edge case: segment was valid but no patients matched), `st.progress(sent/total)` raises `ZeroDivisionError`.
**Why it happens:** Python division; Streamlit does not guard this.
**How to avoid:** Guard: `progress_val = sent_count / total_recipients if total_recipients > 0 else 0.0`.

### Pitfall 5: phone_normalized Format Mismatch
**What goes wrong:** Evolution API rejects the number format; message fails with 4xx.
**Why it happens:** Evolution API v2 accepts numbers in E.164 without the `+` prefix (e.g., `5215512345678`) or with it — behavior depends on instance configuration.
**How to avoid:** Reuse the exact `number` field value format that works in `sub-send-wa-message.json`. The `phone_normalized` column stores the validated normalized value from Phase 3 import. Test with 1-2 recipients before 50+ blast. [ASSUMED — exact format behavior depends on Evolution API instance config; verify via test send]

### Pitfall 6: n8n Webhook Path Conflict
**What goes wrong:** If the webhook path `campaign-blast` conflicts with an existing webhook, n8n returns 404 or routes to wrong workflow.
**Why it happens:** n8n routes by path; the existing chatbot uses `whatsapp-inbound/messages-upsert`. `campaign-blast` is unique.
**How to avoid:** Use path `campaign-blast` (no namespace prefix needed — different from chatbot webhook). Confirm no other workflow uses this path before activating. [VERIFIED: n8n/workflows/ directory scan — no existing campaign-blast webhook]

### Pitfall 7: clinic-admin Container Is "unhealthy"
**What goes wrong:** The Streamlit container (`clinic-admin`) is reporting `unhealthy` status in `docker ps`. If this is a persistent failure, new page won't load.
**Why it happens:** Docker healthcheck may be misconfigured or Streamlit has a startup issue.
**How to avoid:** The container IS running and serving (port 8501 is bound). The unhealthy status warrants a check but is likely a healthcheck probe issue, not a service failure. Verify by accessing http://localhost:8501. [VERIFIED: docker ps output shows Up 2 hours (unhealthy) — service running but healthcheck failing]

---

## Code Examples

Verified patterns from existing sources:

### Fetch patients by tag_ids (new DB function following established pattern)
```python
# Pattern source: admin-ui/src/components/database.py fetch_patients() tag filter
def fetch_patients_by_tags(tag_ids: list[str]) -> list[dict]:
    """Fetch patients matching any of the given tag IDs."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT DISTINCT p.id, p.first_name, p.last_name, p.phone_normalized
                FROM patients p
                JOIN patient_tags pt ON p.id = pt.patient_id
                WHERE pt.tag_id = ANY(%s::uuid[])
                ORDER BY p.first_name, p.last_name
                """,
                (tag_ids,),
            )
            return cur.fetchall()
    finally:
        conn.close()
```

### Campaign recipients batch insert
```python
# Pattern source: admin-ui/src/components/database.py insert_patients() batch pattern
def insert_campaign_recipients(campaign_id: str, patient_ids: list[str]) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = "INSERT INTO campaign_recipients (campaign_id, patient_id) VALUES %s"
            values = [(campaign_id, pid) for pid in patient_ids]
            execute_values(cur, sql, values)
            count = cur.rowcount
        conn.commit()
        return count
    finally:
        conn.close()
```

### Auto-refresh guard pattern (only while in_progress)
```python
# Pattern source: admin-ui/src/pages/5_Inbox.py st_autorefresh usage
try:
    from streamlit_autorefresh import st_autorefresh
    campaign = fetch_campaign_status(st.session_state.campanas_active_campaign_id)
    if campaign and campaign["status"] == "in_progress":
        st_autorefresh(interval=5000, key="campanas_refresh")
except ImportError:
    pass
```

### n8n jitter delay (Claude's discretion — D-08)
```javascript
// n8n Code node: generate random delay between 3000-8000ms
const delay = Math.floor(Math.random() * 5000) + 3000;
return [{ json: { delay_ms: delay } }];
```

Then pass `{{ $json.delay_ms }}` to a Wait node set to "milliseconds" mode.

### n8n cancellation-safe final UPDATE (SQL in Postgres node)
```sql
UPDATE campaign_log
SET
  status = CASE WHEN status = 'cancelled' THEN 'cancelled' ELSE 'completed' END,
  completed_at = now()
WHERE id = '{{ $('Receive Campaign ID').item.json.body.campaign_id }}'
```

### n8n Evolution API send node (direct, not sub-workflow)
```json
{
  "method": "POST",
  "url": "=http://evolution-api:8080/message/sendText/{{ $env.EVOLUTION_INSTANCE_NAME }}",
  "headers": { "apikey": "={{ $env.EVOLUTION_API_KEY }}" },
  "body": {
    "number": "={{ $json.phone_normalized }}",
    "text": "={{ $json.rendered_message }}"
  }
}
```

### app.py navigation addition (D-02)
```python
# Source: admin-ui/src/app.py — add after knowledge_base line
campanhas = st.Page("pages/7_Campañas.py", title="Campañas", icon=":material/send:")

pg = st.navigation({
    "Principal": [dashboard],
    "CRM": [pacientes, plantillas],
    "Chatbot": [inbox, knowledge_base],
    "Campañas": [campanhas],      # new section
    "Conexion": [whatsapp],
})
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Evolution API v1 (Redis-only session) | Evolution API v2 with Postgres persistence (v2.3.7 pinned) | This project's Phase 2 decision | Session survives container restart |
| n8n HTTP Request typeVersion 4.1 | typeVersion 4.2 (used in sub-send-wa-message.json) | n8n 1.x series | Minor — use 4.2 for consistency with existing workflow |
| n8n Loop node — no break support | IF node + No-Op pattern for cancellation | Always the case | Planner must use conditional check pattern, not assume break exists |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | n8n Loop node does not support early break; cancellation requires IF → No-Op on every remaining item | Architecture Patterns §Pattern 4, Common Pitfalls §Pitfall 1 | Low risk — the No-Op path is fast. If n8n added a break node in a recent version, the planner can simplify the workflow, but the IF-check approach always works. |
| A2 | phone_normalized format in patients table is accepted by Evolution API send endpoint without transformation | Common Pitfalls §Pitfall 5 | Medium risk — if Evolution API requires stripping `+` prefix, the campaign workflow needs a transformation step. Verify with a 1-recipient test send before full blast. |
| A3 | Campaign blast n8n workflow triggered via `POST /webhook/campaign-blast` will receive the webhook body as `$json.body` (not `$json`) | Architecture Patterns §Pattern 4 | Medium risk — n8n webhook node v2 uses `$json.body` for POST body by default when `responseMode: onReceived`. Verify the field path in the workflow trigger node parameters matches actual n8n behavior. Chatbot workflow uses `$json.body.data` for the same reason. |
| A4 | clinic-admin "unhealthy" status is a healthcheck probe issue, not a service failure | Environment Availability | Low risk — container is serving on port 8501. If service were down, new page deployment would need a restart, not a code fix. |

---

## Open Questions

1. **n8n webhook body field path (`$json.body` vs `$json`)**
   - What we know: The chatbot workflow uses `$json.body.data` to access the Evolution API webhook payload. This implies n8n webhook node v2 wraps POST body under `body`.
   - What's unclear: Whether `campaign_id` sent as `{"campaign_id": "uuid"}` is accessed as `$json.body.campaign_id` or `$json.campaign_id` in the campaign workflow.
   - Recommendation: In the n8n workflow JSON, use `$json.body.campaign_id` (consistent with chatbot pattern). If it fails, the executor checks with `$json.campaign_id`. Add a Set node early in the workflow to extract and normalize `campaign_id`.

2. **clinic-admin unhealthy healthcheck**
   - What we know: Container is running and bound to port 8501. Healthcheck is failing.
   - What's unclear: Whether adding `7_Campañas.py` will surface a different issue or the unhealthy state is pre-existing.
   - Recommendation: Document as known pre-existing issue. Not a Phase 5 blocker. Verify by accessing Streamlit UI directly.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL | campaign_log / campaign_recipients DB | ✓ | 16-alpine (clinic-postgres, healthy) | — |
| n8n | campaign-blast workflow trigger | ✓ | latest 1.x (clinic-n8n, healthy) | — |
| Evolution API | WhatsApp send per recipient | ✓ | v2.3.7 (clinic-evolution, healthy) | — |
| Redis | n8n queue backend | ✓ | 7-alpine (clinic-redis, healthy) | — |
| Streamlit | Admin UI | ✓ | >=1.35 (clinic-admin, unhealthy*) | — |
| streamlit-autorefresh | 5s polling in progress view | ✓ | installed in requirements.txt | ImportError fallback already in inbox page |
| requests (Python) | Streamlit → n8n webhook POST | ✓ | installed | — |
| `campaign_log` table | DB persistence for campaigns | ✓ | Defined in 001_schema.sql | — |
| `campaign_recipients` table | Per-recipient tracking | ✓ | Defined in 001_schema.sql | — |
| N8N_WEBHOOK_BASE_URL env var | Streamlit webhook POST URL | ✓ | `http://n8n:5678` set in docker-compose.yml | — |
| EVOLUTION_API_KEY env var | n8n → Evolution API auth | ✓ | Set in both n8n and Evolution API containers | — |
| EVOLUTION_INSTANCE_NAME env var | Evolution API instance name | ✓ | `clinic-main` (default) set in docker-compose.yml | — |

*clinic-admin shows "unhealthy" in docker ps — container is running and serving on port 8501. Healthcheck probe appears misconfigured. Not a blocker for Phase 5 execution.

**Missing dependencies with no fallback:** None — all required services are running.

**Missing dependencies with fallback:** None.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.x |
| Config file | `admin-ui/src/pytest.ini` |
| Quick run command | `docker exec clinic-admin python -m pytest tests/ -x -q` |
| Full suite command | `docker exec clinic-admin python -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WA-02 | `fetch_patients_by_tags` returns correct patients for tag filter | unit | `docker exec clinic-admin python -m pytest tests/test_campaigns.py::TestFetchPatientsByTags -x` | ❌ Wave 0 |
| WA-02 | `insert_campaign_recipients` batch inserts correct count | unit | `docker exec clinic-admin python -m pytest tests/test_campaigns.py::TestInsertCampaignRecipients -x` | ❌ Wave 0 |
| WA-03 | `insert_campaign` creates row with status='pending' | unit | `docker exec clinic-admin python -m pytest tests/test_campaigns.py::TestInsertCampaign -x` | ❌ Wave 0 |
| WA-04 | `cancel_campaign` sets status='cancelled' and cancelled_at | unit | `docker exec clinic-admin python -m pytest tests/test_campaigns.py::TestCancelCampaign -x` | ❌ Wave 0 |
| WA-02 | `fetch_campaign_status` returns correct sent_count/total | unit | `docker exec clinic-admin python -m pytest tests/test_campaigns.py::TestFetchCampaignStatus -x` | ❌ Wave 0 |
| WA-02 | n8n workflow JSON structure — webhook path, loop node present | manual | inspect `n8n/workflows/campaign-blast.json` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `docker exec clinic-admin python -m pytest tests/test_campaigns.py -x -q`
- **Per wave merge:** `docker exec clinic-admin python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `admin-ui/src/tests/test_campaigns.py` — covers WA-02, WA-03, WA-04 DB function unit tests
- [ ] No new pytest.ini or conftest.py needed — existing `admin-ui/src/pytest.ini` covers the test directory

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Admin UI is behind Caddy basic auth (established in Phase 1) |
| V3 Session Management | no | Streamlit session_state is server-side; no JWT/cookie surface in this phase |
| V4 Access Control | no | Single-tenant single-admin; no multi-user access control |
| V5 Input Validation | yes | Tag UUIDs and template UUIDs from user selection must be validated as valid UUIDs before use in SQL parameters. psycopg2 parameterized queries prevent injection; UUID format validation prevents type errors. |
| V6 Cryptography | no | No new secrets or cryptographic operations |

### Known Threat Patterns for Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Mass send without confirmation | Spoofing / DoS on WhatsApp account | Confirmation gate (D-04, WA-03) — no send without explicit admin confirm |
| SQL injection via tag/template selection | Tampering | psycopg2 parameterized queries — `%s` placeholders used throughout database.py [VERIFIED: database.py] |
| n8n webhook called externally (bypassing Streamlit confirmation gate) | Elevation of Privilege | n8n webhook is on internal Docker network (`clinic-net`); not exposed via Caddy. Only Streamlit container can reach it via `http://n8n:5678`. [VERIFIED: docker-compose.yml — n8n port 5678 not published to host] |
| WhatsApp account banning from bulk sends | Availability | Rate limiting with 3-8s jitter per D-08 (WA-02 requirement) |
| Campaign recipients data exposure | Information Disclosure | Admin UI behind Caddy basic auth; patient data not logged to browser console |

---

## Sources

### Primary (HIGH confidence)
- `admin-ui/src/components/database.py` — DB connection pattern, psycopg2 usage, query structure, UUID array parameters
- `admin-ui/src/components/templates.py` — `extract_variables`, `render_preview` functions confirmed
- `admin-ui/src/pages/3_Pacientes.py` — session_state mode toggle pattern, tag multiselect pattern
- `admin-ui/src/pages/4_Plantillas.py` — template dropdown and preview pattern
- `admin-ui/src/pages/5_Inbox.py` — autorefresh polling pattern with ImportError fallback
- `admin-ui/src/app.py` — st.navigation() structure, page registration pattern
- `postgres/init/001_schema.sql` — `campaign_log` and `campaign_recipients` table definitions confirmed
- `n8n/workflows/sub-send-wa-message.json` — Evolution API endpoint, apikey header, field names confirmed
- `docker-compose.yml` — service names, env vars, network topology, Evolution API version, N8N_WEBHOOK_BASE_URL
- `admin-ui/requirements.txt` — installed packages confirmed
- `admin-ui/src/pytest.ini` — test framework config confirmed
- `.planning/phases/05-campaign-blast/05-CONTEXT.md` — all decisions, canonical refs, specifics
- `.planning/phases/05-campaign-blast/05-UI-SPEC.md` — session state variables, component inventory, interaction contract

### Secondary (MEDIUM confidence)
- `docker ps` output — all services running and healthy; Evolution API v2.3.7 confirmed; clinic-admin unhealthy noted

### Tertiary (LOW confidence)
- None — all key claims verified from codebase or running environment.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified in requirements.txt and running containers
- Architecture: HIGH — all patterns verified in existing code; n8n cancellation assumption tagged [ASSUMED]
- Pitfalls: HIGH — derived from verified code patterns; phone format and webhook body path tagged [ASSUMED]

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (stable stack; valid until Evolution API or n8n major version change)
