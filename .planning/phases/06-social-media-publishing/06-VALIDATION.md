---
phase: 06
slug: social-media-publishing
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-13
---

# Phase 06 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `streamlit/tests/` (to be created in Wave 0) |
| **Quick run command** | `docker compose exec streamlit python -m pytest streamlit/tests/ -q --tb=short` |
| **Full suite command** | `docker compose exec streamlit python -m pytest streamlit/tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | SOCIAL-01 | — | Insert validates image_url is internal path, not external redirect | unit | `pytest streamlit/tests/test_social_posts.py::test_insert_social_post -q` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | SOCIAL-01 | — | Composer rejects scheduled_at in the past | unit | `pytest streamlit/tests/test_social_posts.py::test_reject_past_date -q` | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 1 | SOCIAL-01 | — | Timezone-aware scheduling (ZoneInfo Mexico_City) | unit | `pytest streamlit/tests/test_social_posts.py::test_timezone_aware_schedule -q` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 2 | SOCIAL-02 | — | Dispatcher uses SELECT FOR UPDATE SKIP LOCKED (no double-post) | unit | `pytest streamlit/tests/test_dispatcher.py::test_skip_locked -q` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 2 | SOCIAL-02 | — | Mock mode returns success without hitting Meta API | unit | `pytest streamlit/tests/test_dispatcher.py::test_mock_mode -q` | ❌ W0 | ⬜ pending |
| 06-03-01 | 03 | 2 | SOCIAL-03 | — | Unified campaign action inserts both campaign + social_post rows atomically | unit | `pytest streamlit/tests/test_unified_campaign.py::test_atomic_insert -q` | ❌ W0 | ⬜ pending |
| 06-03-02 | 03 | 2 | SOCIAL-03 | — | Step 3 checkbox=OFF leaves Phase 5 flow unchanged | unit | `pytest streamlit/tests/test_unified_campaign.py::test_step3_disabled -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `streamlit/tests/test_social_posts.py` — stubs for SOCIAL-01 (insert, past-date, timezone)
- [ ] `streamlit/tests/test_dispatcher.py` — stubs for SOCIAL-02 (skip-locked, mock mode)
- [ ] `streamlit/tests/test_unified_campaign.py` — stubs for SOCIAL-03 (atomic insert, step3 disabled)
- [ ] `streamlit/tests/conftest.py` — shared fixtures (mock DB connection, mock Meta API)
- [ ] `pytest` + `pytest-mock` — if not already in requirements.txt

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Social post publishes to Facebook/Instagram at scheduled time | SOCIAL-02 | Meta API gated behind App Review; MOCK_SOCIAL=true for v1 | When MOCK_SOCIAL=false: schedule post 5 min ahead, verify post appears on Page/IG account |
| Mock mode banner appears in UI when MOCK_SOCIAL=true | SOCIAL-01 | Visual/UI verification | Open 8_Publicaciones.py, confirm `st.info` banner visible at top |
| Unified action confirmation modal shows social addendum | SOCIAL-03 | Visual/UI verification | Check Step 3 checkbox ON triggers confirmation copy with social clause |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
