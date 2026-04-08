# Phase 4: AI Chatbot + Appointment Booking - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Patients receive automatic FAQ answers on WhatsApp via a conversational chatbot. When the patient asks to book an appointment, the chatbot collects service type and preferred date/time, checks Google Calendar availability, and books the appointment without human intervention — sending a WhatsApp confirmation. The chatbot escalates to a human when it cannot answer or detects a medical complaint. The admin can monitor all conversations and reply manually from a Streamlit inbox.

Campaign sending, reminders (24h/1h), and social publishing are NOT in scope — those are Phases 5, 6, and 7.

</domain>

<decisions>
## Implementation Decisions

### LLM Backend
- **D-01:** OpenAI API, model `gpt-4o-mini`. Ollama is not feasible on the current server setup. The n8n native OpenAI node handles the integration — no HTTP Request node workaround needed.
- **D-02:** API key stored as n8n credential (`OPENAI_API_KEY`). All LLM calls go through n8n's AI Agent node or OpenAI Chat node, NOT direct HTTP from Streamlit.

### Knowledge Base (FAQ)
- **D-03:** FAQs are stored in a new PostgreSQL table `knowledge_base` with columns: `id`, `pregunta`, `respuesta`, `categoria`, `is_active`, `created_at`, `updated_at`. Categories: horarios, ubicacion, precios, servicios, general.
- **D-04:** The clinic owner edits FAQs from Streamlit — a new page `6_Knowledge_Base.py` with a simple table editor (add, edit, toggle active/inactive per row). No n8n workflow needed for FAQ management.
- **D-05:** n8n chatbot workflow loads active FAQs from PostgreSQL at the start of each conversation turn (SELECT * FROM knowledge_base WHERE is_active = true) and includes them in the LLM system prompt as context. No vector store — system prompt injection is sufficient for <50 FAQ items.

### Booking Conversation Flow
- **D-06:** Natural conversation — the LLM extracts the patient's preferred date/time and service type from free text. The bot does NOT use numbered menus or WhatsApp list messages.
- **D-07:** The bot collects: (1) tipo de servicio, (2) fecha y hora preferida. If the patient's phone number is already in the `patients` table, their name is auto-filled; if not, the bot also asks for their name.
- **D-08:** After extracting preferences, the bot queries Google Calendar for available slots in the preferred window, presents 2-3 options, and books the one the patient selects. If no slots match, it offers the next available day.
- **D-09:** On successful booking: creates Google Calendar event, inserts row into `appointments` table (with `google_event_id`), and sends a WhatsApp confirmation message with date, time, and clinic details (CAL-02).

### Chatbot State Machine
- **D-10:** Follows ARCHITECTURE.md Pattern 2 — PostgreSQL `conversations` table is the state machine. Existing states from schema are used as-is: `new` → `awaiting_intent` → `faq_flow` / `booking_flow` → `human_handoff` → `closed`. No schema changes needed.
- **D-11:** `context JSONB` column stores in-progress booking data (e.g., service type collected, awaiting time preference). Each n8n execution reads state + context, transitions, writes back.

### n8n Workflow Structure
- **D-12:** The existing `whatsapp-message-stub.json` webhook is replaced by a real `whatsapp-chatbot.json` workflow. Sub-workflow pattern (ARCHITECTURE.md Pattern 3): one main inbound workflow + separate sub-workflows for `classify-intent`, `faq-answer`, `booking-flow`, and `send-wa-message`.
- **D-13:** Typing indicator (BOT-04): n8n sends a "composing" presence update to Evolution API before the LLM call, then sends the actual response after. Implemented as two Evolution API HTTP calls in the chatbot workflow.

### Admin Inbox UX
- **D-14:** New Streamlit page `5_Inbox.py` — split-pane layout with `st.columns([1, 2])`. Left column: conversation list with status badges (BOT / HUMANO / CERRADA) and last message preview. Right column: full chat history (scrollable) + manual reply text area + "Enviar" button.
- **D-15:** Conversations flagged for human response (`state = 'human_handoff'`) are shown at the top of the list with a `[!]` indicator.
- **D-16:** Admin closes a conversation with a "Cerrar conversación" button in the chat view — sets `state = 'closed'` in DB.
- **D-17:** Inbox auto-refreshes every 10 seconds using `st_autorefresh` (or `time.sleep` + `st.rerun()` pattern) — consistent with Phase 2 polling pattern.

### Claude's Discretion
- Exact system prompt wording for the LLM (FAQ injection format, persona instructions)
- Evolution API endpoint for sending typing indicator presence
- How to handle concurrent messages from the same patient (optimistic locking on state update)
- Streamlit chat message rendering (use `st.chat_message` if available, otherwise custom HTML)
- Google Calendar working hours configuration (check CLINIC_CALENDAR_ID env var)

### Folded Todos
No todos folded — none matched Phase 4 scope.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Database Schema
- `postgres/init/001_schema.sql` — `conversations` table (state machine, JSONB context), `messages` table (inbound/outbound/bot/agent), `appointments` table (google_event_id, reminder flags). New `knowledge_base` table must be added via migration.

### Requirements
- `.planning/REQUIREMENTS.md` §BOT — BOT-01 (FAQ via knowledge base), BOT-02 (human handoff), BOT-03 (inbox + manual reply), BOT-04 (typing indicator)
- `.planning/REQUIREMENTS.md` §CAL — CAL-01 (book appointment without intervention), CAL-02 (WhatsApp confirmation with date/time/details)
- `.planning/ROADMAP.md` §Phase 4 — 4 success criteria define what "done" means for this phase

### Architecture Patterns
- `.planning/research/ARCHITECTURE.md` §Pattern 2 — State machine via PostgreSQL (chatbot state transitions)
- `.planning/research/ARCHITECTURE.md` §Pattern 3 — Sub-workflow pattern for chatbot (classify-intent, faq-answer, booking-flow sub-workflows)
- `.planning/research/ARCHITECTURE.md` §Chatbot inbound flow — Sample n8n node sequence for the chatbot

### Existing Workflows (extend/replace)
- `n8n/workflows/whatsapp-message-stub.json` — Stub webhook that receives MESSAGES_UPSERT; this is replaced by the real chatbot workflow in this phase

### Existing Admin UI (extend)
- `admin-ui/src/app.py` — `st.navigation()` entrypoint; add `5_Inbox.py` and `6_Knowledge_Base.py` pages here
- `admin-ui/src/components/sidebar.py` — `render_sidebar()` must be called at the top of every new page
- `admin-ui/src/components/database.py` — DB connection pattern; follow for new queries in Inbox and KB pages

### Prior Phase Context
- `.planning/phases/02-whatsapp-core/02-CONTEXT.md` — WhatsApp session pattern, Evolution API integration, n8n workflow structure decisions
- `.planning/phases/03-crm-core/03-CONTEXT.md` — Established Streamlit page/component patterns, PostgreSQL query patterns

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `admin-ui/src/components/sidebar.py`: `render_sidebar()` — import at top of every new page
- `admin-ui/src/components/database.py`: DB connection via `DATABASE_URL` env var — reuse for inbox queries and knowledge base CRUD
- `postgres/init/001_schema.sql`: `conversations`, `messages`, `appointments` tables fully defined — no changes needed except adding `knowledge_base` table
- `n8n/workflows/whatsapp-message-stub.json`: stub webhook at path `whatsapp-inbound/messages-upsert` — this becomes the chatbot webhook entry point

### Established Patterns
- Streamlit pages: `admin-ui/src/pages/N_PageName.py` naming convention (next: `5_Inbox.py`, `6_Knowledge_Base.py`)
- No ORM — direct psycopg2 queries following `database.py` pattern
- n8n webhook base: `/webhook/whatsapp-inbound/` — chatbot webhook extends this path
- Evolution API calls from n8n: HTTP Request node to `http://evolution-api:8080/` on Docker internal network
- OpenAI calls from n8n: native OpenAI node with `OPENAI_API_KEY` credential (already in stack env)

### Integration Points
- Evolution API → n8n: MESSAGES_UPSERT webhook → chatbot workflow (replaces stub)
- n8n → PostgreSQL: read/write `conversations`, `messages`, `appointments`, `knowledge_base`
- n8n → OpenAI API: LLM intent classification + FAQ answer generation
- n8n → Google Calendar API: check availability + create event (Service Account, CAL-01)
- n8n → Evolution API: send WhatsApp reply + typing indicator
- Streamlit → PostgreSQL: inbox reads `conversations` + `messages`; KB page reads/writes `knowledge_base`
- Streamlit → Evolution API: send manual reply from inbox (HTTP POST to Evolution API send-message endpoint)

</code_context>

<specifics>
## Specific Ideas

- Inbox left column shows [!] indicator for `human_handoff` conversations — these float to the top
- Booking confirmation message (Spanish): "Cita confirmada para el {fecha} a las {hora}. Te esperamos en {dirección_clínica}. ¡Hasta pronto!"
- Human handoff message to patient (Spanish): "Tu consulta fue recibida. Un miembro de nuestro equipo te atenderá en breve."
- Knowledge base categories: horarios, ubicacion, precios, servicios, general
- The `context JSONB` field in `conversations` stores booking state: e.g., `{"booking_step": "awaiting_time", "service_type": "Consulta general"}`

</specifics>

<deferred>
## Deferred Ideas

- Appointment reminders (24h and 1h before) — CAL-03, explicitly Phase 7
- Automatic conversation close after X hours of inactivity — mentioned during Inbox discussion, defer to v2
- WhatsApp list messages / button menus for booking — user chose natural conversation; menu approach deferred
- MiniMax API integration — user mentioned MiniMax initially but pivoted to OpenAI; revisit if OpenAI costs become significant
- Multi-language support for chatbot — not required for MVP (single-clinic, Spanish only)

</deferred>

---

*Phase: 04-ai-chatbot-appointment-booking*
*Context gathered: 2026-04-08*
