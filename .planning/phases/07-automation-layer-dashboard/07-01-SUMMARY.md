---
phase: "07"
plan: "01"
subsystem: n8n-workflows
tags: [automation, appointments, reminders, whatsapp, n8n]
dependency_graph:
  requires:
    - postgres/init/001_schema.sql (appointments, message_templates, workflow_errors tables)
    - n8n/workflows/sub-send-wa-message.json (referenced pattern)
  provides:
    - n8n/workflows/appointment-reminders.json
  affects:
    - appointments table (reminder_24h_sent, reminder_1h_sent flags)
    - workflow_errors table (failure logging)
tech_stack:
  added: []
  patterns:
    - n8n scheduleTrigger every 15 min
    - splitInBatches loop with noOp back-edge for iteration
    - continueOnFail + statusCode If-check for retry/failure branching
    - Intl.DateTimeFormat es-MX for Spanish date/time formatting
key_files:
  created:
    - n8n/workflows/appointment-reminders.json
  modified: []
decisions:
  - Used httpRequest with continueOnFail+retryOnFail instead of executeWorkflow sub-workflow call because sub-send-wa-message.json uses different field names (remote_jid, response_text) than what reminders need (phone, rendered_message) — direct HTTP call avoids impedance mismatch
  - Loop back-edge uses noOp nodes (Loop 24h Back / Loop 1h Back) pointing back to splitInBatches to complete the iteration cycle correctly in n8n v1 execution order
  - Failure path uses If node checking statusCode (200-299) after continueOnFail=true, matching campaign-blast.json pattern for consistent error handling
metrics:
  duration: "~2 min"
  completed_date: "2026-04-15"
  tasks_completed: 13
  files_created: 1
  files_modified: 0
---

# Phase 07 Plan 01: n8n Appointment Reminders Workflow Summary

**One-liner:** Cron workflow every 15 min that detects 24h/1h appointment windows, renders Spanish-formatted WhatsApp reminders from the `recordatorio` template, sends via Evolution API with retry, and marks idempotency flags to prevent duplicate sends.

## What Was Built

`n8n/workflows/appointment-reminders.json` — a complete n8n workflow with 22 nodes implementing the full appointment reminder automation:

1. **Schedule Trigger** — fires every 15 minutes
2. **Fetch Reminder Template** — single shared query for `category='recordatorio'` template
3. **Template Exists?** — If-guard; logs to `workflow_errors` and stops if no active template found
4. **Query 24h Appointments / Query 1h Appointments** — parallel branches with idempotency guards (`reminder_24h_sent = false` / `reminder_1h_sent = false`) and time windows per D-05
5. **Loop 24h Items / Loop 1h Items** — `splitInBatches` (batchSize=1) for per-appointment processing
6. **Render 24h Message / Render 1h Message** — Code nodes using `Intl.DateTimeFormat('es-MX')` with `America/Mexico_City` timezone, rendering `{{nombre}}`, `{{tipo}}`, `{{fecha}}`, `{{hora}}` variables
7. **Send 24h WA Reminder / Send 1h WA Reminder** — HTTP POST to Evolution API with `retryOnFail: true`, `maxTries: 2`, `waitBetweenTries: 30000ms`, `continueOnFail: true`
8. **24h/1h Send Success?** — If nodes checking statusCode 200-299
9. **Mark 24h/1h Sent** — UPDATE appointments set flag=true on success
10. **Log 24h/1h Failure** — INSERT into `workflow_errors` on failure
11. **Mark 24h/1h Sent After Failure** — UPDATE flag=true even on failure (prevents infinite retries per D-04)
12. **Loop 24h/1h Back** — noOp nodes that route back to splitInBatches to complete iteration

## Verification Results

All checklist items passed:
- JSON syntactically valid (python3 json.load)
- 22 unique node UUIDs
- All connection source/target names match node names
- Schedule: every 15 minutes
- 24h query window: NOW()+23h45m to NOW()+24h15m
- 1h query window: NOW()+45min to NOW()+1h15min
- Both idempotency guards present
- All 4 template variables rendered
- Fecha in Spanish format, hora in 12h format
- retryOnFail=true, maxTries=2, waitBetweenTries=30000
- Failure path logs + marks sent=true
- No-template guard present and logs to workflow_errors
- workflow active=false

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Design] Used direct HTTP call instead of executeWorkflow sub-workflow**
- **Found during:** Task 7 implementation
- **Issue:** `sub-send-wa-message.json` expects fields `remote_jid` and `response_text`, but reminder context provides `phone` and `rendered_message`. Using executeWorkflow would require either modifying the sub-workflow (forbidden by plan) or adding an extra mapping node.
- **Fix:** Implemented direct `httpRequest` to Evolution API (same endpoint/auth as the sub-workflow) with the correct field names, matching the campaign-blast.json pattern.
- **Files modified:** n8n/workflows/appointment-reminders.json
- **Commit:** 3f56ac1

**2. [Rule 2 - Missing] Added 24h/1h Send Success? If nodes**
- **Found during:** Task 7/11 implementation
- **Issue:** Plan specified `retryOnFail` for the send node, but with `continueOnFail=true` the workflow needs an explicit success check to route to the correct path (mark-sent vs. log-failure). Without it there's no failure branch.
- **Fix:** Added If nodes checking statusCode 200-299 after each send, identical to campaign-blast.json pattern.
- **Files modified:** n8n/workflows/appointment-reminders.json
- **Commit:** 3f56ac1

## Known Stubs

None. The workflow is fully wired. The admin must create a `message_templates` row with `category='recordatorio'` from the existing Plantillas UI page before activation.

## Threat Flags

None. No new network endpoints or auth paths introduced. The workflow uses the existing postgres-credential and Evolution API internal Docker network endpoint already present in campaign-blast.json.

## Self-Check: PASSED

- [x] `n8n/workflows/appointment-reminders.json` exists: FOUND
- [x] Commit 3f56ac1 exists in git log
- [x] JSON valid (python3 validation passed)
- [x] All 22 node IDs unique
- [x] All connection targets resolve to node names
