---
phase: 07-automation-layer-dashboard
reviewed: 2026-04-15T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - n8n/workflows/appointment-reminders.json
  - admin-ui/src/components/database.py
  - admin-ui/src/pages/1_Dashboard.py
  - admin-ui/src/pages/7_Campañas.py
findings:
  critical: 2
  warning: 5
  info: 4
  total: 11
status: issues_found
---

# Phase 7: Code Review Report

**Reviewed:** 2026-04-15
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Four files were reviewed: the appointment-reminders n8n workflow JSON, the shared database helper module, the Dashboard page, and the Campañas (Campaigns) page.

The most serious issues are in the n8n workflow: a hardcoded API key committed directly in the JSON and SQL queries that use the wrong expression syntax (`{{ }}` instead of `={{ }}`), which causes the UPDATE/INSERT statements to inject raw strings into SQL rather than using parameterised bindings. These two issues must be fixed before the workflow is activated in production.

A secondary logic bug silently marks reminders as sent even when the WhatsApp delivery failed, which will permanently suppress retries for affected appointments.

In the Python code the main concerns are: a missing `None` guard on `DATABASE_URL` that produces an opaque crash, a `bot_resolution_pct` query that references a column (`human_handoff`) that likely does not exist in the actual schema (the schema uses a state enum), and a campaign launch path that leaves orphaned records in the DB when the n8n webhook call fails.

---

## Critical Issues

### CR-01: Hardcoded API key in workflow JSON

**File:** `n8n/workflows/appointment-reminders.json:192` (also line 240)
**Issue:** Both `Send 24h WA Reminder` and `Send 1h WA Reminder` nodes embed the Evolution API key as a literal string value `"Jehova01"` inside the workflow JSON. This file is committed to git, so the credential is exposed in version history for anyone with repository access.
**Fix:** Remove the hardcoded value. In n8n, store the credential in the n8n Credentials manager as an HTTP Header Auth credential named `EvolutionAPI`, then reference it via the `credentials` block on the HTTP Request node instead of a hardcoded header parameter. If the header must remain a parameter (because community node does not support it), use an n8n variable (`$vars.EVOLUTION_API_KEY`) configured via the n8n Settings > Variables UI so the value never enters the JSON export.

```json
// Replace the hardcoded header parameter block:
"headerParameters": {
  "parameters": [
    { "name": "apikey", "value": "={{ $vars.EVOLUTION_API_KEY }}" },
    { "name": "Content-Type", "value": "application/json" }
  ]
}
```

Rotate the `Jehova01` key immediately since it is already in git history.

---

### CR-02: Wrong template syntax in SQL queries — raw string injection instead of parameterised values

**File:** `n8n/workflows/appointment-reminders.json:354` (Mark 24h Sent), also lines 373, 390, 408, 426, 444
**Issue:** The `Mark 24h Sent`, `Mark 1h Sent`, `Mark 24h Sent After Failure`, `Mark 1h Sent After Failure`, `Log 24h Failure`, and `Log 1h Failure` Postgres nodes use Mustache-style `{{ ... }}` syntax inside SQL strings:

```sql
WHERE id = '{{ $('Render 24h Message').item.json.appointment_id }}'::uuid
```

In n8n's Postgres `executeQuery` node, bare `{{ }}` is NOT the expression syntax — the correct n8n expression delimiter is `={{ }}`. When n8n evaluates these queries the `{{ }}` blocks may be passed to Postgres as literal text rather than resolved values, which will either silently no-op the UPDATE (no rows matched) or produce a Postgres syntax error. In either case reminders processed through the failure branch will never be marked as sent, causing duplicate sends on subsequent scheduler runs.

Beyond correctness, if the n8n version does evaluate `{{ }}` as expressions in this context, the value is interpolated as a raw string into the SQL — not a parameterised binding — which is a SQL injection vector if `appointment_id` were ever sourced from user-controlled data.

**Fix:** Use n8n's `query parameters` feature for the Postgres node to bind values safely, or at minimum use the correct expression syntax `={{ }}`:

```sql
-- Query field:
UPDATE appointments
SET reminder_24h_sent = true, updated_at = now()
WHERE id = $1::uuid

-- Query parameters field (JSON array):
["={{ $('Render 24h Message').item.json.appointment_id }}"]
```

Apply the same fix to all six affected nodes (Mark 24h Sent, Mark 1h Sent, both After Failure variants, Log 24h Failure, Log 1h Failure).

---

## Warnings

### WR-01: Failed WhatsApp send permanently suppresses future reminder retries

**File:** `n8n/workflows/appointment-reminders.json:419` (Mark 24h Sent After Failure), also line 437
**Issue:** The `Log 24h Failure` node (which fires when the WhatsApp send fails) feeds into `Mark 24h Sent After Failure`, which executes:

```sql
UPDATE appointments SET reminder_24h_sent = true WHERE id = ...
```

This marks the appointment as "reminder sent" even though the message was never successfully delivered. On all subsequent 15-minute scheduler runs the appointment will be excluded from the query (`reminder_24h_sent = false` filter), so the patient receives no reminder at all. The same logic applies to the 1h path.

**Fix:** Do not mark `reminder_Xh_sent = true` on send failure. Remove the `Mark 24h Sent After Failure` and `Mark 1h Sent After Failure` nodes entirely. Let the appointment remain in the query pool so the scheduler retries naturally on the next run. The `workflow_errors` log entry already captures the failure for observability.

---

### WR-02: `get_connection()` passes None to psycopg2 when DATABASE_URL is unset

**File:** `admin-ui/src/components/database.py:11`
**Issue:** `os.environ.get("DATABASE_URL")` returns `None` when the variable is not set. `psycopg2.connect(None)` raises `TypeError: argument 1 must be str, not None` — an opaque error that gives the operator no indication that a required environment variable is missing.

```python
def get_connection():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))
```

**Fix:**

```python
def get_connection():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Check your .env file and Docker Compose service config."
        )
    return psycopg2.connect(url)
```

---

### WR-03: `fetch_dashboard_kpis` queries non-existent column `human_handoff`

**File:** `admin-ui/src/components/database.py:821`
**Issue:** The bot resolution query references `human_handoff` as a boolean column:

```sql
COUNT(*) FILTER (WHERE human_handoff = false) AS bot_resolved
```

However, the project's data model (per the schema conventions and the `fetch_conversations` function at line 449) uses `state` as a varchar/enum column with the value `'human_handoff'`, not a boolean column. If the `conversations` table does not have a `human_handoff` boolean column, this query will raise `psycopg2.errors.UndefinedColumn` at runtime. The Dashboard page's `except Exception` block at line 27 will silently swallow the error and display `bot_resolution_pct: 0.0`, making the KPI appear to work while returning wrong data.

**Fix:** Align the query with the actual schema:

```sql
-- If state is an enum/varchar:
COUNT(*) FILTER (WHERE state != 'human_handoff') AS bot_resolved,
COUNT(*) AS total
FROM conversations
WHERE created_at >= now() - interval '1 day' * %s
```

Verify the actual column definition in `postgres/init/001_schema.sql` and update accordingly.

---

### WR-04: Orphaned campaign record when n8n webhook fails after DB insert

**File:** `admin-ui/src/pages/7_Campañas.py:137-139`
**Issue:** In `_handle_launch_campaign`, the campaign row and all recipient rows are inserted into the database before the n8n webhook is triggered. If `_trigger_n8n_webhook` returns `False`, the code calls `st.error(...)` and `st.stop()`, but the `campaign_log` row already has `status='pending'` and the `campaign_recipients` rows are already committed. The campaign is now stuck in `pending` state permanently — the operator has no automatic way to recover it, and it will show as stuck in the history table.

```python
row = insert_campaign(...)           # committed
insert_campaign_recipients(...)      # committed
...
if not _trigger_n8n_webhook(str(new_id)):
    st.error("Error al iniciar la campaña...")
    st.stop()                        # campaign stuck in DB as 'pending'
```

**Fix:** Cancel the campaign immediately before stopping:

```python
if not _trigger_n8n_webhook(str(new_id)):
    try:
        cancel_campaign(str(new_id))
    except Exception:
        pass
    st.error(
        "Error al iniciar la campaña. Verifica que n8n esté activo e intenta de nuevo. "
        "La campaña fue cancelada automáticamente."
    )
    st.stop()
```

---

### WR-05: Social post image path passed to `save_uploaded_image` may be None at callback time

**File:** `admin-ui/src/pages/7_Campañas.py:116-118`
**Issue:** When the launch button is clicked, `_handle_launch_campaign` reads `st.session_state.campanas_social_image_bytes`. If the user checked `publish_social` but then cleared the file uploader (or if there is a session state timing edge case across reruns), `campanas_social_image_bytes` may be `None`. `save_uploaded_image(None, ...)` is called unconditionally and will likely raise an `AttributeError` or `TypeError` inside that function, leaving the campaign in an ambiguous state (the WA campaign insert may have already succeeded).

The `step3_valid` guard at line 282 is evaluated at render time, but `_handle_launch_campaign` is called in a different execution context (button callback) and re-reads session state independently — the guard does not prevent the code path.

**Fix:** Add an explicit guard inside `_handle_launch_campaign` before calling `save_uploaded_image`:

```python
if st.session_state.get("campanas_publish_social"):
    image_bytes = st.session_state.get("campanas_social_image_bytes")
    image_name = st.session_state.get("campanas_social_image_name") or "image.jpg"
    if not image_bytes:
        st.warning("Imagen del post social no disponible. Se omite la publicación en redes.")
    else:
        try:
            rel_path = save_uploaded_image(image_bytes, image_name)
            ...
```

---

## Info

### IN-01: `SELECT *` in `fetch_knowledge_base`

**File:** `admin-ui/src/components/database.py:373`
**Issue:** Uses `SELECT *` instead of explicit column names. If the `knowledge_base` table schema changes (columns added or reordered), callers may break silently.
**Fix:** Enumerate columns explicitly: `SELECT id, pregunta, respuesta, categoria, is_active, created_at`.

---

### IN-02: Deferred `from datetime import ...` inside conditional block

**File:** `admin-ui/src/pages/1_Dashboard.py:109`
**Issue:** `from datetime import datetime, timezone` is imported inside an `else:` block at module scope. This is unconventional and makes import dependencies non-obvious to readers and tooling.
**Fix:** Move the import to the top of the file with the other imports.

---

### IN-03: Deferred `import pandas as pd` inside `else` block

**File:** `admin-ui/src/pages/7_Campañas.py:419`
**Issue:** `import pandas as pd` appears inside an `else:` block that only runs when `history` is non-empty. This is unconventional; it is already imported at the top of `1_Dashboard.py` and should be at the top of this file as well.
**Fix:** Move `import pandas as pd` to the top of the file.

---

### IN-04: `insert_social_post` calls `conn.commit()` inside the cursor context manager

**File:** `admin-ui/src/components/database.py:722`
**Issue:** Unlike every other function in the module (which call `conn.commit()` after the `with conn.cursor()` block exits), `insert_social_post` calls `conn.commit()` on line 722 inside the `with` block and again implicitly closes in `finally`. This works correctly but is inconsistent with the rest of the module and may confuse future maintainers.
**Fix:** Move `conn.commit()` to after the `with` block closes, matching the established pattern used in all other write functions.

---

_Reviewed: 2026-04-15_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
