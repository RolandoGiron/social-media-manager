---
status: resolved
trigger: "n8n workflow import error - Could not find property option"
created: 2026-04-10T00:00:00Z
updated: 2026-04-10T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - Two root causes: (1) Switch v3 nodes used old v2 parameter format, (2) IF v2 nodes used wrong operator names (equal/notEqual instead of equals/notEquals)
test: Fix applied to both files - needs human verification via n8n import
expecting: Both workflows import without error
next_action: User verifies import in n8n UI

## Symptoms

expected: Successfully import sub-booking-flow.json and whatsapp-chatbot.json into n8n UI
actual: Error "Problem importing workflow Could not find property option"
errors: "Problem importing workflow Could not find property option"
reproduction: Try to import the JSON workflow files via n8n UI import
started: After recent edits (commits bb68abb, 3d3f850, 9e6fa6d)

## Eliminated

- hypothesis: Previous fix (bb68abb) removed leftValue from conditions.options — that was a valid sub-issue but did not fully resolve the import error
  evidence: Error persisted after that commit
  timestamp: 2026-04-10

## Evidence

- timestamp: 2026-04-10
  checked: Switch node parameters in both workflow files
  found: Switch nodes declared typeVersion 3 but used old v2 format (mode/dataType/value1/rules.rules[].value2/output). Switch v3 requires rules.values[].conditions structure with leftValue/rightValue/operator per condition.
  implication: n8n UI cannot find the property definitions for v2-style parameters in the v3 schema, causing "Could not find property option"

- timestamp: 2026-04-10
  checked: IF node operator operation names
  found: All IF v2 nodes used "equal"/"notEqual" instead of the correct "equals"/"notEquals". n8n IF v2 conditions system uses "equals"/"notEquals"/"notEmpty" as operation values.
  implication: Invalid operation names mean n8n cannot find the operator option in its dropdown schema, contributing to the same error

- timestamp: 2026-04-10
  checked: Switch fallback output connections
  found: Old format used numeric fallbackOutput (0 or 2) routing to existing rule outputs. Switch v3 uses "extra" fallback which needs its own connection entry.
  implication: Added extra output connections for fallback routing to preserve original behavior

## Resolution

root_cause: Two issues in workflow JSON files: (1) Switch v3 nodes used incompatible v2 parameter format (mode/dataType/value1/value2 instead of rules.values[].conditions), (2) IF v2 nodes used wrong operator names ("equal"/"notEqual" instead of "equals"/"notEquals"). Both cause n8n to fail looking up property options in the node schema during import.
fix: Converted Switch nodes to v3 conditions-based format with rules.values[] containing conditions objects. Fixed all IF node operator operations to use correct names (equals/notEquals/notEmpty). Added fallback output connections for Switch v3 extra output.
verification: Both JSON files validate as valid JSON. All operator values confirmed correct. Connection counts match expected outputs (rules + fallback).
files_changed: [n8n/workflows/sub-booking-flow.json, n8n/workflows/whatsapp-chatbot.json]
