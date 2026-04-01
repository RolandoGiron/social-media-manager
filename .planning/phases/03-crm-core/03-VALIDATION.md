---
phase: 3
slug: crm-core
status: draft
nyquist_compliant: false
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
| 3-01-01 | 01 | 1 | CRM-01 | unit | `pytest src/tests/test_csv_import.py -x -q` | ❌ W0 | ⬜ pending |
| 3-01-02 | 01 | 1 | CRM-01 | unit | `pytest src/tests/test_phone_normalize.py -x -q` | ❌ W0 | ⬜ pending |
| 3-01-03 | 01 | 2 | CRM-01 | integration | `pytest src/tests/test_import_db.py -x -q` | ❌ W0 | ⬜ pending |
| 3-02-01 | 02 | 1 | CRM-02 | unit | `pytest src/tests/test_patient_search.py -x -q` | ❌ W0 | ⬜ pending |
| 3-02-02 | 02 | 1 | CRM-02 | unit | `pytest src/tests/test_tag_filter.py -x -q` | ❌ W0 | ⬜ pending |
| 3-02-03 | 02 | 2 | CRM-03 | unit | `pytest src/tests/test_tag_crud.py -x -q` | ❌ W0 | ⬜ pending |
| 3-03-01 | 03 | 1 | WA-01 | unit | `pytest src/tests/test_template_crud.py -x -q` | ❌ W0 | ⬜ pending |
| 3-03-02 | 03 | 1 | WA-01 | unit | `pytest src/tests/test_template_render.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/tests/test_phone_normalize.py` — unit tests for MX phone normalization logic (CRM-01)
- [ ] `src/tests/test_csv_import.py` — unit tests for CSV parsing and duplicate detection (CRM-01)
- [ ] `src/tests/test_import_db.py` — integration tests for batch insert with conflict handling (CRM-01)
- [ ] `src/tests/test_patient_search.py` — unit tests for search query construction (CRM-02)
- [ ] `src/tests/test_tag_filter.py` — unit tests for tag-based filtering (CRM-02)
- [ ] `src/tests/test_tag_crud.py` — unit tests for tag create/assign/remove operations (CRM-03)
- [ ] `src/tests/test_template_crud.py` — unit tests for template save/load/delete (WA-01)
- [ ] `src/tests/test_template_render.py` — unit tests for `{{nombre}}` / `{{fecha}}` variable rendering (WA-01)
- [ ] `src/tests/conftest.py` — shared fixtures: test DB connection, sample patient rows, sample CSV bytes

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

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
