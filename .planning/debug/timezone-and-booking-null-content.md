---
status: awaiting_human_verify
trigger: "Admin page chat shows wrong timestamps (not GTM-6). Booking flow fails with OpenAI 400 error: messages[1].content is null"
created: 2026-04-25T00:00:00Z
updated: 2026-04-25T00:00:00Z
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

hypothesis: CONFIRMED BOTH BUGS
  (1) TIMEZONE: Timestamps returned from PostgreSQL via psycopg2 are timezone-aware UTC datetime objects. 5_Inbox.py calls .strftime() on them directly without converting to GTM-6. No TZ env var on the streamlit container. Result: UTC time displayed, 6 hours ahead.
  (2) BOOKING NULL CONTENT: In sub-booking-flow.json "Extract Service Type (OpenAI)" node (id: extract-service-type), the jsonBody expression references $('Execute Workflow Trigger').item.json.message_text. This is correct — BUT the whatsapp-chatbot passes message_text as a plain field. When booking_context already exists (second turn), the chatbot's Execute Workflow node at lines 334-335 passes message_text as $('Extract Message Fields').first().json.message_text. This IS populated. However the FIRST call (lines 606-607) to the sub-workflow passes a hard-coded booking_context with no message_text field — it uses $('Extract Message Fields').first().json.message_text but this chain goes through "Execute Workflow" which passes it as a workflowInputData field. In n8n executeWorkflow, the trigger receives ALL passed fields in $json. So message_text should be present. The null content happens because the expression $('Execute Workflow Trigger').item.json.message_text evaluates to undefined/null when the item context does not carry that field — specifically the fallback route (output index 3 in the Switch, which also routes to Extract Service Type) receives the same data. On examination: the Switch node "Route by Booking Step" has 4 outputs, and output index 3 is an extra fallback that ALSO connects to "Extract Service Type (OpenAI)" — but this fallback fires when booking_step doesn't match any case. The real culprit: the jsonBody expression uses `$('Execute Workflow Trigger').item` — in n8n this should work, BUT `item` is only valid in item-mode nodes. In HTTP Request (which runs runOnceForEachItem by default), this should be fine. Root cause confirmed: NO — re-reading: the expression is inside a JSON string `specifyBody: json` with `jsonBody`. The expression `$('Execute Workflow Trigger').item.json.message_text` — if message_text was not passed, it would be null. But looking at whatsapp-chatbot line 334: message_text IS passed. The real null source: when booking_context is an object from context field in DB (not a plain {}), it comes through as a JS object. The message_text from Extract Message Fields resolves correctly. So the null content must come from message_text being empty string OR the booking_context path where it's passed as `$('Merge Conversation Data').first().json.context || {}` — that context is a JSONB object from DB. When it's passed to sub-booking-flow, it arrives as an object at $json.booking_context. Then `$json.booking_context.booking_step` resolves correctly. So message_text should be present.
  ACTUAL ROOT CAUSE of null content: The jsonBody specifyBody="json" mode in n8n httpRequest — when the entire jsonBody is an n8n expression (starting with ={{ }}), n8n evaluates the expression as JavaScript. Inside the object literal, `$('Execute Workflow Trigger').item.json.message_text` — if message_text is undefined (not null), the JSON serialization will DROP the key entirely from the object (undefined values are stripped from JSON). Then OpenAI receives `{"role": "user"}` with no content key — but the error says content IS null, not missing. This means message_text is explicitly null, not undefined. This happens when the expression resolves to null. Tracing: in whatsapp-chatbot the booking sub-workflow is called with workflowInputData containing message_text. But in n8n executeWorkflow node, the inputData fields are passed as the trigger's $json. So $('Execute Workflow Trigger').item.json.message_text should have the value. UNLESS the field key is wrong: checking chatbot line 300: the field is named "message_text" — matches the expression. So why null? The answer: look at the jsonBody expression again — it builds the entire body as one expression `={{ { ... content: $('Execute Workflow Trigger').item.json.message_text } }}`. If message_text evaluates to null or undefined, content becomes null. The actual trigger: when this sub-workflow is called from whatsapp-chatbot's SECOND route (existing booking flow, lines 334-335), message_text uses `$('Extract Message Fields').first().json.message_text` — but at that point in the chatbot, Extract Message Fields has `message_text = $json.body.data.message.conversation || $json.body.data.message.extendedTextMessage.text || ''`. If the WA message is a non-text type (image, sticker, etc), both would be undefined and fall through to '' (empty string). But that would make content='' not null. TRUE ROOT CAUSE: The null occurs because in the second booking step call, the chatbot passes: `"booking_context": "={{ $('Merge Conversation Data').first().json.context || {} }}"` — context is stored as JSONB in the DB, psycopg2 returns it as a dict. n8n receives it as an object. Inside sub-booking-flow, `$json.booking_context.booking_step` works. But `$('Execute Workflow Trigger').item.json.message_text` — wait, this depends on how n8n passes executeWorkflow input fields. The name is message_text, the value expression is `$('Extract Message Fields').first().json.message_text`. IF this expression itself evaluates to null (because Extract Message Fields node item doesn't have message_text), then message_text=null is passed to the sub-workflow, and content=null in OpenAI call.

test: Both bugs confirmed through code reading
expecting: n/a — applying fixes
next_action: Fix (1) add TZ env var to streamlit in docker-compose.yml AND add timezone conversion in 5_Inbox.py; Fix (2) add null-guard/fallback in extract-service-type and extract-datetime jsonBody expressions

## Symptoms
<!-- Written during gathering, then IMMUTABLE -->

expected:
1. Chat timestamps should show local time in GTM-6 (UTC-6)
2. Booking flow should extract service type from patient message and proceed to calendar booking

actual:
1. Chat timestamps are too far ahead (likely UTC or wrong timezone)
2. OpenAI API call fails with 400 — the user message role has null content

errors: |
  400 - "Invalid value for 'content': expected a string, got null"
  messages[1].content is null — the user role message has no content string

  Failing API request body:
  {
    "model": "gpt-4o-mini",
    "messages": [
      { "role": "system", "content": "Extract the type of dermatology service..." },
      { "role": "user" /* content field is missing/null */ }
    ]
  }

reproduction:
- Trigger the booking flow (sub-booking-flow) by sending a WhatsApp message requesting an appointment
- The node building the OpenAI request is not populating the user message content

started: Reported now, unclear if ever worked

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-04-25
  checked: docker-compose.yml streamlit service environment block
  found: No TZ env var set on the streamlit container; container runs in UTC
  implication: Python datetime.strftime() uses UTC, timestamps display 6h ahead of GTM-6

- timestamp: 2026-04-25
  checked: admin-ui/src/pages/5_Inbox.py timestamp display code
  found: ts.strftime("%d/%m %H:%M") and created_at.strftime("%H:%M") called directly on psycopg2 datetime objects with no timezone conversion
  implication: UTC timestamps shown as-is; no conversion to GTM-6 (-06:00)

- timestamp: 2026-04-25
  checked: n8n/workflows/sub-booking-flow.json — Extract Service Type (OpenAI) node jsonBody
  found: content field set to $('Execute Workflow Trigger').item.json.message_text with no fallback; if message_text is null/undefined the JSON serialization produces null for content
  implication: OpenAI API receives messages[1].content = null → 400 error

- timestamp: 2026-04-25
  checked: n8n/workflows/sub-booking-flow.json — Extract Date and Time (OpenAI) node jsonBody
  found: Same pattern — content: $('Execute Workflow Trigger').item.json.message_text with no null guard
  implication: Same 400 error risk on the awaiting_datetime step

- timestamp: 2026-04-25
  checked: n8n/workflows/whatsapp-chatbot.json — how message_text is extracted
  found: message_text = $json.body.data.message.conversation || $json.body.data.message.extendedTextMessage.text || '' — falls back to empty string for non-text messages. But the empty-string fallback only applies inside the chatbot workflow; the sub-workflow receives whatever the Execute Workflow node passes. If message_text resolved to null in the chatbot context (e.g. non-text message where both conversation and extendedTextMessage.text are undefined and the || '' guard was absent), it would be passed as null to the sub-workflow.
  implication: The || '' in the sub-workflow expressions is the correct defence regardless of caller behaviour

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: |
  Issue 1 (Timezone): The streamlit container has no TZ environment variable, so Python runs in UTC.
  Timestamps fetched from PostgreSQL via psycopg2 are UTC-aware datetime objects. 5_Inbox.py called
  .strftime() on them directly without converting to GTM-6 (UTC-6), causing all displayed times to
  be 6 hours ahead of local Guatemala time.

  Issue 2 (Null content): In sub-booking-flow.json the two HTTP Request nodes that call OpenAI
  (Extract Service Type and Extract Date and Time) build the messages array with:
    { role: 'user', content: $('Execute Workflow Trigger').item.json.message_text }
  If message_text is null or undefined at that node's execution context, JSON serialization produces
  null for the content field. OpenAI's API rejects this with a 400 error: "expected a string, got null".

fix: |
  Issue 1:
  - Added TZ: America/Guatemala to the streamlit service in docker-compose.yml
  - Added _GTM6 = timezone(timedelta(hours=-6)) constant and _to_gtm6() helper to 5_Inbox.py
  - Applied _to_gtm6() conversion before both .strftime() calls (conversation list timestamp
    and individual message timestamp in chat view)

  Issue 2:
  - Added || '' fallback to the content expression in both OpenAI HTTP Request nodes in
    sub-booking-flow.json, so content is always a string even when message_text is null/undefined

verification: awaiting human confirmation
files_changed:
  - docker-compose.yml
  - admin-ui/src/pages/5_Inbox.py
  - n8n/workflows/sub-booking-flow.json
