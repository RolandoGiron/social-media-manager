---
status: partial
phase: 02-whatsapp-core
source: [02-VERIFICATION.md]
started: 2026-03-28T12:00:00Z
updated: 2026-03-28T12:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. QR scan and connect via admin UI
expected: Admin opens the WhatsApp page in the admin UI, a QR code is displayed, scanning it with WhatsApp shows the session as Connected (green dot in sidebar)
result: [pending]

### 2. Sidebar status persistence across pages
expected: After WhatsApp page shows connected, navigating to Dashboard still shows green dot with clinic number in sidebar
result: [pending]

### 3. Disconnect alert delivery to admin
expected: Simulating a disconnect (curl POST with state=close to n8n webhook) results in a WhatsApp message received on ADMIN_WHATSAPP_NUMBER within 5 minutes
result: [pending]

### 4. Send/receive validation (ROADMAP Success Criterion 4)
expected: A message sent via n8n workflow is received on the clinic WhatsApp number; an inbound message from the clinic number triggers the messages-upsert webhook
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
