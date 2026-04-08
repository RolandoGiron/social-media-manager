---
phase: 4
slug: ai-chatbot-appointment-booking
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-08
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | admin-ui/src/tests/ |
| **Quick run command** | `pytest admin-ui/src/tests/ -x -q` |
| **Full suite command** | `pytest admin-ui/src/tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest admin-ui/src/tests/ -x -q`
- **After every plan wave:** Run `pytest admin-ui/src/tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-xx-xx | TBD  | TBD  | BOT-01      | integration | `pytest admin-ui/src/tests/ -x -q` | ❌ W0 | ⬜ pending |
| 4-xx-xx | TBD  | TBD  | BOT-02      | integration | `pytest admin-ui/src/tests/ -x -q` | ❌ W0 | ⬜ pending |
| 4-xx-xx | TBD  | TBD  | BOT-03      | integration | `pytest admin-ui/src/tests/ -x -q` | ❌ W0 | ⬜ pending |
| 4-xx-xx | TBD  | TBD  | BOT-04      | integration | `pytest admin-ui/src/tests/ -x -q` | ❌ W0 | ⬜ pending |
| 4-xx-xx | TBD  | TBD  | CAL-01      | integration | `pytest admin-ui/src/tests/ -x -q` | ❌ W0 | ⬜ pending |
| 4-xx-xx | TBD  | TBD  | CAL-02      | integration | `pytest admin-ui/src/tests/ -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `admin-ui/src/tests/test_chatbot.py` — stubs for BOT-01, BOT-02, BOT-03, BOT-04
- [ ] `admin-ui/src/tests/test_calendar.py` — stubs for CAL-01, CAL-02
- [ ] `admin-ui/src/tests/conftest.py` — shared fixtures

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| WhatsApp typing indicator visible during LLM processing | BOT-01 | Requires live WhatsApp connection and visual observation | Send test message, observe "typing..." indicator in WhatsApp before response arrives |
| Google Calendar appointment appears in clinic calendar | CAL-01 | Requires live Google Calendar API + real calendar | Request appointment via WhatsApp, verify event appears in Google Calendar with correct time |
| Human handoff flag visible in admin inbox | BOT-04 | Requires UI interaction | Send unanswerable question, verify conversation flagged in admin UI |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
