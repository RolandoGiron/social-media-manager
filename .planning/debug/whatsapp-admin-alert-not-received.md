---
status: awaiting_human_verify
trigger: "No WhatsApp message received by admin after QR connection"
created: 2026-04-01T00:00:00Z
updated: 2026-04-01T00:02:00Z
---

## Current Focus

hypothesis: CONFIRMED - Workflow only handled disconnect states, not connection success
test: Review workflow logic
expecting: state=="open" after QR scan takes false branch (noOp)
next_action: Await human verification after re-importing workflow into n8n

## Symptoms

expected: After scanning QR and connecting Evolution API, admin receives a WhatsApp confirmation message at +50378422032
actual: QR scan worked (connection established), but no WhatsApp message was received
errors: No error — workflow silently ignores "open" state
reproduction: Connect Evolution API via QR scan on WhatsApp page
started: Phase 2 completed; never received a connection confirmation

## Eliminated

## Evidence

- timestamp: 2026-04-01T00:02:00Z
  checked: .env
  found: ADMIN_WHATSAPP_NUMBER=+50378422032 — correct El Salvador format
  implication: Admin number is correctly configured in environment

- timestamp: 2026-04-01T00:02:00Z
  checked: n8n/workflows/whatsapp-connection-update.json
  found: Workflow had If node checking for state=="close" OR state=="connecting". True=send alert, False=noOp. When QR succeeds, state="open" hits False branch (noOp), so no message sent.
  implication: Root cause confirmed — no handler for successful connection

- timestamp: 2026-04-01T00:02:00Z
  checked: .env.example
  found: Placeholder numbers used Mexico format (+521234567890)
  implication: Updated to El Salvador format for consistency

## Resolution

root_cause: The n8n workflow only handled disconnect/connecting states. When QR scan succeeds and state becomes "open", it hit the false branch of the If node (a noOp), so no message was ever sent.
fix: Replaced If node with Switch node (3 outputs): disconnect (close/connecting) sends disconnect alert, connected (open) sends success confirmation message, fallback goes to noOp. Also updated .env.example to use El Salvador phone format.
verification: Structural verification complete. Requires re-import into n8n and QR reconnection test.
files_changed: [n8n/workflows/whatsapp-connection-update.json, .env.example]
