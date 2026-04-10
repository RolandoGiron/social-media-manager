---
phase: 04-ai-chatbot-appointment-booking
plan: 04
subsystem: n8n-workflows
tags: [chatbot, booking, google-calendar, whatsapp, appointment]
dependency_graph:
  requires: [04-01, 04-03]
  provides: [sub-booking-flow, booking-integration]
  affects: [whatsapp-chatbot, appointments-table, google-calendar]
tech_stack:
  added: [n8n-google-calendar-node]
  patterns: [multi-turn-booking-conversation, sub-workflow-execution, state-machine-booking-steps]
key_files:
  created:
    - n8n/workflows/sub-booking-flow.json
  modified:
    - n8n/workflows/whatsapp-chatbot.json
decisions:
  - "Booking state routing added before intent classification — booking_flow state bypasses KB load + classify-intent entirely"
  - "Separate merge nodes for mid-booking path vs intent-routing path to avoid n8n waitForAll deadlock"
  - "Slot selection parses digit 1/2/3 from free text — natural reply without menus (D-06)"
  - "patient_id cast to UUID only if non-empty/non-null to avoid Postgres cast errors on unknown patients"
metrics:
  duration: 10min
  completed_date: "2026-04-10"
  tasks_completed: 1
  tasks_total: 2
  files_changed: 2
---

# Phase 04 Plan 04: Booking Sub-Workflow + Chatbot Integration Summary

One-liner: Multi-turn appointment booking via Google Calendar with OpenAI natural language extraction, wired into the main chatbot as a proper sub-workflow replacing the placeholder Set node.

## What Was Built

### sub-booking-flow.json (23 nodes)

A self-contained sub-workflow that handles the full booking conversation lifecycle. Receives inputs from the main chatbot workflow (message_text, booking_context, patient_id, patient_name, remote_jid, etc.) and returns response_text, new_state, new_context.

**State machine inside the sub-workflow:**

| Step | Trigger | Output |
|------|---------|--------|
| awaiting_service_type | BOOKING intent or first booking turn | OpenAI extracts service name; asks user if unclear |
| awaiting_datetime | Service type known | OpenAI extracts date/time as JSON; Google Calendar checks availability; presents 2-3 slots |
| confirming_slot | Patient replies 1/2/3 | Creates GCal event, inserts appointment row, sends "Cita confirmada" |

**Key nodes:**
- `Extract Service Type (OpenAI)` — gpt-4o-mini, temperature 0.1, returns service name or NEEDS_INPUT
- `Extract Date and Time (OpenAI)` — returns `{"date": "YYYY-MM-DD", "time": "HH:mm"}` or `{"error": "NEEDS_INPUT"}`
- `Get Calendar Events` — Google Calendar OAuth2, queries 9:00-18:00 on target date
- `Find Available Slots` — Code node: finds free 30-min slots, sorts by proximity to preferred time, returns top 3
- `Create Calendar Event` — Google Calendar OAuth2, creates event with patient name + service in summary
- `Insert Appointment` — Postgres INSERT into appointments table with google_event_id, scheduled_at, appointment_type

### whatsapp-chatbot.json (27 nodes, updated)

**Changes from previous version:**
1. Added `Is Booking Flow Active?` IF node after `Is Human Handoff?` — checks if `conversation.state == 'booking_flow'`
2. `booking_flow` state routes to `Continue Booking Flow` (Execute Workflow → sub-booking-flow), bypassing KB load and intent classification
3. Replaced `Set Booking Response` placeholder Set node with `Start Booking Flow` (Execute Workflow → sub-booking-flow) for new BOOKING intents
4. Added `Merge All Response Paths` node to merge the mid-booking path with the intent-routing path before state update
5. Both paths end in the same Update Conversation State → Insert Bot Message → Send WA Message sequence

## Deviations from Plan

### Auto-added: Separate merge for booking bypass path

**Found during:** Task 1 — architectural need when wiring both new-booking and mid-booking paths
**Issue:** The original plan's merge node assumed all intent responses funneled into one merge. Adding the booking bypass path (which skips the intent routing entirely) required a second merge node before the state update.
**Fix:** Added `Merge All Response Paths` node with two inputs: (0) from mid-booking Prepare node, (1) from Check FAQ Triggers Handoff. Updated Insert Bot Message and Send WA Message to reference the new merge node.
**Files modified:** n8n/workflows/whatsapp-chatbot.json
**Commit:** 9e6fa6d

None of the plan's core logic was changed — the deviation was purely structural to handle the two-path flow.

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Booking sub-workflow + main workflow integration | 9e6fa6d | n8n/workflows/sub-booking-flow.json (created), n8n/workflows/whatsapp-chatbot.json (updated) |
| 2 | End-to-end chatbot verification | PENDING | Awaiting human verify checkpoint |

## Known Stubs

None — sub-booking-flow.json is fully wired: OpenAI for NLP, Google Calendar for availability/booking, Postgres for persistence, confirmation message with real date formatting.

The `CLINIC_CALENDAR_ID` and `google-calendar-credential` must be configured in n8n before import. These are runtime credentials, not stubs.

## Threat Flags

None — no new network endpoints introduced. Sub-workflow is invoked only from within n8n (Execute Workflow node), not exposed via webhook.

## Self-Check: PASSED

- n8n/workflows/sub-booking-flow.json: EXISTS, 23 nodes, valid JSON
- n8n/workflows/whatsapp-chatbot.json: EXISTS, 27 nodes, valid JSON, references sub-booking-flow
- Commit 9e6fa6d: EXISTS in git log
- All acceptance criteria: VERIFIED by automated check
