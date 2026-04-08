---
phase: 04-ai-chatbot-appointment-booking
plan: 01
subsystem: data-layer
tags: [database, knowledge-base, inbox, appointments, postgresql, tdd]
dependency_graph:
  requires: [postgres/init/001_schema.sql]
  provides: [knowledge_base table DDL, KB CRUD functions, inbox query functions, appointment insert]
  affects: [04-02, 04-03, 04-04]
tech_stack:
  added: [streamlit-autorefresh]
  patterns: [psycopg2 RealDictCursor, try/finally conn.close(), upsert via RETURNING *]
key_files:
  created:
    - postgres/init/003_knowledge_base.sql
    - admin-ui/src/tests/test_knowledge_base.py
    - admin-ui/src/tests/test_inbox.py
  modified:
    - admin-ui/src/components/database.py
    - admin-ui/requirements.txt
decisions:
  - "fetch_conversations excludes closed conversations by default and sorts human_handoff first (D-15)"
  - "upsert_knowledge_base_item uses truthy check on item_id to select INSERT vs UPDATE path"
  - "insert_message updates conversation last_message_at in same transaction for data consistency"
metrics:
  duration: 3min
  completed_date: "2026-04-08T21:34:13Z"
  tasks_completed: 2
  files_changed: 5
---

# Phase 4 Plan 01: Data Layer — Knowledge Base, Inbox, Appointments Summary

**One-liner:** PostgreSQL knowledge_base migration + 8 DB helper functions (KB CRUD, inbox queries, appointment insert) with 18 TDD tests covering all new functions.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Knowledge base migration + KB CRUD functions + tests | d955998 | 003_knowledge_base.sql, database.py (+3 funcs), test_knowledge_base.py (8 tests), requirements.txt |
| 2 | Inbox query functions + appointment insert + tests | cd07202 | database.py (+5 funcs), test_inbox.py (10 tests) |

## What Was Built

### Knowledge Base Table (003_knowledge_base.sql)

New PostgreSQL table with:
- Fields: `id`, `pregunta`, `respuesta`, `categoria` (CHECK constraint: horarios/ubicacion/precios/servicios/general), `is_active`, `created_at`, `updated_at`
- `trg_knowledge_base_updated_at` trigger using existing `update_updated_at()` function
- Indexes on `categoria` and `is_active`

### KB CRUD Functions (database.py)

- `fetch_knowledge_base(active_only=True)` — filters by `is_active`, orders by `categoria, created_at`
- `upsert_knowledge_base_item(item_id, pregunta, respuesta, categoria, is_active)` — INSERT if item_id falsy, UPDATE if truthy; RETURNING * in both cases
- `delete_knowledge_base_item(item_id)` — simple DELETE with commit

### Inbox Query Functions (database.py)

- `fetch_conversations(state_filter=None)` — LEFT JOINs patients, excludes closed unless state_filter set, subquery for last_message, sorts human_handoff first
- `fetch_messages_for_conversation(conversation_id)` — ordered ASC for chat display
- `insert_message(conversation_id, direction, sender, content)` — inserts message + updates conversation.last_message_at in same transaction
- `update_conversation_state(conversation_id, new_state)` — UPDATE RETURNING id, state, wa_contact_id, context
- `insert_appointment(patient_id, appointment_type, scheduled_at, ...)` — RETURNING * with optional google_event_id, duration_minutes, notes

### Test Coverage

- `test_knowledge_base.py`: 8 tests — active filter, all-rows, ordering, key validation, INSERT path, UPDATE path, delete SQL, delete returns None
- `test_inbox.py`: 10 tests — non-closed filter, state filter, human_handoff sort, patient join, message ordering, message INSERT + conversation update, state UPDATE, appointment INSERT, optional params
- Full suite: **77 tests, all passing**, zero regressions

### Dependency Addition

- `streamlit-autorefresh` added to `admin-ui/requirements.txt`

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all functions are fully implemented with real SQL queries matching the schema. No placeholder data.

## Self-Check

- [x] `postgres/init/003_knowledge_base.sql` — created and contains "CREATE TABLE knowledge_base"
- [x] `admin-ui/src/components/database.py` — 8 new functions added (24 total `def` count)
- [x] `admin-ui/src/tests/test_knowledge_base.py` — 8 tests, all passing
- [x] `admin-ui/src/tests/test_inbox.py` — 10 tests, all passing
- [x] `admin-ui/requirements.txt` — contains "streamlit-autorefresh"
- [x] Commit d955998 — Task 1
- [x] Commit cd07202 — Task 2
- [x] Full test suite: 77 passed, 0 failed

## Self-Check: PASSED
