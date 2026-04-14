# GSD Debug Knowledge Base

Resolved debug sessions. Used by `gsd-debugger` to surface known-pattern hypotheses at the start of new investigations.

---

## n8n-workflow-import-property-option-error — n8n import fails with "Could not find property option" due to Switch v3/IF v2 format mismatches
- **Date:** 2026-04-10
- **Error patterns:** Could not find property option, n8n import, Switch v3, IF v2, operator, equal, notEqual, equals, notEquals, workflow import
- **Root cause:** Switch v3 nodes used incompatible v2 parameter format (mode/dataType/value1/value2 instead of rules.values[].conditions), and IF v2 nodes used wrong operator names ("equal"/"notEqual" instead of "equals"/"notEquals"). Both cause n8n to fail looking up property options in the node schema during import.
- **Fix:** Converted Switch nodes to v3 conditions-based format with rules.values[] containing conditions objects. Fixed all IF node operator operations to use correct names (equals/notEquals/notEmpty). Added fallback output connections for Switch v3 extra output.
- **Files changed:** n8n/workflows/sub-booking-flow.json, n8n/workflows/whatsapp-chatbot.json
---

## campaign-blast-loop-routing — SplitInBatches v3 output wiring inverted, $() node reference by id, and Wait unit "ms" invalid
- **Date:** 2026-04-13
- **Error patterns:** SplitInBatches, Loop Recipients, Finalize Status, Check Cancelled, loop skipped, Referenced node doesn't exist, Cannot assign to read only property 'name' of object 'Error', Wait node, Invalid wait unit, unit ms, delay_ms, jitter, campaign blast, n8n Wait
- **Root cause:** Three sequential bugs in campaign-blast.json: (1) Loop Recipients SplitInBatches v3 outputs swapped — output[0] (done) wired to Check Cancelled and output[1] (loop) wired to Finalize Status, causing the per-item branch to jump straight to completion; (2) Merge Recipient and Status Code node referenced the loop via $('loop-recipients') (the internal id) instead of $('Loop Recipients') (the display name) — n8n's $() proxy resolves by name only; (3) Wait Jitter node used unit="ms" which is not a valid n8n Wait unit (only 'seconds','minutes','hours','days' are accepted), while Compute Jitter emitted delay_ms 3000-8000.
- **Fix:** (1) Swapped Loop Recipients connections so output[0] → Finalize Status, output[1] → Check Cancelled. (2) Changed $('loop-recipients') to $('Loop Recipients') in Merge Recipient and Status. (3) Compute Jitter now also emits delay_seconds = Math.ceil(delay_ms/1000); Wait Jitter now uses amount={{ $json.delay_seconds }} and unit="seconds", preserving 3-8s jitter semantics.
- **Files changed:** n8n/workflows/campaign-blast.json
---
