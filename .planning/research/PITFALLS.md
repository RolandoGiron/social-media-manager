# Pitfalls Research

**Domain:** AI-powered WhatsApp chatbot + social media management + CRM for clinics (n8n on VPS)
**Researched:** 2026-03-27
**Confidence:** MEDIUM — WebSearch and WebFetch tools unavailable during this session; findings drawn from training knowledge of Evolution API, n8n, WhatsApp Web reverse-engineering ecosystem, and LLM deployment patterns through August 2025. Critical claims flagged with confidence level.

---

## Critical Pitfalls

### Pitfall 1: WhatsApp Number Banned by Sending Mass Messages Too Fast

**What goes wrong:**
The WhatsApp number connected via Evolution API gets permanently banned after a bulk campaign. The clinic loses its main communication channel with patients — potentially its primary contact number — with no appeal path.

**Why it happens:**
Evolution API uses the WhatsApp Web protocol (Baileys library), which mimics the browser client. WhatsApp's spam detection monitors for non-human patterns: identical message bodies to hundreds of recipients in rapid succession, high complaint rates from recipients who mark messages as spam, and abnormal send velocity. Developers test bulk sends without throttling, then replicate the same pattern in production. A single campaign to 200+ patients at 1-message-per-second gets detected immediately.

**How to avoid:**
- Enforce a minimum delay of 3–8 seconds between individual messages in any bulk send, with jitter (randomized delay, not fixed interval)
- Cap daily outbound messages per number to 200–300 until the number has 90+ days of history on the platform
- Personalize every message: include the patient's first name and vary sentence structure across segments; identical bodies are a strong spam signal
- Use message templates that look like genuine reminders, not promotional blasts
- Never send to unverified/old numbers — invalid numbers and high delivery failure rates correlate with spam scoring
- Implement a recipient opt-out mechanism and honor it immediately
- Do NOT use a freshly created WhatsApp number for bulk sends; use an established number with normal usage history of at least 60 days

**Warning signs:**
- WhatsApp Web session disconnects immediately after a bulk send starts
- Recipients report "this message looks like spam" notifications
- Evolution API logs show repeated QR code regeneration cycles (session being killed by server)
- Sudden drop in message delivery receipts (double checkmark never appears)

**Phase to address:** WhatsApp core phase (Phase 1 or 2 — wherever bulk messaging is first implemented). Rate limiting architecture must be built before the first production bulk send, not added later.

---

### Pitfall 2: n8n Workflow Execution Queue Overwhelm on Limited VPS RAM

**What goes wrong:**
n8n's execution queue fills up during peak hours (a bulk campaign triggers hundreds of webhook callbacks simultaneously), the Node.js process exhausts available RAM, and n8n either crashes or begins failing executions silently. The VPS has no alerting, so the failure goes undetected for hours. Appointments booked during the outage are lost.

**Why it happens:**
n8n stores execution data in memory during processing. A single bulk WhatsApp send to 500 contacts triggers 500 potential incoming webhook responses (delivery receipts, replies) within minutes. If n8n is configured with default concurrency settings and the VPS has 2–4 GB RAM shared with PostgreSQL, Evolution API, and Ollama, the heap fills rapidly. Developers typically size the VPS for normal chatbot load, forgetting campaign spikes multiply it 100x.

**How to avoid:**
- Set `EXECUTIONS_PROCESS=main` and configure `N8N_DEFAULT_CONCURRENCY` to a low value (4–8) to queue instead of parallelize
- Use n8n's built-in queue mode with a Redis-backed queue when execution volume scales — prevents RAM exhaustion even at high throughput
- Separate webhook receiver workflows (fast, minimal logic) from processing workflows (slow, complex logic) using n8n's "Execute Workflow" node as a queue boundary
- Reserve at minimum 1 GB RAM exclusively for n8n; run PostgreSQL and Ollama on separate resource allocations with `systemd` memory limits
- Add a dead letter queue: store incoming webhook payloads to PostgreSQL first, then process from DB — this decouples arrival rate from processing rate
- Monitor n8n execution failure rate via its internal metrics endpoint or export to a simple cron-based health check

**Warning signs:**
- n8n process memory usage above 80% of allocated RAM for more than 5 minutes
- Execution queue depth growing instead of draining
- `ETIMEDOUT` or `ECONNREFUSED` errors in n8n logs for internal webhook calls
- Scheduled workflows skipping execution windows

**Phase to address:** Infrastructure/architecture phase (first phase). Concurrency limits and queue architecture must be defined before workflows are built, not retrofitted.

---

### Pitfall 3: LLM Hallucinations Giving Wrong Medical or Scheduling Information

**What goes wrong:**
The AI chatbot confidently tells a patient that a specific treatment costs X, that Dr. Y is available on Thursday, or that a procedure is appropriate for their condition — all of which are wrong. The patient shows up for a non-existent appointment, pays the wrong amount, or worse, makes a health decision based on fabricated medical information. This creates legal liability and destroys patient trust.

**Why it happens:**
LLMs generate plausible-sounding answers even when they have no knowledge of the specific clinic's pricing, doctor schedules, or clinical protocols. Developers build the chatbot with a system prompt that says "you are an assistant for Dermatología X" without constraining the model to only answer from a verified knowledge base. The model fills gaps in its context with hallucinated specifics. This is especially dangerous in medical contexts where patients make health decisions based on the answers.

**How to avoid:**
- Implement strict Retrieval-Augmented Generation (RAG): the LLM must only answer pricing, treatment, and scheduling questions by retrieving from the clinic's verified knowledge base (stored in PostgreSQL or a vector store)
- For scheduling specifically: NEVER let the LLM decide if a slot is available. The bot must query Google Calendar via n8n, get the actual free slots, and present them to the user. The LLM's role is conversation flow management, not data retrieval
- Add a constraint in the system prompt: "If the answer is not in the provided context, respond: 'I don't have that information right now. Let me connect you with our team.' Do NOT guess."
- Flag and escalate to human: any question about contraindications, drug interactions, medical history, or post-procedure complications must immediately escalate to a human staff member, never be answered by the AI
- Log all chatbot responses with a review queue for the first 30 days — manually audit 10% of responses per week

**Warning signs:**
- Bot answers specific pricing or availability questions without making an API call first (visible in n8n execution logs)
- Staff reporting patients arriving with incorrect expectations
- Bot responses that include specific doctor names or dates not present in the retrieved context

**Phase to address:** Chatbot AI phase. RAG architecture and escalation rules must be the foundation of the bot, not added after testing reveals hallucinations.

---

### Pitfall 4: Evolution API Session Instability Under Long-Running Deployments

**What goes wrong:**
Evolution API's WhatsApp session disconnects randomly every few days (or hours), requiring manual QR code re-scanning. Since the clinic uses the same number for real patient communication, when the session drops at 2 AM, the chatbot goes dark until someone manually reconnects it. The 24/7 availability requirement fails silently.

**Why it happens:**
Evolution API uses the WhatsApp Web Baileys library, which maintains a WebSocket connection to WhatsApp's servers. WhatsApp periodically terminates sessions that look like automated tools, especially when the session has no "human" interaction patterns (only sends automated messages without any manual interaction). The multi-device protocol is more stable than the old Web protocol but still requires session health management. Most deployments don't implement auto-reconnection with exponential backoff or session health monitoring.

**How to avoid:**
- Configure Evolution API's webhook for connection state changes (`CONNECTION_UPDATE` events) and trigger an n8n workflow that attempts automatic reconnection
- Run Evolution API with Docker Compose with `restart: always` — process crashes are recovered automatically
- Implement a cron-based health check every 5 minutes: ping the Evolution API `/instance/fetchInstances` endpoint and alert if the instance state is not `open`
- Store the session credentials (the `auth` folder) on a persistent Docker volume — losing this on restart requires full QR re-scan
- Keep one "human" interaction pattern: the clinic owner occasionally sends a message manually from the connected phone, which maintains a more authentic session profile
- Use Evolution API v2 (multi-device) rather than v1 — multi-device sessions survive phone going offline

**Warning signs:**
- Evolution API logs showing `close` state events
- Chatbot stops responding to messages without any n8n error
- Docker container for Evolution API restarting frequently
- Session state file being regenerated (timestamp changes on auth folder)

**Phase to address:** Infrastructure phase and WhatsApp core phase. Session monitoring must be operational before any production traffic.

---

### Pitfall 5: Social Media API Approval Blocking Launch Timeline

**What goes wrong:**
The developer builds the social media auto-publishing feature assuming Meta (Instagram/Facebook) API access is straightforward to obtain. In reality, Meta requires app review for publishing permissions, Instagram requires a Business or Creator account linked to a Facebook Page, and the review process takes 2–6 weeks with a non-trivial rejection rate for new apps. TikTok's API for content publishing is even more restricted. Launch is blocked by an external gating process the developer has no control over.

**Why it happens:**
Developers start the API integration phase late in the project, treating API approval as a technical task rather than a business process with external dependencies. They also underestimate the documentation required: Meta requires privacy policy URL, detailed use case description, screen recordings of the OAuth flow, and sometimes a video demo. A single rejected review restarts the wait period.

**How to avoid:**
- Start Meta app review process during the very first week of the project, before writing a single line of code for social publishing
- Use an intermediary publishing service (Buffer, Make, Zapier, or a similar tool with existing Meta approval) as a fallback for the MVP — these already have approved API access and n8n has native integrations with several
- For Instagram specifically: ensure the connected account is a Professional Account (Business or Creator), linked to a Facebook Page, with a valid Facebook App configured in Meta Developer Console
- For TikTok: accept early that the Content Posting API requires a business verification process and plan for it as a post-MVP feature if approval is delayed
- Build the social publishing module as a pluggable adapter so the underlying API can be swapped without rewriting workflow logic

**Warning signs:**
- Meta App Review status stuck in "In Review" for more than 2 weeks without feedback
- Error `(#200) The user hasn't authorized the application to perform this action` when testing publishing endpoints
- Instagram API returning `Error type: OAuthException` for publishing calls

**Phase to address:** Social media phase — but the Meta app registration and review submission must happen in Phase 1 (project setup) regardless of when the social feature is built.

---

### Pitfall 6: Google Calendar Integration Breaking on Token Expiration

**What goes wrong:**
The Google Calendar integration works perfectly during development (using a freshly authorized OAuth token), then breaks in production 7 days later when the refresh token expires or the OAuth consent screen is in "Testing" mode. Appointment booking via chatbot silently fails — patients are told they were booked but no calendar event is created.

**Why it happens:**
Google OAuth refresh tokens for apps in "Testing" mode expire after 7 days. When developers move to production, they often forget to publish the OAuth consent screen, which keeps the app in testing mode perpetually. Additionally, if n8n's credential store loses the refresh token (database reset, credential migration), there's no mechanism to detect the failure other than noticing appointments aren't appearing.

**How to avoid:**
- Publish the Google Cloud Project OAuth consent screen to "Production" status before going live — this requires verification for sensitive scopes but Calendar read/write is not a sensitive scope if used for the app owner's own calendar
- Use a Google Service Account instead of OAuth user credentials for server-to-server access — service accounts don't expire and don't require user consent flows; grant the service account access to the clinic's calendar directly
- Implement a daily health check n8n workflow that creates a test event 6 months in the future, verifies it was created, then deletes it — alerts if this fails
- Store Calendar integration failures in PostgreSQL with a retry queue rather than silently dropping appointment requests

**Warning signs:**
- n8n Google Calendar nodes returning `401 Unauthorized` or `invalid_grant` errors
- Appointments reported by chatbot as "booked" but not appearing on the calendar
- n8n credential panel showing "Connection failed" for Google credentials

**Phase to address:** Calendar integration phase. Use Service Account credentials from day one — it eliminates the token expiration class of problems entirely.

---

### Pitfall 7: Ollama/Local LLM Latency Making Chatbot Feel Broken

**What goes wrong:**
The chatbot takes 8–25 seconds to respond when running Llama 3 or similar models on the VPS CPU (no GPU). Patients send a message and, perceiving no response, send 3–4 follow-up messages before the first response arrives. The bot then responds 4 times in rapid succession, creating a confusing and broken experience. Some patients interpret the silence as the bot being offline and abandon the conversation.

**Why it happens:**
Ollama inference on CPU for a 7B parameter model takes 8–20 seconds per response on a typical 4-core VPS. Developers test locally on a machine with a GPU or Apple Silicon, see 1–2 second responses, and assume the same performance in production. The Baileys/Evolution API webhook architecture also means that while the LLM is generating, new messages from the same user continue arriving and each one triggers a new LLM call.

**How to avoid:**
- Implement a "typing indicator" state: when a message arrives and triggers LLM processing, immediately send a WhatsApp "typing..." status via Evolution API to signal the bot is working
- Implement per-conversation locks: when user X's message is being processed, queue subsequent messages from X rather than spawning parallel LLM calls
- Benchmark Ollama on the actual VPS hardware before committing to local inference. If response time exceeds 6 seconds for the model chosen, switch to a cloud API (GPT-4o-mini or Claude Haiku at ~$0.001 per chatbot interaction is negligible cost for a single clinic)
- Use a smaller, faster model for FAQ responses (Phi-3 Mini or Llama 3.2 3B) and reserve larger models only for complex queries
- Add a 30-second timeout with fallback: "Estamos procesando tu mensaje, te respondemos en un momento" — then a human agent can follow up

**Warning signs:**
- Ollama API response time consistently above 5 seconds in local testing
- Patient conversations showing duplicate or out-of-order bot responses
- n8n execution logs showing multiple simultaneous executions triggered by the same conversation thread
- VPS CPU at 90–100% during any chatbot interaction

**Phase to address:** AI/chatbot phase. Benchmark inference speed before architecture is locked in; the local vs. cloud decision must be made with actual latency data, not assumptions.

---

### Pitfall 8: n8n Workflow Spaghetti — Unmaintainable Automation Logic

**What goes wrong:**
After 3–4 months of incremental workflow building, the n8n canvas becomes a tangle of interconnected workflows with unclear dependencies, duplicate logic, hardcoded values, and no documentation. Adding a new feature (like a new message template) requires understanding 8 different workflows. A change in one workflow silently breaks another. The solo developer becomes afraid to touch the automation layer.

**Why it happens:**
n8n's visual interface makes it easy to "just add a node" rather than design proper abstractions. Without a naming convention, folder structure, and sub-workflow discipline, workflows accumulate organically. Error handling is skipped in early workflows because "we'll add it later." Credentials and API keys get hardcoded as Set node values instead of using n8n's credential manager.

**How to avoid:**
- Establish naming conventions before writing the first workflow: `[domain].[entity].[action]` e.g. `whatsapp.message.send-bulk`, `calendar.appointment.create`
- Create sub-workflows for any logic used in more than one place (API call wrappers, message formatting, error logging)
- Never hardcode API endpoints, phone numbers, or configuration values in workflow nodes — use n8n environment variables or a config lookup from PostgreSQL
- Every workflow must have an error handler node that logs failures to a PostgreSQL `workflow_errors` table with workflow name, timestamp, input data, and error message
- Keep a workflow inventory document (can be a simple markdown file) with one line per workflow: name, purpose, triggers, dependencies

**Warning signs:**
- Difficulty explaining what a workflow does without tracing it node by node
- Same HTTP Request URL appearing hardcoded in 3+ different workflows
- Workflow failures that nobody notices for more than a few hours
- Fear of modifying existing workflows — "if I change this, I don't know what breaks"

**Phase to address:** All phases from the start. Naming conventions and sub-workflow patterns must be established in Phase 1 and enforced throughout.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoding phone numbers and API URLs in n8n nodes | Faster initial workflow setup | Every value must be hunted and updated across 20+ workflows when anything changes | Never — use n8n env vars or config table from day one |
| No per-conversation message queue/lock | Simpler n8n trigger design | Parallel LLM calls for same user, duplicate responses, confused conversation state | Never for production |
| OAuth user tokens for Google Calendar | Quick setup, familiar flow | Tokens expire; require manual re-auth every 6 months or 7 days in test mode | Never — use Service Account |
| Single n8n workflow for entire chatbot flow | Easy to build initially | Impossible to debug, test, or extend; one node failure kills entire conversation | Never — modularize from start |
| Skip message delay on bulk WhatsApp sends | Sends campaigns 10x faster | High ban probability after first large campaign | Never in production |
| Use default Ollama model size without benchmarking | Works in dev with GPU | 20-second responses on CPU VPS, broken UX | Never — benchmark before committing |
| Store conversation state in n8n workflow variables | No DB schema needed | State lost on n8n restart, impossible to inspect or debug | Only for stateless FAQ bot; never for appointment booking |
| Build social publishing before Meta API approval is obtained | Can develop UI and logic | Feature can't ship until external review completes; creates false velocity | Submit for review immediately, develop in parallel |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Evolution API webhooks | Registering the webhook URL using `localhost` or a private IP | Use the VPS public IP or domain; Evolution API webhooks call back to n8n externally |
| Evolution API bulk send | Sending to a list without checking connection state first | Always call `GET /instance/fetchInstances` before starting a bulk job and abort if state is not `open` |
| Google Calendar API | Using `primary` calendar identifier without verifying which calendar patients should book to | Create a dedicated calendar for bot-booked appointments, use its Calendar ID explicitly |
| Google Calendar OAuth | App in "Testing" mode — 7-day refresh token expiry | Publish consent screen to Production or use Service Account |
| Meta Graph API (Instagram/Facebook) | Requesting too many permissions in initial app review | Request only the minimum scopes needed: `pages_manage_posts`, `instagram_content_publish`; each additional scope increases review friction |
| n8n HTTP Request node | Not setting a timeout on LLM API calls | LLM calls can hang indefinitely; always set a 30-second timeout with error handling |
| Ollama in Docker | Accessing Ollama container from n8n container using `localhost` | Use Docker service name (e.g., `http://ollama:11434`) when both run in Docker Compose |
| PostgreSQL from n8n | Not using connection pooling, opening a new connection per execution | Configure n8n's PostgreSQL credential with a pool size of 10–20; VPS Postgres has a default max_connections of 100 which fills quickly |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Unthrottled bulk WhatsApp sends | All 500 messages sent in 30 seconds; n8n shows success but account gets banned | Enforce 3–8s delay with jitter between each message; process in batches of 50 | First campaign above ~50 recipients without throttling |
| Ollama blocking n8n event loop | All n8n workflows slow during LLM inference on same host | Run Ollama as separate Docker service with its own CPU allocation; or use cloud API | Any load above 5 concurrent chatbot conversations |
| n8n loading large CSV files in memory | Importing 5,000-patient CSV causes n8n to OOM crash | Use streaming/chunked processing; insert to PostgreSQL in batches of 100 via a loop workflow | CSV files above ~10,000 rows on 2 GB RAM VPS |
| Chatbot without conversation state pagination | Passing entire conversation history to LLM on every message | Cap context window: last 10 messages + system prompt; truncate older messages | Conversations longer than ~20 messages exceed token limits and cost spikes |
| No index on patient search columns | Patient lookup by phone number takes 500ms+ as DB grows | Add PostgreSQL indexes on `phone_number`, `last_interaction_at`, `segment_id` from migration zero | Database above ~10,000 patient records |
| n8n executing webhook workflows synchronously for all campaign responses | 500 delivery receipts arrive simultaneously, queue blocks | Separate webhook receipt from processing; write receipts to DB immediately, process async | Campaigns above 100 recipients |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing patient phone numbers and health segment data (e.g., "has acne treatment") unencrypted | GDPR/privacy violation even if local regulation doesn't require it; patient data breach | Encrypt sensitive columns (AES-256 at column level or full-disk encryption); separate health segment labels from identifiable contact data |
| Exposing n8n webhook URLs without authentication | Anyone who discovers the URL can trigger workflows — including bulk WhatsApp sends | Add webhook authentication: either a secret query parameter or HMAC signature verification on all inbound webhooks |
| LLM logging patient conversation content to cloud service | Patient messages sent to OpenAI/Anthropic API are logged by default | If using cloud LLM, set `user` parameter and review provider's data retention policy; request zero-data-retention if available; prefer Ollama for medical conversations |
| n8n running as root user in Docker | Container escape gives full VPS access | Run n8n container as non-root user; use Docker's `--user` flag |
| Evolution API admin endpoint exposed to internet without auth | Anyone can connect/disconnect instances, read all messages | Run Evolution API admin panel behind VPN or IP whitelist; never expose port 8080 publicly |
| API keys stored in n8n workflow Set nodes | Keys visible to anyone with workflow view access; exported in workflow JSON backups | Use n8n's credential manager exclusively; audit existing workflows for hardcoded secrets |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Bot responds to every message including accidental taps and voice messages | Patients receive nonsensical bot responses; they feel confused and distrust the bot | Filter: respond only to text messages; for audio/image, send "Por favor escríbeme tu mensaje para poder ayudarte" |
| No handoff message when escalating to human | Patient waits for bot response after escalation but doesn't know a human will take over | Send explicit message: "Te estoy conectando con uno de nuestros asesores. Te responderán en los próximos [X] minutos." Then visually flag the conversation in admin panel |
| Bot sends promotional campaign to patients who just replied with "STOP" | Patient anger, likely spam report | Implement immediate opt-out: any message containing "STOP", "NO", "Dar de baja" removes patient from all campaign lists within seconds |
| Admin interface requires navigating n8n directly | Clinic owner cannot use it; requires developer for every operation | Build a minimal Streamlit or simple web UI for the 3 core operations: upload patients, launch campaign, view conversation history |
| No confirmation before bulk WhatsApp campaign | Accidental trigger sends test message to 500 patients | Require explicit confirmation step: "You are about to send to 487 patients. Confirm?" with preview of message content |
| Calendar booking confirmation not sent immediately | Patient unsure if appointment was booked | Send a WhatsApp confirmation message with date, time, doctor name, and a Google Calendar invite link immediately after successful booking |

---

## "Looks Done But Isn't" Checklist

- [ ] **WhatsApp bulk send:** Rate limiting is implemented and tested — verify by checking n8n execution timing logs show 3–8s gaps between sends, not milliseconds
- [ ] **Chatbot FAQ:** Bot actually pulls answers from the clinic's knowledge base via RAG, not from LLM general knowledge — verify by asking about the clinic's specific pricing and checking n8n logs show a DB lookup before the LLM call
- [ ] **Google Calendar booking:** Appointment appears on the actual Google Calendar, not just in the chatbot's PostgreSQL state — verify by checking the calendar directly after a test booking
- [ ] **Session monitoring:** Evolution API disconnect triggers an alert or auto-reconnect — verify by manually calling `POST /instance/logout` and confirming the health check detects it within 5 minutes
- [ ] **Human escalation:** When bot escalates, the conversation actually appears in the admin interface and the human agent can respond through a supported channel — test the full handoff flow end-to-end
- [ ] **Opt-out:** Sending "STOP" to the bot actually removes the patient from campaign lists — verify by checking the patient record in PostgreSQL immediately after
- [ ] **Error handling:** n8n workflow failures are logged to `workflow_errors` table — verify by intentionally breaking an API call and confirming the error row appears with full context
- [ ] **Token expiry:** Google Calendar credentials still work 8 days after initial setup — verify with Service Account (never expires) or by checking OAuth consent screen is in Production mode
- [ ] **Social publishing:** Meta API permissions are approved (not just requested) — verify by making an actual test post via the API, not just checking the permission list in Developer Console
- [ ] **Patient data import:** CSV import handles duplicate phone numbers and malformed rows gracefully — test with a CSV that has duplicates and missing fields

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| WhatsApp number banned | HIGH | 1. Register a new number (separate SIM) for the chatbot while the banned number recovers. 2. Submit Meta ban appeal (low success rate for unofficial API bans). 3. Migrate patients to new number via alternative channel (SMS or email). 4. Run a 30-day "warming period" on new number before any bulk campaigns. |
| n8n data loss from VPS crash | HIGH if no backups | 1. Restore PostgreSQL from daily backup. 2. Re-import n8n workflow JSON files from version-controlled backups. 3. Re-enter credentials manually (not stored in workflow JSON). Mitigation: automated daily pg_dump + workflow JSON export to Git or S3. |
| LLM hallucination patient incident | HIGH (reputation/legal) | 1. Immediately disable AI responses and switch to human-only mode. 2. Contact affected patients to correct misinformation. 3. Audit last 30 days of AI responses. 4. Reimplement with strict RAG before re-enabling. |
| Google Calendar auth broken | MEDIUM | 1. If OAuth: re-authorize credentials in n8n. 2. If Service Account: check if key was accidentally deleted in Google Cloud Console and create new key. 3. Process queued appointment requests from `workflow_errors` table manually. |
| Evolution API session lost | LOW | 1. Re-scan QR code via Evolution API admin panel. 2. Process any messages that arrived during downtime (stored in Evolution API's local queue if configured). 3. Notify clinic owner of gap in availability. |
| Meta API review rejected | MEDIUM | 1. Read rejection reason carefully — usually specific. 2. Update privacy policy URL and app description per feedback. 3. Resubmit with clearer use case description. 4. Use Buffer/Zapier integration as temporary workaround for social posting. |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| WhatsApp number ban from bulk sends | Phase: WhatsApp messaging implementation | Test: run a 20-message campaign, verify n8n logs show 3–8s gaps; check account status after 48 hours |
| n8n queue overwhelm on VPS RAM | Phase: Infrastructure setup (Phase 1) | Test: simulate 50 concurrent webhook arrivals; verify queue drains without OOM; monitor memory |
| LLM hallucinations in medical context | Phase: AI chatbot implementation | Test: ask bot 10 questions not in knowledge base; verify all 10 escalate to human rather than hallucinate |
| Evolution API session instability | Phase: WhatsApp core infrastructure | Test: run for 7 days with cron health check; verify at least one auto-reconnect event is captured in logs |
| Social media API approval delay | Phase 1 (project setup) — submit immediately | Verification: Meta App Status shows "Live" for required permissions before social publishing phase begins |
| Google Calendar token expiry | Phase: Calendar integration | Test: deliberately expire credentials and verify health check detects failure within 24 hours |
| Ollama latency breaking UX | Phase: AI chatbot implementation (before launch) | Benchmark: measure p95 response time on VPS; must be under 6 seconds or switch to cloud API |
| n8n workflow spaghetti | All phases — naming conventions enforced from Phase 1 | Review: every workflow must be explainable in one sentence; no hardcoded values visible in any node |
| Patient data unencrypted | Phase 1: database schema design | Audit: verify sensitive columns use encryption at rest; confirm backup files are not plaintext |
| No conversation lock/queue | Phase: AI chatbot implementation | Test: send 5 rapid messages from the same number; verify only 1 LLM call is in-flight at a time |

---

## Sources

- Evolution API GitHub repository and community Discord (training knowledge, issues reported through August 2025)
- Baileys library known limitations (WhatsApp Web protocol reverse engineering, session stability patterns)
- n8n community forum patterns for self-hosted VPS deployments (memory management, queue mode configuration)
- Meta Developer Platform documentation on Instagram Content Publishing API requirements and app review process
- Google OAuth 2.0 documentation on refresh token expiry in Testing vs. Production mode
- LLM deployment best practices for healthcare/medical chatbot contexts (RAG mandatory for factual queries)
- WhatsApp automation community reports on spam detection patterns and number banning thresholds

NOTE: WebSearch and WebFetch were unavailable during this research session. All findings are based on training knowledge (through August 2025). Specific rate limits and thresholds (e.g., exact messages-per-day before ban, exact Ollama inference times) should be validated against current Evolution API documentation and community reports before roadmap phase planning. Confidence is MEDIUM overall; the failure modes described are well-established patterns, but specific numerical thresholds carry LOW confidence and should be treated as starting estimates.

---
*Pitfalls research for: AI WhatsApp CRM + social media manager for clinics on n8n VPS*
*Researched: 2026-03-27*
