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
