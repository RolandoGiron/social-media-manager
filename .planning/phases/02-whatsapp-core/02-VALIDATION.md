---
phase: 2
slug: whatsapp-core
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Python, for Streamlit components) + n8n manual execution |
| **Config file** | none — Wave 0 creates pytest.ini |
| **Quick run command** | `docker compose exec streamlit pytest tests/ -x --tb=short` |
| **Full suite command** | `docker compose exec streamlit pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `docker compose exec streamlit pytest tests/ -x --tb=short`
- **After every plan wave:** Run `docker compose exec streamlit pytest tests/ -v` + manual n8n workflow test
- **Before `/gsd:verify-work`:** Full suite must be green + all 4 success criteria manually verified
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 0 | INFRA-01 | integration | `pytest tests/test_evolution_api.py::test_get_qr_code -x` | ❌ W0 | ⬜ pending |
| 2-01-02 | 01 | 0 | INFRA-01 | integration | `pytest tests/test_evolution_api.py::test_create_instance -x` | ❌ W0 | ⬜ pending |
| 2-02-01 | 02 | 0 | INFRA-02 | unit | `pytest tests/test_sidebar.py::test_connection_state_display -x` | ❌ W0 | ⬜ pending |
| 2-02-02 | 02 | 0 | INFRA-02 | unit | `pytest tests/test_sidebar.py::test_sidebar_connected -x` | ❌ W0 | ⬜ pending |
| 2-03-01 | 03 | 1 | INFRA-03 | manual | Send test webhook via curl to n8n endpoint | N/A | ⬜ pending |
| 2-03-02 | 03 | 1 | INFRA-03 | manual | Trigger workflow manually in n8n UI, verify message sent | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `admin-ui/src/tests/test_evolution_api.py` — stubs for INFRA-01 (API client tests with mocked responses)
- [ ] `admin-ui/src/tests/test_sidebar.py` — stubs for INFRA-02 (sidebar rendering logic)
- [ ] `admin-ui/src/tests/conftest.py` — shared fixtures (mock Evolution API responses)
- [ ] `admin-ui/src/pytest.ini` — test config
- [ ] `admin-ui/requirements.txt` updated with `pytest` and `pytest-mock`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| n8n workflow receives CONNECTION_UPDATE | INFRA-03 | Requires live Evolution API webhook delivery | Send test webhook via `curl -X POST {n8n-webhook-url}/connection-update -H "Content-Type: application/json" -d '{"event":"CONNECTION_UPDATE","data":{"state":"close"}}'` |
| Alert message sent on disconnect | INFRA-03 | Requires live WhatsApp session and n8n execution | Trigger workflow manually in n8n UI; verify Telegram/WhatsApp message received by admin |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
