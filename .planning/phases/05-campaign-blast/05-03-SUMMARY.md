---
phase: 05-campaign-blast
plan: 03
subsystem: infra
tags: [n8n, whatsapp, evolution-api, postgres, campaign, broadcast]

# Dependency graph
requires:
  - phase: 05-campaign-blast/05-01
    provides: campaign_log and campaign_recipients DB tables and helper functions
  - phase: 05-campaign-blast/05-02
    provides: Streamlit Campanias page that fires the webhook trigger
provides:
  - n8n workflow campaign-blast.json with full webhook->loop->send->update execution engine
  - Rate-limited WhatsApp broadcast (3-8s jitter) via Evolution API
  - Per-iteration cancellation check preserving cancelled status in finalize UPDATE
affects:
  - 05-campaign-blast/05-02 (Streamlit polls campaign_log; n8n writes progress counters)
  - Phase 6 social publishing (pattern: n8n webhook triggered from Streamlit)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "n8n splitInBatches batchSize=1 loop with dual outputs (item / done) for recipient iteration"
    - "Per-iteration DB status check before send to honor mid-flight cancellation"
    - "CASE WHEN status = 'cancelled' THEN 'cancelled' ELSE 'completed' guard in finalize UPDATE"
    - "Random jitter 3000-8000ms using Math.floor(Math.random() * 5000) + 3000 in Code node"
    - "Evolution API credentials via $env.EVOLUTION_API_KEY and $env.EVOLUTION_INSTANCE_NAME (no hardcoded secrets in JSON)"

key-files:
  created:
    - n8n/workflows/campaign-blast.json
  modified: []

key-decisions:
  - "Webhook path campaign-blast only on internal Docker DNS (n8n:5678); Caddy does not expose it publicly (T-05-09)"
  - "continueOnFail=true on send-whatsapp HTTP node so failures route to update-failed branch rather than aborting the loop"
  - "merge-recipient-and-status Code node merges loop-recipients item with check-cancelled result to carry both data and status into is-cancelled IF node"
  - "finalize-status uses CASE WHEN to prevent overwriting cancelled with completed when splitInBatches done fires after a cancellation (RESEARCH Pitfall 3)"

patterns-established:
  - "Pattern: n8n splitInBatches loop with done output -> finalize node (standard campaign pattern)"
  - "Pattern: per-iteration DB status re-check for long-running loops with external cancellation"

requirements-completed: [WA-02, WA-04]

# Metrics
duration: 1min
completed: 2026-04-13
---

# Phase 5 Plan 03: Campaign Blast n8n Workflow Summary

**n8n campaign-blast workflow with 15 nodes: webhook trigger, in_progress mark, pending recipient load, per-iteration cancellation check, 3-8s jitter, Evolution API send, sent/failed status updates, and CASE WHEN finalize guard**

## Performance

- **Duration:** 1 min
- **Started:** 2026-04-13T19:28:12Z
- **Completed:** 2026-04-13T19:29:22Z
- **Tasks:** 1 of 3 auto-executed (Tasks 2 and 3 are human checkpoints — pending operator action)
- **Files modified:** 1

## Accomplishments

- Created `n8n/workflows/campaign-blast.json` with all 15 required nodes and correct kebab-case ids
- All 18 acceptance criteria verified: valid JSON, correct node types/versions, all SQL fragments, all node ids present
- Evolution API key and instance name referenced via `$env.*` expressions — no secrets in JSON (T-05-13 mitigated)

## Task Commits

1. **Task 1: Author campaign-blast.json with full webhook->loop->send->update flow** - `60557ae` (feat)

Tasks 2 and 3 are `checkpoint:human-action` and `checkpoint:human-verify` requiring operator action. They are documented below under Pending Human Checkpoints.

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `n8n/workflows/campaign-blast.json` - n8n workflow: webhook trigger at `campaign-blast`, marks campaign `in_progress`, loads pending recipients, iterates with 3-8s jitter, sends via Evolution API, updates per-recipient status, CASE WHEN finalizes without overwriting `cancelled`

## Decisions Made

- `continueOnFail=true` on the `send-whatsapp` HTTP Request node so failed sends route to `update-failed` branch rather than aborting the entire loop
- `merge-recipient-and-status` Code node (runOnceForEachItem) spreads both the loop recipient data and the `check-cancelled` status row into a single item so the downstream IF node has both fields available
- Connections use node names (not ids) in the `connections` object — this matches n8n's standard JSON schema where connection keys are the node `name` field, not the `id` field

## Deviations from Plan

None — plan executed exactly as written. All 16 required node ids present, all SQL guards in place, all env var references correct.

## Issues Encountered

None — JSON validated on first attempt, all acceptance criteria passed immediately.

## Pending Human Checkpoints

### Task 2: Import campaign-blast workflow into n8n and activate

**Type:** checkpoint:human-action  
**What to do:**
1. Open the n8n UI behind Caddy.
2. Workflows -> Import from File -> select `n8n/workflows/campaign-blast.json`.
3. Verify the Postgres credential `PostgreSQL` auto-binds on all Postgres nodes (id `postgres-credential`).
4. Click the Active toggle to activate the workflow.
5. Verify the webhook URL shows as `https://<n8n-host>/webhook/campaign-blast`.
6. Test: `curl -X POST http://localhost:5678/webhook/campaign-blast -H 'Content-Type: application/json' -d '{"campaign_id":"00000000-0000-0000-0000-000000000000"}'` — expect 200.
7. In n8n executions, verify flow ran: webhook -> extract-campaign-id -> mark-in-progress (fails at mark-in-progress because UUID doesn't exist — expected).

**Resume signal:** Type "imported" once active, or describe the import error.

### Task 3: End-to-end small broadcast test (3 recipients) + cancellation test

**Type:** checkpoint:human-verify  
**Prerequisites:** Task 2 complete; at least 3 test patients tagged "test" with owned phone numbers; at least one active message template.

**Test A — Successful blast:**
1. Open Campanas page, select "test" tag (3 recipients), select test template.
2. Confirm send. Watch progress bar update to 3/3 over ~10-30s.
3. Verify test phones received the message.
4. DB check: all three `campaign_recipients` rows have `status='sent'` and `wa_message_id` populated.

**Test B — Cancellation:**
1. Run another blast to the same 3 recipients.
2. After first send (~5s), click "Cancelar campaña".
3. Verify `campaign_log.status = 'cancelled'` (NOT 'completed'); remaining recipients stay `status='pending'`.
4. Verify fewer than 3 messages received.

**Resume signal:** Type "approved" or describe issues.

## Threat Surface Scan

No new network endpoints or auth paths introduced beyond what the plan's threat model covers. All threats T-05-09 through T-05-14 are mitigated or accepted as documented in the plan.

## Next Phase Readiness

- `campaign-blast.json` is committed and ready for n8n import (Task 2 operator action)
- Once Tasks 2 and 3 pass, Phase 5 campaign blast feature is fully complete
- Phase 6 social publishing can reference this webhook-trigger-from-Streamlit pattern

## Self-Check

- `n8n/workflows/campaign-blast.json` — FOUND (committed at 60557ae)
- JSON valid — PASS (python3 -m json.tool exits 0)
- All 15 node ids present — PASS
- All 18 acceptance criteria — PASS

## Self-Check: PASSED

---
*Phase: 05-campaign-blast*
*Completed: 2026-04-13*
