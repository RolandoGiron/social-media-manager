---
phase: 5
slug: campaign-blast
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-12
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `admin-ui/src/pytest.ini` |
| **Quick run command** | `docker exec clinic-admin python -m pytest tests/test_campaigns.py -x -q` |
| **Full suite command** | `docker exec clinic-admin python -m pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `docker exec clinic-admin python -m pytest tests/test_campaigns.py -x -q`
- **After every plan wave:** Run `docker exec clinic-admin python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 0 | WA-02 | — | `fetch_patients_by_tags` returns only patients matching selected tags | unit | `docker exec clinic-admin python -m pytest tests/test_campaigns.py::TestFetchPatientsByTags -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 0 | WA-02 | — | `insert_campaign_recipients` batch inserts correct count | unit | `docker exec clinic-admin python -m pytest tests/test_campaigns.py::TestInsertCampaignRecipients -x` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 0 | WA-03 | T-05-01 | `insert_campaign` creates row with status='pending'; no send without confirm | unit | `docker exec clinic-admin python -m pytest tests/test_campaigns.py::TestInsertCampaign -x` | ❌ W0 | ⬜ pending |
| 05-01-04 | 01 | 0 | WA-04 | — | `cancel_campaign` sets status='cancelled' and cancelled_at | unit | `docker exec clinic-admin python -m pytest tests/test_campaigns.py::TestCancelCampaign -x` | ❌ W0 | ⬜ pending |
| 05-01-05 | 01 | 0 | WA-02 | — | `fetch_campaign_status` returns correct sent_count/total | unit | `docker exec clinic-admin python -m pytest tests/test_campaigns.py::TestFetchCampaignStatus -x` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 1 | WA-02 | — | n8n workflow JSON structure — webhook path, loop node present, cancellation IF check | manual | inspect `n8n/workflows/campaign-blast.json` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `admin-ui/src/tests/test_campaigns.py` — stubs for WA-02, WA-03, WA-04 DB function unit tests (TestFetchPatientsByTags, TestInsertCampaignRecipients, TestInsertCampaign, TestCancelCampaign, TestFetchCampaignStatus)
- [ ] No new `pytest.ini` or `conftest.py` needed — existing `admin-ui/src/pytest.ini` covers the test directory

*Note: n8n workflow validation is manual-only (no test runner can inspect n8n JSON automatically).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| n8n campaign-blast workflow JSON structure — webhook path `/webhook/campaign-blast`, Loop Over Items node present, IF-node cancellation check per iteration | WA-02 | n8n workflows are configured in n8n UI; no test runner can execute the workflow end-to-end without sending real WhatsApp messages | Inspect `n8n/workflows/campaign-blast.json`; verify webhook trigger path, loop node type, and IF node routing cancelled → No-Op |
| Confirmation gate UI shows exact recipient count before send | WA-03 | Streamlit UI interaction requires visual inspection | Open admin UI → Campañas page → select segment → verify count shown in confirmation message matches DB query result before clicking confirm |
| Cancel button halts remaining sends | WA-04 | Requires live Evolution API interaction | Start a broadcast of 5+ recipients; click Cancel after first send; verify remaining recipients in `campaign_recipients` have status='pending' (not 'sent') |
| 3-8 second jitter delay between sends | WA-02 | Requires timing measurement of actual sends | Inspect n8n execution log timing between send iterations; confirm no sub-1s gaps |
| phone_normalized format accepted by Evolution API | A2 | Requires live API call | Send a 1-recipient test blast; check Evolution API response for format errors |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
