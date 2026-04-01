---
phase: 3
slug: crm-core
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-01
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | admin-ui/src/tests/ |
| **Quick run command** | `docker compose exec admin-ui pytest src/tests/ -x -q` |
| **Full suite command** | `docker compose exec admin-ui pytest src/tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `docker compose exec admin-ui pytest src/tests/ -x -q`
- **After every plan wave:** Run `docker compose exec admin-ui pytest src/tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 1 | CRM-01 | unit | `pytest src/tests/test_patients.py -x -q` | ✅ Plan 01 Task 1 | ⬜ pending |
| 3-01-02 | 01 | 1 | WA-01 | unit | `pytest src/tests/test_templates.py -x -q` | ✅ Plan 01 Task 1 | ⬜ pending |
| 3-01-03 | 01 | 1 | CRM-02, CRM-03 | unit | `pytest src/tests/test_database.py -x -q` | ✅ Plan 01 Task 2 | ⬜ pending |
| 3-02-01 | 02 | 2 | CRM-01, CRM-02, CRM-03 | syntax | `python -m py_compile pages/3_Pacientes.py` | ✅ Plan 02 Task 1 | ⬜ pending |
| 3-03-01 | 03 | 2 | WA-01 | syntax | `python -m py_compile pages/4_Plantillas.py` | ✅ Plan 03 Task 1 | ⬜ pending |
| 3-03-02 | 03 | 2 | D-12 | syntax | `python -m py_compile app.py` | ✅ Plan 03 Task 2 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Plan 01 creates all test files as part of its TDD workflow. No separate Wave 0 scaffolding is needed.

- [x] `src/tests/test_patients.py` — unit tests for phone normalization, CSV parsing, preview builder (Plan 01 Task 1)
- [x] `src/tests/test_templates.py` — unit tests for variable extraction and preview rendering (Plan 01 Task 1)
- [x] `src/tests/test_database.py` — unit tests for all database.py CRUD functions with mocked DB (Plan 01 Task 2)
- [x] `src/tests/conftest.py` — shared fixtures: sample CSV bytes, mock DB connection (Plan 01 Tasks 1+2)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Streamlit file upload widget accepts CSV/Excel | CRM-01 | Browser interaction | Upload `clientes.csv` via the import page; verify preview table renders |
| QR / session status visible on import page sidebar | Phase 2 integration | Requires live Evolution API | Open import page and confirm WhatsApp status chip appears in sidebar |
| Duplicate row flagging visible in import preview | CRM-01 | UI rendering | Import file with 2 identical phone numbers; verify "duplicate" badge shown |
| Tag assignment persists across page navigation | CRM-03 | Streamlit session state | Tag a patient, navigate to Patients list, confirm tag still shown |
| Template preview renders correctly with accented chars | WA-01 | Visual rendering | Create template with `{{nombre}}` = "José"; confirm accent preserved in preview |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
