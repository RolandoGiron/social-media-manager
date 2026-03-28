---
phase: 02-whatsapp-core
plan: 01
subsystem: infra, api
tags: [evolution-api, whatsapp, python, requests, pytest, docker-compose]

# Dependency graph
requires:
  - phase: 01-infrastructure-foundation
    provides: docker-compose.yml with 6 services, .env.example with base config
provides:
  - Evolution API env vars injected into Streamlit container
  - EvolutionAPIClient Python module with 5 methods
  - Test infrastructure with pytest, 14 test functions
affects: [02-whatsapp-core plan 02, 02-whatsapp-core plan 03]

# Tech tracking
tech-stack:
  added: [requests, pytest, pytest-mock, requests-mock]
  patterns: [EvolutionAPIClient wrapper pattern, env-var-based config, requests-mock for HTTP testing]

key-files:
  created:
    - admin-ui/src/components/evolution_api.py
    - admin-ui/src/components/__init__.py
    - admin-ui/src/tests/test_evolution_api.py
    - admin-ui/src/tests/test_sidebar.py
    - admin-ui/src/tests/conftest.py
    - admin-ui/src/tests/__init__.py
    - admin-ui/src/pytest.ini
  modified:
    - docker-compose.yml
    - .env.example
    - admin-ui/requirements.txt

key-decisions:
  - "EvolutionAPIClient reads config from env vars with constructor override support"
  - "Sidebar tests use pytest.mark.skip until sidebar.py is created in Plan 02-02"

patterns-established:
  - "API client pattern: class with env-var defaults, _headers(), _handle_error() helpers"
  - "Test pattern: requests_mock for HTTP mocking, conftest fixtures for shared clients"
  - "Skip-ahead test pattern: write behavior tests with skip marker for not-yet-implemented modules"

requirements-completed: [INFRA-01, INFRA-02]

# Metrics
duration: 3min
completed: 2026-03-28
---

# Phase 2 Plan 01: Evolution API Foundation Summary

**Evolution API Python client with 5 HTTP methods, docker-compose env var injection, and 14-test pytest scaffolding**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-28T10:59:14Z
- **Completed:** 2026-03-28T11:02:28Z
- **Tasks:** 3
- **Files modified:** 10

## Accomplishments
- Streamlit container now receives all Evolution API env vars (URL, key, instance name, phone numbers) at runtime
- EvolutionAPIClient module with create_instance, get_qr_code, get_connection_state, send_text_message, fetch_instances -- all with error handling via EvolutionAPIError
- Full pytest infrastructure: 9 passing API client tests + 5 skipped sidebar behavior tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Evolution API env vars to docker-compose and .env.example** - `988e9e9` (feat)
2. **Task 2: Create Evolution API Python client module with tests** - `3e54a86` (test/RED) + `0c342dc` (feat/GREEN)
3. **Task 3: Create sidebar status test scaffolds** - `45d68ac` (test)

## Files Created/Modified
- `docker-compose.yml` - Added 7 env vars and evolution-api dependency to streamlit service
- `.env.example` - Added WhatsApp Session section with 3 new vars
- `admin-ui/requirements.txt` - Added requests, pytest, pytest-mock, requests-mock
- `admin-ui/src/components/evolution_api.py` - HTTP client wrapper for Evolution API v2.2.3
- `admin-ui/src/components/__init__.py` - Package init
- `admin-ui/src/pytest.ini` - Pytest configuration
- `admin-ui/src/tests/conftest.py` - Shared fixtures (api_client, mock_session_state)
- `admin-ui/src/tests/test_evolution_api.py` - 9 tests for API client methods
- `admin-ui/src/tests/test_sidebar.py` - 5 skipped tests for sidebar rendering
- `admin-ui/src/tests/__init__.py` - Package init

## Decisions Made
- EvolutionAPIClient uses env vars as defaults but accepts constructor overrides for testability
- Sidebar tests are skip-marked rather than excluded -- they serve as executable specs for Plan 02-02
- send_text_message returns the full response dict (not just True/False) to preserve message ID for tracking

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed requests-mock dependency**
- **Found during:** Task 2 (GREEN phase)
- **Issue:** requests-mock not installed in local Python environment, tests failed to collect
- **Fix:** Installed via pip; already listed in requirements.txt for Docker builds
- **Files modified:** None (runtime dependency only)
- **Verification:** All 9 tests pass after install
- **Committed in:** 0c342dc (part of Task 2 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Expected environment setup. No scope creep.

## Issues Encountered
None beyond the expected dependency installation.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all code is fully functional with mocked tests.

## Next Phase Readiness
- Evolution API client module ready for import by sidebar component (Plan 02-02)
- Sidebar test scaffolds ready to be unskipped when sidebar.py is created
- docker-compose env vars ready for Evolution API integration

## Self-Check: PASSED

All 8 created files verified present. All 4 commit hashes verified in git log.

---
*Phase: 02-whatsapp-core*
*Completed: 2026-03-28*
