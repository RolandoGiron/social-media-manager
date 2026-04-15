---
phase: 07-automation-layer-dashboard
verified: 2026-04-15T06:00:00Z
status: human_needed
score: 3/4
overrides_applied: 0
human_verification:
  - test: "Start Docker stack and verify Dashboard page renders correctly"
    expected: "4 KPI cards in a single row, 7-day activity chart, workflow error log — no Python tracebacks or Streamlit red error boxes"
    why_human: "Requires running Docker stack and browser access; automated executor cannot run docker compose up"
  - test: "Verify 7_Campanas.py analytics section renders after history table"
    expected: "Section header 'Analisis de entrega por campana' visible; no tracebacks; 'Sin campanas completadas' is acceptable on empty DB"
    why_human: "Requires running Docker stack and browser access"
  - test: "Import appointment-reminders.json into n8n and execute manually"
    expected: "Workflow imports without errors, all nodes connected, workflow stays inactive, manual execution produces no node errors (empty results on empty DB are OK)"
    why_human: "Requires running n8n UI and browser access; cannot be verified statically"
  - test: "Confirm bot_resolution_pct KPI produces correct data vs schema"
    expected: "Dashboard KPI does not silently return 0.0 due to UndefinedColumn error on human_handoff column (WR-03 must be resolved first)"
    why_human: "Requires live DB to confirm whether conversations table has human_handoff boolean or uses state enum — determines if KPI silently fails"
open_issues:
  - id: CR-01
    severity: critical
    file: "n8n/workflows/appointment-reminders.json"
    lines: "192, 241"
    description: "Hardcoded API key 'Jehova01' committed to git. Must rotate key and replace with n8n credential reference or $vars.EVOLUTION_API_KEY before activation."
  - id: CR-02
    severity: critical
    file: "n8n/workflows/appointment-reminders.json"
    lines: "354, 372, 390, 408, 426, 444"
    description: "Six Postgres nodes use {{ }} Mustache syntax instead of n8n's ={{ }} expression syntax for SQL interpolation. UPDATE/INSERT statements likely no-op or produce syntax errors at runtime. Fix required before activation."
  - id: WR-03
    severity: warning
    file: "admin-ui/src/components/database.py"
    line: 823
    description: "fetch_dashboard_kpis queries human_handoff as a boolean column but schema likely uses state enum. Will silently return bot_resolution_pct=0.0 due to except block swallowing psycopg2.errors.UndefinedColumn."
---

# Phase 7: Automation Layer + Dashboard — Verification Report

**Phase Goal:** Appointment reminders run automatically, the admin has a metrics dashboard showing system health and campaign performance, and campaign delivery analytics are visible per segment
**Verified:** 2026-04-15T06:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC-1 | Patient receives WhatsApp reminder automatically 24h and 1h before appointment, without admin action | VERIFIED (code-level) | `n8n/workflows/appointment-reminders.json` exists: 22 nodes, active=false, Schedule Trigger every 15m, 24h/1h query windows with idempotency guards. CRITICAL blockers (CR-01, CR-02) prevent production activation but the workflow logic is complete. Human verification of n8n import + execution still required (SC-1 human checkpoint). |
| SC-2 | Admin can view dashboard with messages sent, bot resolution %, appointments booked, posts published | VERIFIED (code-level) | `1_Dashboard.py` is 139 lines (not a stub). Imports and calls `fetch_dashboard_kpis`, `fetch_activity_chart_data`. 4 KPI cards in `st.columns(4)` with help tooltips. WR-03 (human_handoff column mismatch) may cause bot_resolution_pct to silently return 0.0. Browser smoke test still required. |
| SC-3 | Admin can see per-segment delivery metrics: recipients received and read the campaign | VERIFIED (code-level) | `7_Campanas.py` appended with analytics section (lines 434–487). `fetch_campaign_delivery_analytics` imported at line 13 and called at line 442. Funnel progress bars with zero-division guard and st.progress clamping confirmed. Browser smoke test still required. |
| SC-4 | Admin can view n8n workflow error log from admin UI without accessing n8n directly | VERIFIED (code-level) | `fetch_workflow_errors` added to `database.py` (line 910). `1_Dashboard.py` imports and renders it as `st.dataframe` with relative-time "Hace" column. Read-only display confirmed. Browser smoke test still required. |

**Score:** 3/4 truths verified at code level (SC-1 has critical blockers; all 4 need browser confirmation)

---

### Deferred Items

None — all four success criteria are addressed in this phase.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `n8n/workflows/appointment-reminders.json` | n8n workflow, 22 nodes, active=false, Schedule Trigger every 15m | VERIFIED | 22 unique node UUIDs, all connections resolve, active=false, minutesInterval=15. Commits 3f56ac1 confirmed. |
| `admin-ui/src/components/database.py` (fetch_dashboard_kpis) | Returns 4-key KPI dict | VERIFIED | Defined at line 799, substantive (50+ lines), wired via import in 1_Dashboard.py |
| `admin-ui/src/components/database.py` (fetch_activity_chart_data) | Returns daily series list with date/messages_sent/appointments | VERIFIED | Defined at line 867, uses generate_series for gap-filling, wired in 1_Dashboard.py |
| `admin-ui/src/components/database.py` (fetch_workflow_errors) | Returns recent workflow_errors rows | VERIFIED | Defined at line 910, wired in 1_Dashboard.py |
| `admin-ui/src/components/database.py` (fetch_campaign_delivery_analytics) | Returns per-campaign delivery funnel | VERIFIED | Defined at line 937, LEFT JOIN confirmed, cumulative funnel logic confirmed. Commits 95c6851 confirmed. |
| `admin-ui/src/pages/1_Dashboard.py` | Full dashboard (139+ lines, not stub) | VERIFIED | 139 lines confirmed. KPI cards, line chart, error log all present. |
| `admin-ui/src/pages/7_Campanas.py` analytics section | Section "Analisis de entrega por campana" after history table | VERIFIED | Section header at line 438, import at line 13, usage at line 442. Commit dce736a confirmed. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `1_Dashboard.py` | `database.fetch_dashboard_kpis` | import at line 12 + call at line 26 | WIRED | Function imported and called with try/except |
| `1_Dashboard.py` | `database.fetch_activity_chart_data` | import at line 12 + call at line 76 | WIRED | Function imported and called |
| `1_Dashboard.py` | `database.fetch_workflow_errors` | import at line 12 + call at line 101 | WIRED | Function imported and called |
| `7_Campanas.py` | `database.fetch_campaign_delivery_analytics` | import at line 13 + call at line 442 | WIRED | Function imported alphabetically with Phase 7 comment, called in analytics section |
| `appointment-reminders.json` Schedule Trigger | Fetch Reminder Template → query branches → send nodes | JSON connections object | WIRED | All 22 node connections resolve cleanly, no orphaned nodes |
| n8n workflow send nodes | Evolution API (HTTP POST) | hardcoded API key (CR-01) | PARTIAL — BLOCKED | HTTP call is wired but credential is a plaintext hardcoded key, not a managed n8n credential |
| n8n Postgres UPDATE/INSERT nodes | appointments table | Mustache {{ }} syntax (CR-02) | PARTIAL — BROKEN | SQL uses {{ }} not ={{ }} — expressions will not be evaluated correctly, UPDATEs will likely no-op |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `1_Dashboard.py` | `kpis` dict | `fetch_dashboard_kpis` → PostgreSQL queries on messages/conversations/appointments/social_posts | Yes (live DB queries) | FLOWING — but WR-03: bot_resolution_pct query uses `human_handoff = false` column that may not exist; silently falls back to 0.0 on error |
| `1_Dashboard.py` | `chart_rows` | `fetch_activity_chart_data` → generate_series LEFT JOIN on messages/appointments | Yes (live DB with gap fill) | FLOWING |
| `1_Dashboard.py` | `errors` list | `fetch_workflow_errors` → workflow_errors table ORDER BY created_at DESC | Yes (live DB query) | FLOWING |
| `7_Campanas.py` | `analytics` list | `fetch_campaign_delivery_analytics` → campaign_log LEFT JOIN campaign_recipients | Yes (live DB query, cumulative funnel) | FLOWING |

---

### Behavioral Spot-Checks

Step 7b: SKIPPED — no runnable entry points without a live Docker stack. All checks require database connectivity or n8n UI.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CAL-03 | 07-01-PLAN.md | System sends automatic WhatsApp reminders 24h and 1h before appointment | SATISFIED (code) | appointment-reminders.json implements full reminder logic with idempotency, retry, and failure logging. Critical bugs (CR-01, CR-02) must be fixed before production activation. |
| DASH-01 | 07-02-PLAN.md | Admin can view key metrics: messages sent, bot resolution %, appointments booked, posts published | SATISFIED (code) | fetch_dashboard_kpis + 1_Dashboard.py KPI cards. WR-03 risk on bot_resolution_pct. |
| DASH-02 | 07-03-PLAN.md | Admin can view delivery metrics per segment: received and read counts | SATISFIED (code) | fetch_campaign_delivery_analytics + analytics section in 7_Campanas.py |
| DASH-03 | 07-02-PLAN.md | Admin can view n8n workflow error log for operational diagnosis | SATISFIED (code) | fetch_workflow_errors + error log table in 1_Dashboard.py |

---

### Anti-Patterns Found

| File | Line(s) | Pattern | Severity | Impact |
|------|---------|---------|----------|--------|
| `n8n/workflows/appointment-reminders.json` | 192, 241 | Hardcoded API key "Jehova01" in committed JSON | BLOCKER (CR-01) | Security: credential exposed in git history. Workflow cannot be safely activated in production. Key must be rotated immediately. |
| `n8n/workflows/appointment-reminders.json` | 354, 372, 390, 408, 426, 444 | `{{ }}` Mustache syntax in n8n Postgres executeQuery nodes instead of `={{ }}` | BLOCKER (CR-02) | Correctness: appointment UPDATE statements will likely not match any rows (wrong expression evaluation), causing reminder flags to never be set and/or INSERT to fail. Infinite retry risk on next scheduler run. |
| `admin-ui/src/components/database.py` | 823 | `human_handoff = false` queries a column that is likely an enum value in the state field, not a boolean column | WARNING (WR-03) | Silent data error: `psycopg2.errors.UndefinedColumn` swallowed by try/except → bot_resolution_pct always reports 0.0 |
| `admin-ui/src/components/database.py` | 11 | `os.environ.get("DATABASE_URL")` passes None to psycopg2 when env var unset | WARNING (WR-02) | Opaque crash: `TypeError: argument 1 must be str, not None` with no indication of root cause |
| `n8n/workflows/appointment-reminders.json` | 419, 437 | Mark reminder as sent even on WhatsApp delivery failure | WARNING (WR-01) | Operational: patients miss reminders permanently after a send failure; reminder can never be retried once flag is set to true |
| `admin-ui/src/pages/1_Dashboard.py` | 109 | `from datetime import datetime, timezone` inside `else:` block | INFO (IN-02) | Style: deferred import is unconventional; no runtime impact |
| `admin-ui/src/pages/7_Campanas.py` | 419 | `import pandas as pd` inside `else:` block | INFO (IN-03) | Style: deferred import; no runtime impact |

---

### Human Verification Required

The following items require a running Docker stack and browser access. The automated executor cannot complete these.

#### 1. Dashboard Smoke Test

**Test:** Start the stack with `docker compose up -d`, open Streamlit admin UI, navigate to Dashboard page.
**Expected:**
- 4 KPI cards visible in a single row (values may be 0 on empty DB)
- 7-day activity line chart renders without error
- Workflow error log section visible ("Sin errores recientes" is acceptable)
- No Python tracebacks or red Streamlit error boxes in the browser
**Why human:** Requires running Docker stack and browser. Programmatic import check cannot confirm Streamlit rendering.

#### 2. Campaign Analytics Section Smoke Test

**Test:** On running stack, navigate to Campanas page (7_Campanas.py), scroll past the history table.
**Expected:**
- "Analisis de entrega por campana" section header visible
- No Python tracebacks
- "Sin campanas completadas en los ultimos 30 dias" is acceptable on empty DB
**Why human:** Requires running Docker stack and browser.

#### 3. Appointment Reminders Workflow — n8n Import and Execution Test

**Test:** Open n8n UI, import `n8n/workflows/appointment-reminders.json` via Workflows > Import from File. Manually execute via "Execute Workflow" button (do NOT activate).
**Expected:**
- Workflow imports without parse errors
- All 22 nodes appear connected in the canvas (no orphaned nodes)
- Workflow status shows as Inactive
- Manual execution completes without red node errors (empty appointment result is OK)
- NOTE: CR-01 and CR-02 must be fixed before this test is meaningful. Recommend fixing critical issues first, then re-importing.
**Why human:** Requires running n8n UI and browser. Static JSON validation does not confirm n8n's runtime expression evaluation.

#### 4. bot_resolution_pct Column Verification

**Test:** Check `postgres/init/001_schema.sql` for the `conversations` table definition; confirm whether `human_handoff` is a boolean column or if the correct column is `state` (enum/varchar).
**Expected:** If the schema uses `state != 'human_handoff'`, update `fetch_dashboard_kpis` at database.py line 823 before running the stack — otherwise the KPI silently returns 0.0.
**Why human:** Requires reviewing the schema file and potentially modifying `database.py` before the smoke test produces valid data.

---

### Critical Issues — Must Fix Before Activation

Both critical issues (CR-01, CR-02) are documented in `07-REVIEW.md` and must be resolved before the appointment-reminders workflow is activated in n8n. The Streamlit dashboard components (Plans 07-02, 07-03) are not blocked by these issues and can be browser-tested independently.

**CR-01 — Rotate API Key Immediately:** The Evolution API key "Jehova01" is now in git history. Even after fixing the workflow JSON, the key must be rotated in the Evolution API admin panel to eliminate the exposure window.

**CR-02 — Fix Expression Syntax in 6 Postgres Nodes:** Replace `{{ expression }}` with `={{ expression }}` (or use parameterised query bindings) in: Mark 24h Sent (line 354), Mark 1h Sent (line 372), Log 24h Failure (line 390), Log 1h Failure (line 408), Mark 24h Sent After Failure (line 426), Mark 1h Sent After Failure (line 444).

---

### Gaps Summary

No structural gaps — all four artifacts exist, are substantive, and are wired to their consumers. The phase goal is achievable once two blocking issues in the n8n workflow are fixed and human browser verification is completed.

The 4/4 roadmap success criteria have code-level implementations. The `human_needed` status reflects that:
1. Automated executor could not run the Docker stack / browser smoke tests (documented in 07-03-SUMMARY.md as expected)
2. Two critical security/correctness bugs in the n8n workflow (CR-01, CR-02) must be patched before SC-1 can be considered fully satisfied

---

_Verified: 2026-04-15T06:00:00Z_
_Verifier: Claude (gsd-verifier)_
