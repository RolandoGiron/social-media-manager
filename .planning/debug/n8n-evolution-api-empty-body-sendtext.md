---
status: awaiting_human_verify
trigger: "n8n workflow sends POST to Evolution API /message/sendText/clinic-main with an empty body {} — missing required number and text fields — causing a 400 Bad Request error."
created: 2026-04-11T00:00:00Z
updated: 2026-04-11T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - Paired-item tracking breaks through Postgres nodes between "Merge All Response Paths" and "Send WA Message". The expressions use $('Merge All Response Paths').item.json which relies on paired items, but the two Postgres nodes (Update Conversation State, Insert Bot Response Message) create new output items from SQL RETURNING, breaking the pairing chain. This causes .item.json to resolve to undefined, making remote_jid and response_text undefined, and JSON.stringify({number: undefined, text: undefined}) produces {}.
test: Change .item to .first() in the Send WA Message node's workflowInputs expressions.
expecting: The sub-workflow receives the correct remote_jid and response_text values.
next_action: Apply fix to whatsapp-chatbot.json

## Symptoms

expected: The n8n chatbot workflow sends a WhatsApp text message back to the user who initiated the conversation, with the correct phone number (remote_jid) and AI-generated response text.
actual: The HTTP Request node POSTs to http://evolution-api:8080/message/sendText/clinic-main with body: {} — empty. Evolution API returns 400 with: "instance requires property \"number\"" and "instance requires property \"text\"".
errors: |
  400 - "{\"status\":400,\"error\":\"Bad Request\",\"response\":{\"message\":[[\"instance requires property \\\"number\\\"\",\"instance requires property \\\"text\\\"\"]]}}"
reproduction: Trigger the chatbot by sending a WhatsApp message. The flow processes it but fails at the send-response step.
started: Ongoing issue — the send message node never correctly passes the number/text parameters.

## Eliminated

## Evidence

- timestamp: 2026-04-11T00:01:00Z
  checked: sub-send-wa-message.json HTTP Request node body configuration
  found: jsonBody uses JSON.stringify({ number: $json.remote_jid, text: $json.response_text }). If both are undefined, JSON.stringify omits them, producing {}.
  implication: The sub-workflow itself is correctly configured -- the problem is upstream (data not arriving).

- timestamp: 2026-04-11T00:02:00Z
  checked: whatsapp-chatbot.json "Send WA Message" node workflowInputs expressions
  found: Uses $('Merge All Response Paths').item.json.remote_jid (and .response_text, .instance_name, .api_key). The .item accessor relies on n8n paired-item tracking.
  implication: If paired-item chain is broken, .item returns undefined silently.

- timestamp: 2026-04-11T00:03:00Z
  checked: Data flow between "Merge All Response Paths" and "Send WA Message"
  found: Two Postgres nodes sit between them: "Update Conversation State" (RETURNING id, state, response_text) and "Insert Bot Response Message" (RETURNING id). Both create new output items from SQL results, not passing through input items.
  implication: Postgres executeQuery nodes with RETURNING clauses produce new items that break paired-item linkage. $('Merge All Response Paths').item cannot resolve back through these nodes.

- timestamp: 2026-04-11T00:04:00Z
  checked: Whether .first() would be a safe alternative to .item
  found: The workflow processes one message at a time (single item flow). "Merge All Response Paths" always outputs exactly one item per execution.
  implication: Using .first() instead of .item is safe and does not depend on paired-item tracking.

## Resolution

root_cause: n8n paired-item tracking breaks when data flows through Postgres executeQuery nodes that use RETURNING clauses. The "Send WA Message" node referenced $('Merge All Response Paths').item.json, but two Postgres nodes between them (Update Conversation State, Insert Bot Response Message) create new output items from SQL results, severing the paired-item chain. The .item accessor silently returns undefined when pairing is broken, causing remote_jid and response_text to be undefined. JSON.stringify({number: undefined, text: undefined}) omits undefined values, producing the empty body {}.
fix: Changed all $('NodeName').item.json references to $('NodeName').first().json in whatsapp-chatbot.json. The .first() accessor does not depend on paired-item tracking -- it simply gets the first output item of the referenced node. This is safe because the workflow processes one message at a time (single item flow). Applied to references for Merge All Response Paths, Merge Conversation Data, and Extract Message Fields.
verification: Awaiting human verification -- user needs to send a WhatsApp message and confirm the bot responds correctly.
files_changed: [n8n/workflows/whatsapp-chatbot.json]
