---
status: awaiting_human_verify
trigger: "Phone normalization produces all Error on CSV import for El Salvador numbers"
created: 2026-04-01T00:00:00Z
updated: 2026-04-01T00:01:00Z
---

## Current Focus

hypothesis: CONFIRMED - Tests referenced nonexistent normalize_mx_phone and used Mexico phone data
test: Full test suite run
expecting: All 55 tests pass
next_action: Await human verification of CSV import in Streamlit UI

## Symptoms

expected: Patient CSV import shows "Nuevo" status for valid El Salvador phone numbers
actual: ALL rows show "Error" — tests broken because they reference normalize_mx_phone which no longer exists
errors: ImportError on normalize_mx_phone; test assertions use Mexico +52 format
reproduction: Run pytest on test_patients.py
started: Always broken — code updated to SV but tests not updated

## Eliminated

## Evidence

- timestamp: 2026-04-01T00:01:00Z
  checked: admin-ui/src/components/patients.py
  found: Function is already named normalize_sv_phone with correct El Salvador logic (8 digits, +503 prefix)
  implication: Production code is correct; bug is in tests only

- timestamp: 2026-04-01T00:01:00Z
  checked: admin-ui/src/tests/test_patients.py
  found: Tests import normalize_mx_phone (does not exist), all test cases use Mexico phone format (+52, 10 digits)
  implication: Tests will fail with ImportError; need to update imports and test data to El Salvador format

- timestamp: 2026-04-01T00:01:00Z
  checked: admin-ui/src/tests/conftest.py
  found: sample_csv_bytes fixture uses Mexico phone numbers (5512345678, 5587654321)
  implication: Even if import is fixed, CSV fixture data will fail SV normalization (8-digit check)

- timestamp: 2026-04-01T00:02:00Z
  checked: Full test suite after fix
  found: All 55 tests pass (18 patient tests + 37 others), zero regressions
  implication: Fix is correct and complete

## Resolution

root_cause: Tests were never updated when normalize_mx_phone was renamed to normalize_sv_phone. Test data still used Mexico phone format (10-digit numbers with +52 prefix).
fix: Updated test_patients.py (import, class name, all test cases to El Salvador 8-digit format) and conftest.py (CSV fixture phone numbers to SV format). Added new tests for landline and country-code-in-CSV scenarios.
verification: All 55 tests pass. No regressions.
files_changed: [admin-ui/src/tests/test_patients.py, admin-ui/src/tests/conftest.py]
