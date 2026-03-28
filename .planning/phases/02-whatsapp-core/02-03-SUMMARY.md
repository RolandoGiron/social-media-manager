---
phase: 02-whatsapp-core
plan: 03
subsystem: infra
tags: [n8n, whatsapp, evolution-api, webhooks, workflows]

# Dependency graph
requires:
  - phase: 02-whatsapp-core/01
    provides: "Docker Compose stack with Evolution API, n8n, and webhook routing config"
provides:
  - "n8n workflow for CONNECTION_UPDATE webhook handling with admin WhatsApp alert"
  - "n8n workflow stub for MESSAGES_UPSERT webhook (placeholder for Phase 4 chatbot)"
  - "Evolution API env vars exposed to n8n container"
affects: [04-chatbot-ai, 02-whatsapp-core]

# Tech tracking
tech-stack:
  added: []
  patterns: [n8n-workflow-json-export, webhook-event-routing-by-suffix, env-var-driven-config]

key-files:
  created:
    - n8n/workflows/whatsapp-connection-update.json
    - n8n/workflows/whatsapp-message-stub.json
  modified:
    - docker-compose.yml

key-decisions:
  - "Alert fires once per event with no retry -- if clinic number is disconnected, alert fails silently (per D-08, D-09)"
  - "Message stub uses NoOp node as placeholder -- Phase 4 replaces with chatbot routing"

patterns-established:
  - "n8n workflow JSON export pattern: workflows stored in n8n/workflows/ for version control and import"
  - "Webhook path convention: whatsapp-inbound/{event-name-lowercase} matching Evolution API WEBHOOK_BY_EVENTS routing"

requirements-completed: [INFRA-03]

# Metrics
duration: 5min
completed: 2026-03-28
---

# Phase 02 Plan 03: n8n WhatsApp Workflows Summary

**n8n workflows for Evolution API webhook handling: disconnect alert to admin via WhatsApp and message-upsert stub for Phase 4 chatbot**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-28T11:06:00Z
- **Completed:** 2026-03-28T11:11:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Connection-update workflow receives CONNECTION_UPDATE webhooks, detects disconnect (state=close/connecting), and sends WhatsApp alert to admin with timestamp and QR reconnection link
- Message-stub workflow accepts MESSAGES_UPSERT webhooks silently, preventing Evolution API errors on message events
- Evolution API env vars (EVOLUTION_API_KEY, EVOLUTION_INSTANCE_NAME, ADMIN_WHATSAPP_NUMBER, DOMAIN, ADMIN_SUBDOMAIN) added to n8n service in docker-compose.yml

## Task Commits

Each task was committed atomically:

1. **Task 1: Create n8n workflow JSONs for connection-update and message-stub** - `0eb3952` (feat)
2. **Task 2: Verify n8n workflows** - checkpoint:human-verify (approved by user, no separate commit)

## Files Created/Modified
- `n8n/workflows/whatsapp-connection-update.json` - n8n workflow: Webhook -> IF (disconnect?) -> HTTP Request (send WhatsApp alert to admin)
- `n8n/workflows/whatsapp-message-stub.json` - n8n workflow: Webhook -> NoOp (placeholder for Phase 4 chatbot)
- `docker-compose.yml` - Added Evolution API env vars to n8n service

## Decisions Made
- Alert fires once per event with no retry -- avoids spam if session flaps. If the clinic number itself is disconnected, the alert HTTP request fails silently (on-error: continue).
- Message stub uses a NoOp node rather than logging to database -- keeps it minimal until Phase 4 wires chatbot logic.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Webhook endpoints are ready: connection-update alerts admin on disconnect, messages-upsert accepts events
- Phase 4 (chatbot) will replace the NoOp node in whatsapp-message-stub.json with AI routing logic
- Evolution API env vars are available to n8n for all future workflow development

## Self-Check: PASSED

- FOUND: n8n/workflows/whatsapp-connection-update.json
- FOUND: n8n/workflows/whatsapp-message-stub.json
- FOUND: docker-compose.yml
- FOUND: commit 0eb3952

---
*Phase: 02-whatsapp-core*
*Completed: 2026-03-28*
