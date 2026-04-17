---
type: quick
task_id: 260417-ied
title: Fix CR-01, CR-02, WR-03 in appointment-reminders workflow and database.py
status: complete
completed_at: "2026-04-17T19:19:35Z"
duration_minutes: 2
tags:
  - phase-07
  - verification-followup
  - security
  - n8n
  - dashboard
source: .planning/phases/07-automation-layer-dashboard/07-VERIFICATION.md
key-files:
  modified:
    - n8n/workflows/appointment-reminders.json
    - admin-ui/src/components/database.py
  created: []
commits:
  - 2f10c9f: "fix(quick-260417-ied): replace hardcoded Evolution API key with env expression (CR-01)"
  - 49c2bb0: "fix(quick-260417-ied): prefix six Postgres query strings with = so n8n evaluates expressions (CR-02)"
  - 810b7f7: "fix(quick-260417-ied): use conversations.state enum for bot resolution KPI (WR-03)"
requires:
  - EVOLUTION_API_KEY env var injected into the n8n container
  - conversations table with `state TEXT` column (Phase 4 schema)
provides:
  - appointment-reminders workflow with env-var API key and correct n8n expression syntax in all six executeQuery nodes
  - fetch_dashboard_kpis with schema-correct bot_resolution_pct query
decisions:
  - "Used '=' prefix (not full rewrite to executeQueryReplacement) to keep the diff minimal; query text is otherwise unchanged."
  - "Applied '=' prefix ONLY to the six nodes that contain {{ }} expressions; the four static-SQL queries (Fetch Reminder Template, Log No Template Error, Query 24h Appointments, Query 1h Appointments) correctly remain without the prefix."
  - "Used `state != 'human_handoff'` verbatim per WR-03 reviewer recommendation rather than also excluding 'closed' — kept the fix minimal and matches the review text exactly."
---

# Quick Task 260417-ied: Fix CR-01, CR-02, WR-03 in appointment-reminders workflow and database.py Summary

Resolved three Phase 7 verification findings by removing the hardcoded Evolution API key from the n8n appointment-reminders workflow (CR-01), fixing n8n expression syntax in six Postgres executeQuery nodes so SQL placeholders actually resolve at runtime (CR-02), and correcting the dashboard `bot_resolution_pct` KPI to query the real `conversations.state` enum instead of a non-existent `human_handoff` boolean column (WR-03).

## Files Changed

### `n8n/workflows/appointment-reminders.json`

**CR-01 (lines 192 and 241)** — Replaced literal `"Jehova01"` apikey header value with the n8n expression `"={{ $env.EVOLUTION_API_KEY }}"` in both HTTP Request nodes (`Send 24h WA Reminder`, `Send 1h WA Reminder`).

**CR-02 (six query positions)** — Prefixed the `query` string with a single leading `=` so n8n evaluates the embedded `{{ ... }}` expressions before sending to Postgres:

| Node | Approx line | Statement |
|------|-------------|-----------|
| `Mark 24h Sent` | 354 | `UPDATE appointments SET reminder_24h_sent = true ...` |
| `Mark 1h Sent` | 372 | `UPDATE appointments SET reminder_1h_sent = true ...` |
| `Log 24h Failure` | 390 | `INSERT INTO workflow_errors ... 24h ...` |
| `Log 1h Failure` | 408 | `INSERT INTO workflow_errors ... 1h ...` |
| `Mark 24h Sent After Failure` | 426 | `UPDATE appointments SET reminder_24h_sent = true ...` |
| `Mark 1h Sent After Failure` | 444 | `UPDATE appointments SET reminder_1h_sent = true ...` |

The four static-SQL Postgres nodes (`Fetch Reminder Template`, `Log No Template Error`, `Query 24h Appointments`, `Query 1h Appointments`) contain no `{{ }}` expressions and are correctly left without the `=` prefix.

### `admin-ui/src/components/database.py`

**WR-03 (`fetch_dashboard_kpis`, line ~823)** — Changed the bot-resolution predicate from `WHERE human_handoff = false` to `WHERE state != 'human_handoff'` so the query matches the real schema (`conversations.state TEXT` enum). Function signature (`days: int -> dict`), row unpacking, zero-division guard, and the other four KPI queries are unchanged.

## Verification Commands Run

All commands from the plan's `<verification>` block pass:

```
== 1. JSON validity ==
JSON: OK
== 2. Python syntax ==
Python: OK
== 3. No hardcoded key (expect 0) ==
Jehova01 count: 0
== 4. Env var expression count (expect 2) ==
env expr count: 2
== 5. All six executeQuery queries prefixed ==
All six OK
== 6. WR-03 predicate swap ==
WR-03 OK
```

## Deviations from Plan

None — plan executed exactly as written.

## Outstanding Human Actions

1. **CR-01 — rotate the leaked API key (REQUIRED).**
   The literal `Jehova01` is still in git history (and was in the workflow JSON
   until commit `2f10c9f`). Removing it from the working tree does **not**
   close the exposure. The clinic administrator must:
   - Regenerate / rotate the Evolution API global API key via the Evolution
     admin panel (or by resetting `AUTHENTICATION_API_KEY` in the Evolution
     container env and restarting it).
   - Set the new value in `EVOLUTION_API_KEY` in the production `.env` and
     ensure it is injected into the n8n container (Docker Compose `environment:`
     for the n8n service) so `={{ $env.EVOLUTION_API_KEY }}` resolves at runtime.
   - Confirm any other integrations that used `Jehova01` are also updated.

2. **CR-02 — re-import and manually execute the updated workflow (recommended).**
   Import `n8n/workflows/appointment-reminders.json` into n8n and run
   "Execute Workflow" (do not activate yet) with a seeded appointment. Confirm:
   - The six Postgres executeQuery nodes no longer fail silently.
   - `UPDATE appointments SET reminder_*_sent = true ... WHERE id = '<uuid>'::uuid`
     matches and updates exactly one row.
   - `workflow_errors` rows (on the failure path) contain the resolved
     appointment_id/phone values — not the literal `{{ ... }}` text.

3. **CR-02 — verify `EVOLUTION_API_KEY` is in the n8n container environment.**
   The expression `$env.EVOLUTION_API_KEY` reads from the n8n Node.js process
   environment. If it is only in the Evolution container's env (not n8n's), the
   HTTP requests will be sent with an empty `apikey` header. Check
   `docker compose exec clinic-n8n printenv | grep EVOLUTION_API_KEY` before
   activating the workflow.

## Out of Scope (Intentionally Deferred)

The following Phase 7 verification findings remain open in
`.planning/phases/07-automation-layer-dashboard/07-VERIFICATION.md` and
`07-REVIEW.md`:

- **WR-01** — `Mark Sent After Failure` still flips `reminder_*_sent = true`
  on the delivery-failure branch, which causes permanently-missed reminders
  to be treated as sent. Requires a design decision (swap to a retry counter,
  or remove the failure-branch updates).
- **WR-02** — `DATABASE_URL` `None` guard in `admin-ui/src/components/database.py`.
- **WR-04 / WR-05** — additional warnings from the review.
- **All IN-xx items** — informational findings from 07-REVIEW.md.

These were explicitly excluded by the plan's scope (quick fix targeting only
CR-01, CR-02, and WR-03) and were not modified.

## Self-Check: PASSED

- `n8n/workflows/appointment-reminders.json` — FOUND, parses as JSON, zero `Jehova01` occurrences, 2 `={{ $env.EVOLUTION_API_KEY }}` occurrences, all six target executeQuery queries start with `=`.
- `admin-ui/src/components/database.py` — FOUND, parses via `ast.parse` and `py_compile`, `human_handoff = false` absent, `state != 'human_handoff'` present in `fetch_dashboard_kpis`.
- Commit `2f10c9f` (CR-01) — FOUND in `git log`.
- Commit `49c2bb0` (CR-02) — FOUND in `git log`.
- Commit `810b7f7` (WR-03) — FOUND in `git log`.
