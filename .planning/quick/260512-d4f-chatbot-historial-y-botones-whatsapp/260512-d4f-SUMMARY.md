---
status: complete
---

# Quick Task 260512-d4f Summary

## What was done

### Task 1: Conversation history in LLMs

**`n8n/workflows/whatsapp-chatbot.json`**
- `Read Conversation State`: SQL query now includes a `recent_messages` subquery — fetches the 5 most recent messages for the conversation, returned as a JSON array in chronological order.
- `Extract Message Fields`: handles `buttonsResponseMessage` in the message_text expression; adds a new `button_id` field.
- `Merge Conversation Data`: maps button IDs (`promo_precios`, `horarios_ubicacion`, `agendar_cita`) to natural language before the text flows into intent classification.
- `Format FAQs for LLM`: adds `conversation_history` field built from `recent_messages`; also passes `mergedConv.message_text` (already button-mapped) instead of raw `extractFields.message_text`.
- `Check FAQ Triggers Handoff`: when `is_handoff === true`, sets `send_buttons: true` and `new_state: 'awaiting_intent'` instead of escalating to `human_handoff`. Response text is cleared (buttons replace the text message).
- `Send WA Message` node: added `send_buttons` to both `schema` and `value` mapping.

**`n8n/workflows/sub-classify-intent.json`**
- `Classify Intent (OpenAI)`: system prompt now includes conversation history section before the knowledge base context.
- `Set Intent Output`: passes `conversation_history` field through to downstream nodes.

**`n8n/workflows/sub-faq-answer.json`**
- `Generate FAQ Answer (OpenAI)`: system prompt includes conversation history; changed "not found" sentinel from the ambiguous phrase "No tengo esa información..." to the token `NEEDS_CLARIFICATION` — eliminates the accent-insensitive string-match bug that made `is_handoff` always false.
- `Set FAQ Answer Output`: `is_handoff` now checks `trim() === 'NEEDS_CLARIFICATION'` (exact match, no accent issues). `response_text` is empty string when `NEEDS_CLARIFICATION`.

### Task 2: Reply buttons fallback

**`n8n/workflows/sub-send-wa-message.json`** — full rewrite
- Added `Send Buttons?` IF node that branches on `send_buttons` field.
- `true` branch → `Send Buttons Message` (HTTP POST `/message/sendButtons/{instance}`) with 3 buttons: "Precios / Promo", "Horarios / Ubicación", "Agendar cita".
- `false` branch → existing `Send Text Message` node (unchanged behavior).

## Bug fixed
Pre-existing: `is_handoff` was always `false` because the check looked for `'No tengo esa informacion'` (no accent) while the LLM returned `'información'` (with accent). Fixed by switching to `NEEDS_CLARIFICATION` sentinel.

## Files changed
- `n8n/workflows/whatsapp-chatbot.json`
- `n8n/workflows/sub-classify-intent.json`
- `n8n/workflows/sub-faq-answer.json`
- `n8n/workflows/sub-send-wa-message.json`
