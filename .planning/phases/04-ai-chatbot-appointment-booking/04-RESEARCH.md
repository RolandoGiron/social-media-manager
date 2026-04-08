# Phase 4: AI Chatbot + Appointment Booking - Research

**Researched:** 2026-04-08
**Domain:** n8n chatbot workflow + OpenAI LLM + Google Calendar + Streamlit inbox UI
**Confidence:** MEDIUM-HIGH

## Summary

Phase 4 builds the core chatbot pipeline: Evolution API receives WhatsApp messages, n8n orchestrates intent classification and response generation via OpenAI gpt-4o-mini, PostgreSQL tracks conversation state, and Google Calendar handles appointment booking. The admin monitors conversations and sends manual replies from a new Streamlit inbox page. A knowledge base table in PostgreSQL stores FAQ content editable from Streamlit.

The technical risk is concentrated in two areas: (1) the n8n workflow complexity of managing a multi-state chatbot with sub-workflows, and (2) Google Calendar authentication on self-hosted n8n, where service account support may require OAuth2 instead. All other components (Evolution API presence/send endpoints, OpenAI via n8n, Streamlit chat UI) are well-documented and straightforward.

**Primary recommendation:** Build the n8n chatbot as a main webhook workflow that dispatches to sub-workflows (classify-intent, faq-answer, booking-flow, send-wa-message). Use OpenAI gpt-4o-mini with function-calling style prompts for structured intent extraction. Use Google Calendar OAuth2 credentials (not service account) unless service account is confirmed working on the self-hosted n8n version deployed.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** OpenAI API, model `gpt-4o-mini`. n8n native OpenAI node. No Ollama.
- **D-02:** API key as n8n credential. All LLM calls through n8n, NOT from Streamlit.
- **D-03:** FAQs in PostgreSQL `knowledge_base` table (id, pregunta, respuesta, categoria, is_active, created_at, updated_at). Categories: horarios, ubicacion, precios, servicios, general.
- **D-04:** Streamlit page `6_Knowledge_Base.py` for FAQ management. Simple table editor.
- **D-05:** n8n loads active FAQs via SELECT at each conversation turn, injects into LLM system prompt. No vector store.
- **D-06:** Natural conversation for booking (no numbered menus/list messages).
- **D-07:** Bot collects: tipo de servicio, fecha/hora preferida. Auto-fills name from patients table if phone exists; asks name if not.
- **D-08:** Bot queries Google Calendar for availability, presents 2-3 options, books on selection.
- **D-09:** On booking: create GCal event, insert appointments row (with google_event_id), send WhatsApp confirmation.
- **D-10:** State machine via `conversations` table. States: new -> awaiting_intent -> faq_flow / booking_flow -> human_handoff -> closed. No schema changes.
- **D-11:** `context JSONB` stores in-progress booking data.
- **D-12:** Replace `whatsapp-message-stub.json` with `whatsapp-chatbot.json`. Sub-workflow pattern: classify-intent, faq-answer, booking-flow, send-wa-message.
- **D-13:** Typing indicator via Evolution API presence endpoint before LLM call.
- **D-14:** Streamlit `5_Inbox.py` with split-pane `st.columns([1, 2])`. Left: conversation list with status badges. Right: chat history + reply area.
- **D-15:** `human_handoff` conversations shown at top with `[!]` indicator.
- **D-16:** "Cerrar conversacion" button sets state to 'closed'.
- **D-17:** Auto-refresh every 10 seconds (st_autorefresh or time.sleep + st.rerun pattern).

### Claude's Discretion
- Exact LLM system prompt wording (FAQ injection format, persona instructions)
- Evolution API endpoint for typing indicator presence
- Concurrent message handling (optimistic locking on state update)
- Streamlit chat rendering approach (st.chat_message vs custom)
- Google Calendar working hours configuration

### Deferred Ideas (OUT OF SCOPE)
- Appointment reminders (24h/1h) -- CAL-03, Phase 7
- Automatic conversation close after inactivity -- v2
- WhatsApp list messages / button menus for booking
- MiniMax API integration
- Multi-language support
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BOT-01 | Chatbot responds to FAQs (hours, location, prices, services) using knowledge base | knowledge_base table + system prompt injection pattern; gpt-4o-mini via n8n OpenAI node |
| BOT-02 | Chatbot escalates to human when no answer found or medical complaint detected | State machine transition to `human_handoff`; handoff message template; n8n Switch node on LLM classification |
| BOT-03 | Admin inbox with full conversation history and manual reply | Streamlit st.chat_message for rendering; direct PG reads for messages; Evolution API send_text_message for replies |
| BOT-04 | Typing indicator while LLM processes | Evolution API POST /chat/sendPresence/{instance} with presence: "composing" |
| CAL-01 | Book appointment via Google Calendar without human intervention | n8n Google Calendar node (check availability + create event); OAuth2 credentials |
| CAL-02 | WhatsApp confirmation with date, time, clinic details | Evolution API sendText after GCal event creation; message template with placeholders |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Infrastructure:** Single VPS Hostinger with Docker Compose. All services on one stack.
- **WhatsApp:** Evolution API v2 (unofficial). Pin to specific release tag.
- **LLM:** OpenAI gpt-4o-mini (per CLAUDE.md stack patterns for limited VPS).
- **Admin UI:** Streamlit with Caddy basic auth. No ORM -- direct psycopg2 queries.
- **Anti-Pattern:** Admin UI must NOT write actions directly to DB for side effects. Use n8n webhooks for actions. BUT: the inbox manual reply sends directly to Evolution API from Streamlit (per D-14 code_context), which is acceptable since it's a simple message send, not a workflow trigger.
- **Anti-Pattern:** Do NOT store chatbot state in n8n execution. Use PostgreSQL conversations table.
- **Workflow:** Separate n8n workflows per domain. Sub-workflows for shared operations.

## Standard Stack

### Core (already in project)
| Library/Service | Version | Purpose | Notes |
|----------------|---------|---------|-------|
| n8n | 1.x (latest stable) | Chatbot workflow orchestration | OpenAI node, Google Calendar node, Postgres node, HTTP Request node |
| OpenAI API | gpt-4o-mini | Intent classification + FAQ answers + booking conversation | Via n8n native OpenAI Chat node |
| Evolution API | v2.x (pinned tag) | WhatsApp message send/receive + typing indicator | POST /chat/sendPresence, POST /message/sendText |
| PostgreSQL | 16.x | Conversation state, messages, appointments, knowledge_base | Existing schema + new knowledge_base table |
| Streamlit | 1.35+ | Inbox page + Knowledge Base editor | st.chat_message for chat UI rendering |

### Supporting (new for this phase)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| streamlit-autorefresh | latest | Auto-refresh inbox every 10s | For D-17 auto-refresh. Alternative: time.sleep + st.rerun |
| Google Calendar API | v3 | Check availability + create events | Via n8n Google Calendar node with OAuth2 credential |

**Installation (Streamlit side):**
```bash
# Add to admin-ui/requirements.txt
streamlit-autorefresh
```

**n8n credentials to configure:**
1. OpenAI API credential (OPENAI_API_KEY)
2. Google Calendar OAuth2 credential (client_id + client_secret from Google Cloud Console)

## Architecture Patterns

### n8n Workflow Structure
```
n8n/workflows/
  whatsapp-chatbot.json          # Main: webhook -> state read -> route -> state write -> reply
  sub-classify-intent.json       # Sub: OpenAI call to classify intent (faq/booking/handoff/unknown)
  sub-faq-answer.json            # Sub: Load KB + OpenAI call to answer FAQ
  sub-booking-flow.json          # Sub: Multi-turn booking (collect data, check GCal, book)
  sub-send-wa-message.json       # Sub: Send typing indicator + message via Evolution API
```

### Main Chatbot Workflow Flow
```
Webhook (MESSAGES_UPSERT)
  |-> Filter: skip fromMe=true messages
  |-> Postgres: SELECT conversation WHERE wa_contact_id FOR UPDATE
  |-> IF no conversation: INSERT new conversation (state='new')
  |-> Switch on state:
       |-> 'human_handoff' -> store message only, skip bot
       |-> 'closed' -> reopen conversation (set state='new'), continue
       |-> 'new'/'awaiting_intent' -> Execute sub-classify-intent
       |-> 'faq_flow' -> Execute sub-faq-answer
       |-> 'booking_flow' -> Execute sub-booking-flow
  |-> Postgres: UPDATE conversation state + context
  |-> Execute sub-send-wa-message (typing + reply)
```

### Conversation State Machine
```
new -> awaiting_intent (on first message received)
awaiting_intent -> faq_flow (intent = FAQ)
awaiting_intent -> booking_flow (intent = booking)
awaiting_intent -> human_handoff (intent = complaint/medical/unknown)
faq_flow -> awaiting_intent (after FAQ answered, ready for next question)
booking_flow -> awaiting_intent (after booking complete or cancelled)
booking_flow -> human_handoff (if booking fails or patient frustrated)
any -> human_handoff (explicit escalation)
human_handoff -> closed (admin closes)
closed -> new (patient sends new message to closed conversation)
```

### Database Migration: knowledge_base table
```sql
CREATE TABLE knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pregunta TEXT NOT NULL,
    respuesta TEXT NOT NULL,
    categoria TEXT NOT NULL DEFAULT 'general'
        CHECK (categoria IN ('horarios', 'ubicacion', 'precios', 'servicios', 'general')),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_knowledge_base_updated_at
    BEFORE UPDATE ON knowledge_base
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

### Streamlit Page Structure
```
admin-ui/src/pages/
  5_Inbox.py              # Conversation inbox (BOT-03)
  6_Knowledge_Base.py     # FAQ editor (D-04)
```

### Anti-Patterns to Avoid
- **Giant monolithic n8n workflow:** Split into main + sub-workflows per D-12
- **Storing state in n8n static data or Wait nodes:** Use PostgreSQL conversations table per D-10
- **Calling OpenAI from Streamlit:** All LLM calls go through n8n per D-02
- **Vector store for <50 FAQs:** System prompt injection is sufficient per D-05

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Intent classification | Custom regex/keyword matching | OpenAI gpt-4o-mini with structured prompt | LLM handles fuzzy natural language; regex breaks on spelling variations |
| Calendar availability | Custom free/busy logic | n8n Google Calendar node "Check Availability" operation | Handles timezone, recurring events, all-day events correctly |
| WhatsApp message formatting | Custom text builder | Evolution API sendText with simple string templates | Evolution API handles encoding, delivery, read receipts |
| Chat UI rendering | Custom HTML chat bubbles | Streamlit st.chat_message component | Native component with avatar, alignment, styling built in |
| Conversation polling | WebSocket implementation | st_autorefresh or st.rerun with time check | Polling every 10s is sufficient for single-admin clinic; WS is out of scope |

## Common Pitfalls

### Pitfall 1: Race Condition on Concurrent Messages
**What goes wrong:** Patient sends two messages quickly. Two n8n executions read the same conversation state simultaneously, both try to update, one overwrites the other.
**Why it happens:** n8n spawns a new execution per webhook event. No built-in mutex.
**How to avoid:** Use `SELECT ... FOR UPDATE` when reading conversation state. This acquires a row-level lock. The second execution waits until the first commits.
**Warning signs:** Duplicate bot responses, state jumping backward unexpectedly.

### Pitfall 2: Google Calendar OAuth2 Token Expiry
**What goes wrong:** OAuth2 access token expires after 1 hour. Booking requests fail silently.
**Why it happens:** n8n manages token refresh automatically IF the credential is configured correctly with a refresh token. But initial setup must include `access_type=offline` and `prompt=consent` in the OAuth flow.
**How to avoid:** During OAuth2 setup in n8n, ensure the Google Cloud Console app is configured for "offline" access. Test token refresh by waiting >1 hour and re-testing.
**Warning signs:** Booking works initially but fails after ~1 hour.

### Pitfall 3: Evolution API fromMe Messages in Webhook
**What goes wrong:** Bot's own outbound messages trigger the webhook (MESSAGES_UPSERT fires for ALL messages, including sent ones). Creates an infinite loop: bot sends reply -> webhook fires -> bot processes its own message -> sends another reply.
**Why it happens:** Evolution API's MESSAGES_UPSERT event includes both inbound and outbound messages by default.
**How to avoid:** Filter on `data.key.fromMe === false` at the very first node of the chatbot workflow. Only process messages NOT from the instance.
**Warning signs:** Bot responding to itself, exponentially growing message count.

### Pitfall 4: LLM Hallucinating Appointment Times
**What goes wrong:** The LLM "confirms" an appointment time that doesn't exist in Google Calendar or is already booked.
**Why it happens:** LLM generates text without checking actual calendar data.
**How to avoid:** NEVER let the LLM confirm a booking. The flow must be: LLM extracts preferred time -> n8n code checks GCal -> n8n presents actual available slots -> patient confirms -> n8n books. The LLM is used for natural language extraction, not for booking decisions.
**Warning signs:** Appointments that don't exist in Google Calendar, double-bookings.

### Pitfall 5: Knowledge Base Loading on Every Turn
**What goes wrong:** Loading all FAQs into the system prompt on every single message adds latency and token cost.
**Why it happens:** D-05 specifies loading active FAQs per turn.
**How to avoid:** This is acceptable for <50 FAQs (a few hundred tokens). If FAQ count grows significantly, cache the formatted FAQ text and refresh it on a timer (e.g., every 5 minutes) rather than per-turn DB query. For v1, per-turn query is fine.
**Warning signs:** Increasing token costs, response latency growing with FAQ count.

### Pitfall 6: Streamlit Inbox Not Showing New Messages
**What goes wrong:** Admin doesn't see new messages until manual page refresh.
**Why it happens:** Streamlit re-renders the entire page on rerun, losing scroll position and form state.
**How to avoid:** Use `st_autorefresh(interval=10000)` which triggers a rerun without losing the selected conversation in session_state. Store `selected_conversation_id` in st.session_state so it persists across reruns.
**Warning signs:** Admin repeatedly clicking refresh, complaints about "laggy" inbox.

## Code Examples

### Evolution API: Send Typing Indicator (from n8n HTTP Request node)
```
POST http://evolution-api:8080/chat/sendPresence/{{instance_name}}
Headers: { "apikey": "{{api_key}}", "Content-Type": "application/json" }
Body:
{
  "number": "{{remoteJid}}",
  "options": {
    "delay": 3000,
    "presence": "composing"
  }
}
```
Source: [Evolution API v2 Send Presence docs](https://doc.evolution-api.com/v2/api-reference/chat-controller/send-presence)
Confidence: HIGH

### Evolution API: MESSAGES_UPSERT Webhook Payload Structure
```json
{
  "event": "messages.upsert",
  "instance": "clinic-main",
  "data": {
    "key": {
      "remoteJid": "5215512345678@s.whatsapp.net",
      "fromMe": false,
      "id": "3EB0A0B1234567890"
    },
    "pushName": "Ana Lopez",
    "message": {
      "conversation": "Hola, quiero agendar una cita"
    },
    "messageType": "conversation",
    "messageTimestamp": 1712345678
  }
}
```
Source: [Evolution API webhooks docs](https://doc.evolution-api.com/v2/en/configuration/webhooks) + GitHub issues
Confidence: MEDIUM (field names verified against multiple sources, but exact v2 structure may vary slightly)

### LLM System Prompt Pattern for Intent Classification
```
You are a dermatology clinic assistant. Classify the patient's message into one of these intents:
- FAQ: patient asks about hours, location, prices, services, or general information
- BOOKING: patient wants to schedule/book/make an appointment
- HANDOFF: patient has a medical complaint, is frustrated, or asks something you cannot answer
- GREETING: patient says hello or a generic greeting

Respond with ONLY the intent label (FAQ, BOOKING, HANDOFF, or GREETING). No explanation.

Knowledge base context:
{{formatted_faqs}}

Patient message: {{message}}
```
Confidence: HIGH (standard prompt engineering pattern)

### LLM System Prompt Pattern for FAQ Answer
```
Eres la asistente virtual de la clinica dermatologica [NOMBRE]. Responde en espanol, de forma amable y concisa.

Usa SOLAMENTE la informacion del siguiente knowledge base para responder. Si la pregunta no esta cubierta, responde: "No tengo esa informacion. Te comunico con un miembro de nuestro equipo."

Knowledge base:
{{formatted_faqs_as_qa_pairs}}

Mensaje del paciente: {{message}}
```
Confidence: HIGH (standard pattern)

### Streamlit Inbox: Chat Message Rendering
```python
import streamlit as st

# Render conversation messages using st.chat_message
for msg in messages:
    role = "user" if msg["sender"] == "patient" else "assistant"
    with st.chat_message(role):
        st.write(msg["content"])
        st.caption(msg["created_at"].strftime("%H:%M"))

# Manual reply input
reply = st.chat_input("Escribe tu respuesta...")
if reply:
    # Send via Evolution API
    client.send_text_message(conversation["wa_contact_id"], reply)
    # Insert message record
    insert_message(conversation_id, "outbound", "agent", reply)
    st.rerun()
```
Source: [Streamlit chat elements docs](https://docs.streamlit.io/develop/api-reference/chat)
Confidence: HIGH

### PostgreSQL: Conversation State Read with Lock
```sql
-- n8n Postgres node query (parameterized)
SELECT c.id, c.state, c.context, c.patient_id, c.wa_contact_id,
       p.first_name, p.last_name, p.phone_normalized
FROM conversations c
LEFT JOIN patients p ON c.patient_id = p.id
WHERE c.wa_contact_id = $1 AND c.state != 'closed'
FOR UPDATE OF c
LIMIT 1;
```
Confidence: HIGH (standard PostgreSQL pattern)

### Database: New Knowledge Base Functions for database.py
```python
def fetch_knowledge_base(active_only: bool = True) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = "SELECT * FROM knowledge_base"
            if active_only:
                sql += " WHERE is_active = true"
            sql += " ORDER BY categoria, created_at"
            cur.execute(sql)
            return cur.fetchall()
    finally:
        conn.close()

def upsert_knowledge_base_item(item_id, pregunta, respuesta, categoria, is_active):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if item_id:
                cur.execute("""
                    UPDATE knowledge_base
                    SET pregunta=%s, respuesta=%s, categoria=%s, is_active=%s
                    WHERE id=%s RETURNING *
                """, (pregunta, respuesta, categoria, is_active, item_id))
            else:
                cur.execute("""
                    INSERT INTO knowledge_base (pregunta, respuesta, categoria, is_active)
                    VALUES (%s, %s, %s, %s) RETURNING *
                """, (pregunta, respuesta, categoria, is_active))
            result = cur.fetchone()
        conn.commit()
        return result
    finally:
        conn.close()
```
Confidence: HIGH (follows existing database.py patterns exactly)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| n8n AI Agent node (LangChain-based) | n8n OpenAI node with Responses API (v1.117+) | Late 2025 | Can use OpenAI Chat Completions directly without LangChain overhead. Simpler for intent classification. |
| Google Calendar Service Account | OAuth2 remains primary for self-hosted n8n | Ongoing | Service Account is documented but community reports issues on self-hosted. Use OAuth2 as safe default. |
| st_autorefresh third-party | Streamlit native fragment auto-rerun | Streamlit 1.37+ | `st.fragment` with `run_every` parameter may be available. st_autorefresh remains a safe fallback. |

## Open Questions

1. **Google Calendar: OAuth2 vs Service Account on self-hosted n8n**
   - What we know: n8n docs list Service Account as supported for Google Calendar. Community reports (April 2026) say self-hosted instances only show OAuth2 option.
   - What's unclear: Whether the deployed n8n version supports Service Account for GCal.
   - Recommendation: Default to OAuth2 setup. If Service Account works after testing, switch to it for zero-expiry tokens. OAuth2 with refresh token works fine -- n8n handles refresh automatically.

2. **Evolution API v2 sendPresence field naming**
   - What we know: v1 docs show `number` + `options.delay` + `options.presence`. v2 Postman collection shows `number` + `delay` + `presence` at body root level.
   - What's unclear: Exact v2 field structure (nested in options vs flat).
   - Recommendation: Test both structures against the deployed Evolution API version. Start with the v2 flat structure: `{ "number": "...", "delay": 3000, "presence": "composing" }`.

3. **n8n Postgres node FOR UPDATE support**
   - What we know: n8n Postgres node accepts raw SQL queries. FOR UPDATE is standard PostgreSQL.
   - What's unclear: Whether n8n's Postgres node keeps the transaction open long enough for the lock to be useful (if it auto-commits after the SELECT).
   - Recommendation: If FOR UPDATE does not work within a single n8n Postgres node execution, use a Function node with a custom pg client that runs SELECT FOR UPDATE + business logic + UPDATE in one transaction. Alternatively, use an optimistic locking pattern: read state + version, process, UPDATE WHERE version = expected_version, retry if 0 rows updated.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| n8n | Chatbot workflow | Yes (Docker) | 1.x | -- |
| OpenAI API | LLM calls | Yes (external) | gpt-4o-mini | -- (key must be configured) |
| Evolution API | WhatsApp messaging | Yes (Docker) | v2.x | -- |
| PostgreSQL | State + data | Yes (Docker) | 16.x | -- |
| Google Calendar API | Appointment booking | External service | v3 | -- (OAuth2 setup required) |
| Streamlit | Admin UI | Yes (Docker) | 1.35+ | -- |
| streamlit-autorefresh | Inbox polling | Not installed | -- | time.sleep + st.rerun pattern |

**Missing dependencies with no fallback:**
- Google Calendar OAuth2 credential must be configured in n8n before booking features work. Requires Google Cloud Console project + OAuth consent screen setup.

**Missing dependencies with fallback:**
- `streamlit-autorefresh`: If package is problematic, use `time.sleep(10); st.rerun()` pattern or Streamlit's `st.fragment(run_every=timedelta(seconds=10))` if available in deployed version.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.x+ with pytest-mock and requests-mock |
| Config file | None (default discovery in admin-ui/src/tests/) |
| Quick run command | `cd admin-ui/src && python -m pytest tests/ -x -q` |
| Full suite command | `cd admin-ui/src && python -m pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BOT-01 | FAQ response from knowledge base | n8n workflow (manual test) + unit test for KB queries | `cd admin-ui/src && python -m pytest tests/test_database.py -x -k knowledge` | No -- Wave 0 |
| BOT-02 | Human handoff escalation | n8n workflow (manual test) | Manual: send test message, verify state transition | N/A |
| BOT-03 | Inbox conversation view + manual reply | unit test for inbox DB queries + Evolution API send | `cd admin-ui/src && python -m pytest tests/test_inbox.py -x` | No -- Wave 0 |
| BOT-04 | Typing indicator | n8n workflow (manual test) | Manual: verify "composing" appears on phone | N/A |
| CAL-01 | Book appointment via Google Calendar | n8n workflow (manual test) + unit test for appointment DB insert | `cd admin-ui/src && python -m pytest tests/test_database.py -x -k appointment` | No -- Wave 0 |
| CAL-02 | WhatsApp confirmation message | n8n workflow (manual test) | Manual: verify message received with correct details | N/A |

### Sampling Rate
- **Per task commit:** `cd admin-ui/src && python -m pytest tests/ -x -q`
- **Per wave merge:** `cd admin-ui/src && python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `admin-ui/src/tests/test_inbox.py` -- covers inbox DB query functions and Evolution API send for manual reply
- [ ] Knowledge base DB functions in `test_database.py` or new `test_knowledge_base.py` -- covers fetch/upsert/toggle operations
- [ ] `streamlit-autorefresh` added to `requirements.txt` (if used)
- [ ] SQL migration file `postgres/init/003_knowledge_base.sql` or appended to 002_seed.sql

## Sources

### Primary (HIGH confidence)
- [Evolution API v2 Send Presence](https://doc.evolution-api.com/v2/api-reference/chat-controller/send-presence) - typing indicator endpoint, request format
- [Evolution API v2 Webhooks](https://doc.evolution-api.com/v2/en/configuration/webhooks) - MESSAGES_UPSERT payload structure
- [Streamlit Chat Elements](https://docs.streamlit.io/develop/api-reference/chat) - st.chat_message, st.chat_input API
- [n8n Google Calendar Event Operations](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.googlecalendar/event-operations/) - create, get, check availability
- [n8n Google Calendar Credentials](https://docs.n8n.io/integrations/builtin/credentials/google/) - OAuth2 and Service Account setup
- [n8n OpenAI Chat Model node](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.lmchatopenai/) - LLM integration

### Secondary (MEDIUM confidence)
- [Evolution API v2 Postman Collection](https://www.postman.com/agenciadgcode/evolution-api/documentation/jn0bbzv/evolution-api-v2-2-2) - sendPresence field structure variations
- [n8n community: Service Accounts in Google Calendar](https://community.n8n.io/t/service-accounts-in-google-calendar-nodes/283731) - self-hosted limitation report
- [n8n booking system template](https://n8n.io/workflows/8635-complete-booking-system-with-google-calendar-business-hours-and-rest-api/) - reference workflow pattern

### Tertiary (LOW confidence)
- Evolution API v2 MESSAGES_UPSERT exact field nesting (verified against GitHub issues, not live-tested)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all components already in project, well-documented
- Architecture: MEDIUM-HIGH - sub-workflow pattern is established in ARCHITECTURE.md; chatbot state machine is standard
- Pitfalls: HIGH - race conditions, fromMe filtering, OAuth token refresh are well-known issues
- Google Calendar auth: MEDIUM - OAuth2 is safe fallback; service account status uncertain on self-hosted

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (30 days -- stable stack, no fast-moving components)
