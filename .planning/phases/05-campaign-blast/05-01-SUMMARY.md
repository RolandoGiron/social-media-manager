---
phase: 05-campaign-blast
plan: "01"
subsystem: database
tags: [psycopg2, postgresql, pytest, tdd, campaign_log, campaign_recipients]

# Dependency graph
requires:
  - phase: 03-crm-core
    provides: patient_tags join table and tags table used by fetch_patients_by_tags
  - phase: 01-infrastructure-foundation
    provides: campaign_log and campaign_recipients tables in 001_schema.sql
provides:
  - fetch_patients_by_tags: returns distinct patients matching any of a list of tag UUIDs
  - insert_campaign: creates campaign_log row with status=pending, returns id
  - insert_campaign_recipients: batch inserts recipient rows via execute_values
  - fetch_campaign_status: returns progress dict for a campaign_id or None
  - cancel_campaign: sets status=cancelled and cancelled_at=now()
  - fetch_campaign_history: returns all campaigns DESC with concatenated tag names
affects:
  - 05-02: Streamlit Campanas page depends on all 6 functions
  - 05-03: n8n campaign-blast workflow validates against these row shapes

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD RED-GREEN: test file committed with ImportError failures before implementation"
    - "Campaign DB helpers follow get_connection()/try-finally/RealDictCursor pattern from database.py"
    - "execute_values used for batch insert of campaign_recipients (mirrors insert_patients pattern)"
    - "DISTINCT + ANY(%s::uuid[]) for multi-tag patient filtering (mirrors fetch_patients pattern)"

key-files:
  created:
    - admin-ui/src/tests/test_campaigns.py
  modified:
    - admin-ui/src/components/database.py

key-decisions:
  - "Early return guard in fetch_patients_by_tags for empty tag_ids avoids unnecessary DB round-trip"
  - "fetch_campaign_history uses correlated subquery to tags (not JOIN) to avoid row multiplication from UUID array expansion"
  - "insert_campaign returns only {id} via RETURNING id — Streamlit uses this to pass campaign_id to n8n webhook"

patterns-established:
  - "Campaign functions appended at end of database.py under # ---------- Campaigns (Phase 5) ---------- comment block"

requirements-completed: [WA-02, WA-03, WA-04]

# Metrics
duration: 2min
completed: 2026-04-13
---

# Phase 5 Plan 01: Campaign DB Helper Functions Summary

**Six psycopg2 campaign helper functions with full TDD coverage: fetch/insert/cancel/history for campaign_log and campaign_recipients tables**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-13T19:04:06Z
- **Completed:** 2026-04-13T19:06:03Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created 18 pytest tests across 6 test classes (RED commit `ea7e928`) covering SQL-shape assertions, edge cases, and commit verification
- Implemented 6 campaign helper functions appended to database.py without touching existing functions (GREEN commit `0a7340a`)
- Full test suite (95 tests) passes with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — Failing tests for all six campaign DB functions** - `ea7e928` (test)
2. **Task 2: GREEN — Implement six campaign DB functions in database.py** - `0a7340a` (feat)

_Note: TDD tasks have two commits (test → feat)_

## Files Created/Modified

- `admin-ui/src/tests/test_campaigns.py` — 18 pytest tests across 6 classes; mock pattern mirrors test_database.py
- `admin-ui/src/components/database.py` — 6 new campaign functions appended (+151 lines); existing functions untouched

## Decisions Made

- Early return guard in `fetch_patients_by_tags` returns `[]` immediately on empty `tag_ids`, avoiding a DB round-trip and SQL syntax error with an empty array
- `fetch_campaign_history` uses a correlated subquery `(SELECT string_agg(t.name, ...) FROM tags t WHERE t.id = ANY(cl.segment_tags))` rather than a LEFT JOIN to avoid row multiplication when a campaign has multiple segment_tags
- `insert_campaign` returns only `{id}` via `RETURNING id` — minimal surface, Streamlit only needs the UUID to pass to n8n webhook

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None — all 6 functions are fully implemented and tested. No hardcoded placeholders or empty return values.

## Next Phase Readiness

- All 6 campaign DB functions are implemented and test-verified
- Ready for 05-02: Streamlit 7_Campanas.py page (uses fetch_patients_by_tags, insert_campaign, insert_campaign_recipients, fetch_campaign_status, cancel_campaign, fetch_campaign_history)
- Ready for 05-03: n8n campaign-blast workflow (row shapes for campaign_log and campaign_recipients are validated by tests)

---
*Phase: 05-campaign-blast*
*Completed: 2026-04-13*
