---
status: resolved
trigger: "Phone normalization produces all Error on CSV import for El Salvador numbers"
created: 2026-04-01T00:00:00Z
updated: 2026-04-07T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - pandas reads numeric telefono column as float64 when any value is missing, producing "77546650.0" which has 9 digits and fails the 8-digit check
test: Simulated CSV with missing phone -> all phones become float64 -> normalize_sv_phone gets "77546650.0" -> 9 digits -> Error
expecting: Fix by converting telefono to int-string before normalization
next_action: Apply fix to normalize_sv_phone or build_preview to strip .0 from float strings

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

- timestamp: 2026-04-07T00:00:00Z
  checked: pandas dtype behavior with numeric phone columns
  found: When CSV has any empty telefono cell, pandas reads entire column as float64. str(77546650.0) -> "77546650.0" -> after \D strip -> "775466500" (9 digits) -> fails 8-digit check
  implication: THIS is the real production bug. The test fix was correct but insufficient -- the normalization function itself needs to handle float-string inputs

- timestamp: 2026-04-07T00:00:00Z
  checked: normalize_sv_phone with "77546650.0" input
  found: re.sub(r"\D", "", "77546650.0") produces "775466500" (9 digits), function returns Error
  implication: Confirmed root cause. Fix needed in normalize_sv_phone to handle decimal point in numeric strings

## Resolution

root_cause: pandas reads the telefono CSV column as float64 when any cell is empty (or when exported from Excel). This converts 77546650 to 77546650.0. str(77546650.0) produces "77546650.0", and re.sub(r"\D", "") strips the dot but keeps the trailing "0", yielding 9 digits instead of 8. normalize_sv_phone rejects anything not exactly 8 digits.
fix: Added float-string handling in normalize_sv_phone -- regex detects "DIGITS.0+" pattern and strips the decimal suffix before digit extraction. Also handles "nan" string from pandas NaN conversion. Added 4 regression tests.
verification: All 59 tests pass (22 patient tests including 4 new ones for float/nan cases). End-to-end simulation with float64 DataFrame produces correct Nuevo/Error classification.
files_changed: [admin-ui/src/components/patients.py, admin-ui/src/tests/test_patients.py]
