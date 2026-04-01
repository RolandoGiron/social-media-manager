---
phase: 03-crm-core
plan: 01
subsystem: database
tags: [psycopg2, pandas, phone-normalization, csv-import, template-engine, tdd]

# Dependency graph
requires:
  - phase: 01-infrastructure-foundation
    provides: PostgreSQL schema (001_schema.sql) with patients, tags, patient_tags, message_templates tables
provides:
  - database.py: DB connection helper, patient CRUD, tag CRUD, template CRUD, batch insert
  - patients.py: Phone normalization (+52 MX E.164), CSV/Excel parsing, import preview builder
  - templates.py: Variable extraction ({{var}} regex), preview rendering with sample values
  - Full test suite: 39 new tests covering all business logic and DB operations
affects: [03-crm-core]

# Tech tracking
tech-stack:
  added: [psycopg2-binary]
  patterns: [database-helper-module, phone-normalization, template-variable-extraction, tdd-red-green]

key-files:
  created:
    - admin-ui/src/components/database.py
    - admin-ui/src/components/patients.py
    - admin-ui/src/components/templates.py
    - admin-ui/src/tests/test_database.py
    - admin-ui/src/tests/test_patients.py
    - admin-ui/src/tests/test_templates.py
  modified:
    - admin-ui/src/tests/conftest.py

key-decisions:
  - "psycopg2-binary installed on host for test execution (already in Docker requirements.txt)"
  - "Phone normalization handles +521 legacy format by stripping the 1 prefix"
  - "Tag deletion blocked when assigned to patients (D-08) via ValueError"
  - "Template variables use open {{variable}} syntax with dict.fromkeys for dedup"

patterns-established:
  - "Pattern: database.py helper with try/finally connection management per function"
  - "Pattern: execute_values for batch inserts with ON CONFLICT DO NOTHING"
  - "Pattern: Pure business logic in separate modules (patients.py, templates.py) testable without DB"
  - "Pattern: TDD red-green workflow with atomic commits per phase"

requirements-completed: [CRM-01, CRM-02, CRM-03, WA-01]

# Metrics
duration: 3min
completed: 2026-04-01
---

# Phase 3 Plan 01: CRM Data Layer Summary

**Database helper with patient/tag/template CRUD, phone normalization for +52 MX E.164, CSV import parser, and template variable extraction -- 53 tests green**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-01T15:57:26Z
- **Completed:** 2026-04-01T16:00:30Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Three component modules (database.py, patients.py, templates.py) with all exported functions per plan spec
- 39 new unit tests covering phone normalization variants, CSV parsing, preview builder, all DB CRUD operations, and template rendering
- Full test suite of 53 tests passes (39 new + 14 existing)
- TDD workflow followed: RED commits with failing tests, GREEN commits with passing implementation

## Task Commits

Each task was committed atomically:

1. **Task 1: Pure business logic modules** - `720aa69` (test: RED) + `f836413` (feat: GREEN)
2. **Task 2: Database helper module** - `467bf32` (feat: RED test + GREEN implementation combined)

## Files Created/Modified
- `admin-ui/src/components/database.py` - DB connection, patient queries, tag CRUD, template CRUD, batch insert with execute_values
- `admin-ui/src/components/patients.py` - Phone normalization (+52 MX), CSV/Excel parsing, preview builder
- `admin-ui/src/components/templates.py` - {{variable}} extraction regex, preview rendering with sample values
- `admin-ui/src/tests/test_database.py` - 15 tests for all DB helper functions with mocked psycopg2
- `admin-ui/src/tests/test_patients.py` - 16 tests for phone normalization, CSV parsing, preview builder
- `admin-ui/src/tests/test_templates.py` - 8 tests for variable extraction and preview rendering
- `admin-ui/src/tests/conftest.py` - Added sample_csv_bytes and sample_csv_missing_col fixtures

## Decisions Made
- Installed psycopg2-binary on host Python for running tests outside Docker (already in Docker requirements.txt)
- Phone normalization checks +521 (13 digits) before +52 (12 digits) to avoid ambiguous stripping
- Tag deletion raises ValueError with patient count message (per D-08 locked decision)
- Template variable extraction uses dict.fromkeys for order-preserving deduplication

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed psycopg2-binary on host**
- **Found during:** Task 2 (database.py tests)
- **Issue:** psycopg2 not installed on host Python; tests could not import components.database
- **Fix:** Ran `pip install psycopg2-binary` (already listed in admin-ui/requirements.txt for Docker)
- **Files modified:** None (system package install)
- **Verification:** All 15 database tests pass with mocked connections
- **Committed in:** N/A (pip install, not a code change)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary for test execution outside Docker. No scope creep.

## Issues Encountered
None beyond the psycopg2 installation.

## Known Stubs
None - all functions are fully implemented with real logic.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All data layer and business logic modules ready for Plans 02 (Pacientes page) and 03 (Plantillas page)
- database.py provides all query functions the UI pages will consume
- patients.py and templates.py provide all pure logic the UI pages will call
- conftest.py has shared fixtures for future test expansion

---
*Phase: 03-crm-core*
*Completed: 2026-04-01*
