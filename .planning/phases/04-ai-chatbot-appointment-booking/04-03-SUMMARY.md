---
phase: 04-ai-chatbot-appointment-booking
plan: 03
subsystem: chatbot
tags: [n8n, openai, gpt-4o-mini, whatsapp, evolution-api, postgresql, chatbot, sub-workflows]

# Dependency graph
requires:
  - phase: 04-01
    provides: knowledge_base table and database functions for inbox/FAQ data

provides:
  - n8n main chatbot workflow (whatsapp-chatbot.json) replacing the stub workflow
  - Sub-workflow for intent classification via OpenAI (sub-classify-intent.json)
  - Sub-workflow for FAQ answering via OpenAI with knowledge_base injection (sub-faq-answer.json)
  - Sub-workflow for WhatsApp message send with typing indicator (sub-send-wa-message.json)

affects:
  - 04-04 (booking sub-workflow plugs into booking_flow branch of main chatbot)
  - Any phase testing the chatbot end-to-end

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sub-workflow pattern: main workflow dispatches to specialized sub-workflows via Execute Workflow node"
    - "Intent classification: OpenAI gpt-4o-mini with temperature=0.1 for deterministic labeling"
    - "FAQ injection: SELECT all active knowledge_base rows, format as Q/A string, inject into LLM system prompt"
    - "State machine in PostgreSQL: conversation state transitions encoded in n8n Switch/IF nodes"

key-files:
  created:
    - n8n/workflows/whatsapp-chatbot.json
    - n8n/workflows/sub-classify-intent.json
    - n8n/workflows/sub-faq-answer.json
    - n8n/workflows/sub-send-wa-message.json
  modified: []

key-decisions:
  - "Merge node in chooseBranch mode used to unify conversation creation (new vs existing) before message insert"
  - "fromMe filter placed at node 2 (immediately after webhook) to prevent infinite bot loops per Pitfall 3"
  - "FAQ handoff detection done in Code node after FAQ sub-workflow to check response text for handoff phrase"
  - "booking_flow branch sends placeholder response and sets context booking_step=awaiting_service_type pending Plan 04"
  - "api_key hardcoded as Jehova01 in Extract Fields node — same pattern as whatsapp-connection-update.json"

patterns-established:
  - "Sub-workflow input/output: Execute Workflow Trigger receives named fields; Set node normalizes output for caller"
  - "Conversation state transitions: Code node after intent merge normalizes state and context before Postgres UPDATE"

requirements-completed: [BOT-01, BOT-02, BOT-04]

# Metrics
duration: 5min
completed: 2026-04-08
---

# Phase 4 Plan 03: Core Chatbot Workflow Summary

**n8n chatbot pipeline with OpenAI intent classification, knowledge_base FAQ answering, human escalation, and typing indicator — 4 workflow files implementing the WhatsApp chatbot brain**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-08T21:35:52Z
- **Completed:** 2026-04-08T21:40:24Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created 3 sub-workflows covering the chatbot's shared operations (classify intent, generate FAQ answer, send WhatsApp message with typing indicator)
- Created the main 23-node chatbot workflow replacing `whatsapp-message-stub.json` — full pipeline from webhook to PostgreSQL state persistence to WhatsApp reply
- Implemented complete state machine: new -> awaiting_intent -> faq_flow/booking_flow/human_handoff, with fromMe filter preventing infinite bot loops
- FAQ answers use knowledge_base injection into OpenAI system prompt; handoff phrase detection automatically escalates to human_handoff state

## Task Commits

Each task was committed atomically:

1. **Task 1: Sub-workflows (classify-intent, faq-answer, send-wa-message)** - `db49e18` (feat)
2. **Task 2: Main chatbot webhook workflow** - `31ad58f` (feat)

**Plan metadata:** _(docs commit follows)_

## Files Created/Modified
- `n8n/workflows/sub-classify-intent.json` - Execute Workflow Trigger + OpenAI Chat (gpt-4o-mini, temp=0.1) + Set node; classifies message into FAQ/BOOKING/HANDOFF/GREETING
- `n8n/workflows/sub-faq-answer.json` - Execute Workflow Trigger + OpenAI Chat (temp=0.3) + Set node; answers from knowledge_base, returns is_handoff flag
- `n8n/workflows/sub-send-wa-message.json` - Execute Workflow Trigger + HTTP sendPresence (composing) + Wait 2s + HTTP sendText; full typing indicator pipeline
- `n8n/workflows/whatsapp-chatbot.json` - 23-node main workflow: webhook -> fromMe filter -> extract fields -> read/create conversation -> insert inbound message -> check human_handoff -> load KB -> format FAQs -> classify intent -> switch by intent -> merge responses -> detect handoff -> update state -> insert bot message -> send WA message

## Decisions Made
- Merge node in `chooseBranch / waitForAll` mode used to unify existing vs new conversation paths before inserting inbound messages
- `fromMe` filter placed as node 2 immediately after the webhook (before any DB access) to prevent the infinite loop Pitfall 3 from RESEARCH.md
- FAQ handoff detection handled in a Code node that runs after the Merge Intent Responses node — checks `is_handoff` flag and response text for the exact handoff phrase
- Booking branch sends placeholder response "Claro, con gusto te ayudo a agendar una cita" and sets `context = {booking_step: awaiting_service_type}` pending Plan 04 implementation
- api_key field extracted directly in the Extract Message Fields Set node using the same hardcoded value as the connection-update workflow

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- File write tool created files in main repo directory (`/home/rolando/Desarrollo/social-media-manager/n8n/workflows/`) rather than the worktree directory — detected when verifying git status in the worktree. Resolved by copying files to the correct worktree path before committing.

## User Setup Required
None - no external service configuration required. However, the following must be configured in n8n before the chatbot is operational:
- **OpenAI API credential** named "OpenAI API" with `OPENAI_API_KEY`
- **PostgreSQL credential** named "PostgreSQL" pointing to the project's Postgres instance
- **Sub-workflow IDs**: The Execute Workflow nodes use `mode: name` (workflow name matching) — ensure sub-workflows are imported into n8n with their exact names: `sub-classify-intent`, `sub-faq-answer`, `sub-send-wa-message`

## Known Stubs
- `n8n/workflows/whatsapp-chatbot.json` — "Set Booking Response" node: booking_flow branch sends a placeholder response and sets `booking_step=awaiting_service_type` in context. The actual multi-turn booking flow is built in Plan 04 (`sub-booking-flow.json`). This is intentional and documented in the plan.

## Next Phase Readiness
- Plan 04 (sub-booking-flow.json) can now plug into the `booking_flow` branch of the Switch node — the main workflow already stores `context.booking_step` and transitions to `booking_flow` state
- The chatbot is functional for FAQ + human escalation immediately after n8n credentials are configured
- `whatsapp-message-stub.json` is superseded but not deleted — the main chatbot workflow uses the same webhook path, so only one should be active in n8n at a time

---
*Phase: 04-ai-chatbot-appointment-booking*
*Completed: 2026-04-08*
