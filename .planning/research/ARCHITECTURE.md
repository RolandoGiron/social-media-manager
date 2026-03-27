# Architecture Research

**Domain:** AI Social Media Manager + WhatsApp CRM on self-hosted VPS
**Researched:** 2026-03-27
**Confidence:** MEDIUM (training data through Aug 2025; web tools unavailable for live verification)

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL LAYER                               │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────┐  │
│  │  WhatsApp    │  │  Facebook /  │  │  Google    │  │  OpenAI/ │  │
│  │  Web (user   │  │  Instagram / │  │  Calendar  │  │  Ollama  │  │
│  │  phone)      │  │  X / TikTok  │  │  API       │  │  (AI)    │  │
│  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘  └────┬─────┘  │
└─────────┼─────────────────┼────────────────┼───────────────┼────────┘
          │ webhook          │ webhook /       │ REST          │ REST
          │                  │ scheduled post  │               │
┌─────────┼─────────────────┼────────────────┼───────────────┼────────┐
│         ▼                  │                 │               │        │
│  ┌─────────────┐           │                 │               │        │
│  │ Evolution   │           │                 │               │        │
│  │ API         │           │                 │               │        │
│  │ (container) │           │                 │               │        │
│  └──────┬──────┘           │                 │               │        │
│         │ webhook events    │                 │               │        │
│         ▼                  ▼                 ▼               ▼        │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                    n8n  (container)                           │    │
│  │                                                               │    │
│  │  ┌─────────────────┐  ┌──────────────┐  ┌────────────────┐  │    │
│  │  │ WhatsApp        │  │ Social Media │  │ CRM / Campaign │  │    │
│  │  │ Chatbot Flows   │  │ Publish      │  │ Blast Flows    │  │    │
│  │  │ (inbound msgs)  │  │ Flows        │  │ (outbound)     │  │    │
│  │  └────────┬────────┘  └──────┬───────┘  └───────┬────────┘  │    │
│  │           │                  │                   │           │    │
│  │           └──────────────────┼───────────────────┘           │    │
│  │                              │                               │    │
│  │                    ┌─────────▼──────────┐                    │    │
│  │                    │  Shared Services   │                    │    │
│  │                    │  - DB queries      │                    │    │
│  │                    │  - AI calls        │                    │    │
│  │                    │  - Calendar ops    │                    │    │
│  │                    └────────────────────┘                    │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                │                                      │
│         ┌──────────────────────┼──────────────────────┐              │
│         ▼                      ▼                      ▼              │
│  ┌─────────────┐  ┌────────────────────┐  ┌──────────────────┐      │
│  │ PostgreSQL  │  │ Redis              │  │ Ollama           │      │
│  │ (container) │  │ (container)        │  │ (container/opt.) │      │
│  │             │  │ Queue + Session    │  │                  │      │
│  │ - patients  │  │ cache              │  │ Local LLM for    │      │
│  │ - appts     │  │                   │  │ chatbot + copy   │      │
│  │ - conv.     │  └────────────────────┘  └──────────────────┘      │
│  │   state     │                                                      │
│  └─────────────┘                                                      │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                    Admin UI  (container)                      │    │
│  │                    Streamlit or Next.js                       │    │
│  │   Dashboard | Patient CRM | Campaigns | Conversation View    │    │
│  └──────────────────────────┬───────────────────────────────────┘    │
│                              │ REST / n8n webhooks                    │
│                              ▼                                        │
│                           n8n (triggers admin-initiated flows)        │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                    Caddy / Nginx  (reverse proxy)             │    │
│  │   admin-ui.domain.com → Admin UI                             │    │
│  │   n8n.domain.com      → n8n                                  │    │
│  │   evolution.domain.com → Evolution API                       │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│                         VPS HOSTINGER                                 │
└───────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Evolution API | WhatsApp session management, inbound/outbound message routing, webhook emission | Docker container, exposes REST API + emits webhooks on message/status events |
| n8n | Workflow orchestrator — receives webhooks, runs logic, calls external APIs, writes to DB | Docker container with PostgreSQL backend, webhook server on port 5678 |
| PostgreSQL | Single source of truth for patients, appointments, conversation state, campaign history | Docker container, shared by both n8n (internal) and Admin UI (direct queries) |
| Redis | Session cache for chatbot state machine, n8n queue worker message broker | Docker container, optional but required when n8n runs in queue mode |
| Ollama | Local LLM inference for chatbot responses and marketing copy generation | Docker container (CPU/GPU), exposes OpenAI-compatible REST API on port 11434 |
| Admin UI | Operational interface for clinic staff — patient CRM, campaign launcher, conversation monitor | Streamlit (rapid) or Next.js (extensible), container on port 8501 / 3000 |
| Caddy | Reverse proxy with automatic HTTPS via Let's Encrypt | Docker container or host-level service, routes by subdomain/path |

## Recommended Project Structure

```
/opt/social-media-manager/          # VPS deployment root
├── docker-compose.yml              # All services declared here
├── docker-compose.override.yml     # Dev/staging overrides
├── .env                            # Secrets (not in git)
├── .env.example                    # Template committed to git
│
├── caddy/
│   └── Caddyfile                   # Reverse proxy routing rules
│
├── n8n/
│   ├── workflows/                  # Exported workflow JSON files (version controlled)
│   │   ├── whatsapp-chatbot.json
│   │   ├── social-publish.json
│   │   ├── campaign-blast.json
│   │   └── calendar-booking.json
│   └── credentials/                # Credential backup scripts (not secrets themselves)
│
├── evolution-api/
│   └── instances/                  # Persisted WhatsApp session data (volume-mounted)
│
├── postgres/
│   ├── init/                       # SQL init scripts run on first start
│   │   ├── 001_schema.sql          # Table definitions
│   │   └── 002_seed.sql            # Static reference data
│   └── backups/                    # Automated backup scripts
│
├── admin-ui/
│   ├── src/                        # Application source code
│   │   ├── pages/                  # Streamlit pages or Next.js routes
│   │   ├── components/             # Reusable UI components
│   │   ├── services/               # DB and n8n API client wrappers
│   │   └── utils/
│   ├── Dockerfile
│   └── requirements.txt / package.json
│
└── scripts/
    ├── backup.sh                   # DB backup cron target
    ├── restore.sh
    └── deploy.sh                   # Pull + restart containers
```

### Structure Rationale

- **n8n/workflows/:** Workflow JSON exported from n8n UI and committed to git. This is the primary code artifact — treat it as source code, not configuration.
- **postgres/init/:** Schema migrations run automatically on container first-start. For v1 single-tenant, this is sufficient. For multi-tenant v2, migrate to Flyway or Liquibase.
- **admin-ui/src/services/:** Isolates DB and n8n coupling. Admin UI should not embed raw SQL everywhere — centralize into service modules so switching from Streamlit to Next.js is less painful.
- **scripts/:** Operational runbooks as code. Backup, restore, and deploy scripts belong in the repo.

## Architectural Patterns

### Pattern 1: Webhook-Driven Event Loop (n8n as Event Bus)

**What:** Every external event (WhatsApp message received, social post liked, appointment updated) fires a webhook to n8n. n8n is the single entry point for all automation logic. Nothing calls another service directly — everything passes through n8n workflows.

**When to use:** Default pattern for this stack. n8n's native trigger model is webhook-first.

**Trade-offs:**
- Pro: All logic is inspectable in n8n UI; no hidden service-to-service calls
- Pro: Retry logic, error handling, and logging are built into n8n
- Con: n8n becomes a single point of failure — plan for restart policy and health checks
- Con: Complex chatbot state machines are awkward in n8n's node graph; supplement with DB state

**Example flow (inbound WhatsApp message):**
```
Evolution API emits webhook POST /webhook/whatsapp-inbound
  → n8n Webhook node receives payload
  → Switch node: new conversation? vs existing?
  → If new: INSERT conversation row in PostgreSQL
  → Classify intent: HTTP node → Ollama /api/chat
  → Based on intent: route to booking sub-workflow OR FAQ sub-workflow OR escalate
  → Evolution API node: send reply message
  → UPDATE conversation state in PostgreSQL
```

### Pattern 2: State Machine via PostgreSQL for Conversation Context

**What:** The chatbot's conversation state is stored in a `conversations` table with a `state` column (enum: `new`, `awaiting_intent`, `booking_flow`, `human_handoff`, `closed`). Each n8n webhook execution reads current state, transitions it, writes it back. n8n is stateless between executions.

**When to use:** Always for WhatsApp chatbots. n8n execution context does not persist between webhook calls from the same user.

**Trade-offs:**
- Pro: Survives n8n restarts; auditable history
- Pro: Enables human agents to see full conversation thread in Admin UI
- Con: Requires careful locking for concurrent messages from the same contact (use PostgreSQL row-level locking via `SELECT ... FOR UPDATE`)
- Con: State machine complexity grows; keep it to 5-7 states max in v1

**Example schema:**
```sql
CREATE TABLE conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  wa_contact_id TEXT NOT NULL,        -- WhatsApp JID (phone@s.whatsapp.net)
  state TEXT NOT NULL DEFAULT 'new',  -- state machine value
  context JSONB,                       -- slot values (name, appointment_type, etc.)
  assigned_agent TEXT,                 -- NULL = bot, email = human
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

### Pattern 3: n8n Sub-Workflows for Reusable Logic

**What:** Complex repeated operations (AI intent classification, Google Calendar availability check, Evolution API send-message wrapper) are implemented as n8n "sub-workflows" triggered via the Execute Workflow node. The main chatbot flow calls these sub-workflows instead of duplicating logic.

**When to use:** Any logic called from more than one parent workflow.

**Trade-offs:**
- Pro: DRY principle in n8n's visual graph
- Pro: Sub-workflows can be tested independently
- Con: Debugging across workflow boundaries requires navigating multiple execution logs
- Con: Sub-workflow calls are synchronous by default in n8n — adds latency; use async only when result is not needed immediately

### Pattern 4: Campaign Blast as Batched Async Jobs

**What:** Sending WhatsApp messages to a patient segment (e.g., 200 patients) is split into batches of 20-50 using n8n's Split In Batches node. Each batch has a delay (2-5 seconds) between sends to avoid WhatsApp rate limits and session bans.

**When to use:** Any outbound bulk WhatsApp operation.

**Trade-offs:**
- Pro: Respects unofficial WhatsApp rate limits (critical for account health)
- Pro: n8n handles retry on transient failures per batch
- Con: A 200-person campaign may take 10-20 minutes to complete — UI must reflect async status
- Con: Job cancellation mid-blast requires a cancellation flag in PostgreSQL checked by the n8n loop

## Data Flow

### Inbound WhatsApp Message Flow

```
User sends WhatsApp message
    ↓
Evolution API (WhatsApp bridge)
    ↓ POST webhook to n8n
n8n Webhook Trigger node
    ↓
PostgreSQL: SELECT conversation WHERE wa_contact_id = $1 FOR UPDATE
    ↓
Switch: state = 'human_handoff'? → Notify agent via n8n, skip AI
    ↓
Ollama / OpenAI: classify intent + generate response
    ↓
(if booking intent) Google Calendar API: check availability + create event
    ↓
PostgreSQL: UPDATE conversation state + context
    ↓
Evolution API REST: sendMessage
    ↓
User receives WhatsApp reply
```

### Outbound Campaign Blast Flow

```
Admin triggers campaign in Admin UI
    ↓ POST to n8n webhook (campaign endpoint)
n8n receives: segment_id + message_template + media_url
    ↓
PostgreSQL: SELECT patients WHERE segment = $1
    ↓
n8n Split In Batches (batch_size=30)
    ↓ [loop with 3s delay between batches]
For each patient:
    Evolution API: sendMessage (text + optional image)
    PostgreSQL: INSERT campaign_log (patient_id, status, sent_at)
    ↓
n8n: emit final webhook to Admin UI (campaign_complete event)
Admin UI: refresh campaign status dashboard
```

### Social Media Publish Flow

```
Admin triggers "publish promotion" in Admin UI
    ↓ (or scheduled via n8n cron trigger)
n8n: fetch promotion data from PostgreSQL
    ↓
(if copy not provided) Ollama/OpenAI: generate post caption
    ↓
(if image not provided) DALL-E / Stability AI: generate image → save to disk/S3
    ↓
n8n: Fan-out to social platforms in parallel:
    ├─ Facebook Graph API: POST /me/feed
    ├─ Instagram Graph API: POST media container → publish
    ├─ X (Twitter) API v2: POST /tweets
    └─ TikTok Content Posting API: upload video/image
    ↓
PostgreSQL: INSERT social_posts (platform, post_id, published_at, status)
    ↓
Admin UI: shows published status per platform
```

### Admin UI to n8n Integration Pattern

```
Admin UI (Streamlit/Next.js)
    │
    ├─ READ operations:  direct PostgreSQL queries (read-only DB user)
    │   Patient list, conversation history, campaign stats, appointment list
    │
    └─ WRITE/ACTION operations: POST to n8n webhook endpoints
        Campaign blast: POST /webhook/campaign-trigger {segment_id, message}
        Social publish:  POST /webhook/social-publish  {content, platforms}
        Manual send:     POST /webhook/manual-wa-send  {contact_id, message}
        Escalate:        POST /webhook/escalate        {conversation_id}
```

**Key principle:** Admin UI reads directly from PostgreSQL for display (fast, no n8n overhead). Admin UI writes/triggers through n8n webhooks (so all action logic stays in n8n workflows, not scattered in UI code).

## Docker Compose Service Topology

```yaml
# Dependency order (build order):
#   1. postgres          — all others depend on it
#   2. redis             — n8n queue mode depends on it
#   3. evolution-api     — depends on postgres (own tables)
#   4. ollama            — independent, but large image
#   5. n8n               — depends on postgres + redis + (evolution-api running to configure)
#   6. admin-ui          — depends on postgres + n8n webhooks being live
#   7. caddy             — depends on all services being up

services:
  postgres:
    image: postgres:16-alpine
    volumes: [postgres_data:/var/lib/postgresql/data, ./postgres/init:/docker-entrypoint-initdb.d]
    environment: {POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD}

  redis:
    image: redis:7-alpine
    # Used for n8n queue mode and optional session caching

  evolution-api:
    image: atendai/evolution-api:v2
    depends_on: [postgres]
    environment: {DATABASE_URL, WEBHOOK_GLOBAL_URL: "http://n8n:5678/webhook/..."}

  ollama:
    image: ollama/ollama:latest
    volumes: [ollama_data:/root/.ollama]
    # GPU passthrough if available; CPU-only fallback is slow for large models

  n8n:
    image: n8nio/n8n:latest
    depends_on: [postgres, redis]
    environment: {DB_TYPE: postgresdb, QUEUE_BULL_REDIS_HOST: redis, N8N_ENCRYPTION_KEY}
    volumes: [./n8n/workflows:/home/node/.n8n/workflows]  # for backup/export

  admin-ui:
    build: ./admin-ui
    depends_on: [postgres]
    environment: {DATABASE_URL, N8N_WEBHOOK_BASE_URL: "http://n8n:5678"}

  caddy:
    image: caddy:2-alpine
    volumes: [./caddy/Caddyfile:/etc/caddy/Caddyfile, caddy_data:/data]
    ports: ["80:80", "443:443"]
```

## Suggested Build Order

Building in this order respects hard dependencies and enables integration testing at each layer.

| Stage | Components | Rationale |
|-------|------------|-----------|
| 1. Infrastructure foundation | PostgreSQL + Docker Compose skeleton | Everything depends on DB; establish schema before any service runs |
| 2. WhatsApp bridge | Evolution API + QR code pairing | Validate WhatsApp connection works before building any automation on top |
| 3. Core n8n plumbing | n8n installed, connected to PostgreSQL, Evolution API webhook wired | Prove the webhook pipeline works end-to-end with a trivial echo workflow |
| 4. Chatbot v1 (FAQ only) | n8n chatbot workflow + PostgreSQL conversation state | First real feature; validates the core loop. No AI required yet (keyword matching) |
| 5. AI layer | Ollama (or OpenAI key) wired into chatbot workflow | Upgrade chatbot from keyword to intent-based. Isolated change. |
| 6. Calendar booking | Google Calendar API + booking sub-workflow | Builds on validated chatbot; adds the highest-value automation |
| 7. Campaign blast | Outbound WhatsApp flow + patient segment query | Requires patient data in DB; outbound is simpler than inbound chatbot |
| 8. Social media publishing | n8n social publish workflow for each platform | Independent from WhatsApp; add platforms incrementally (Instagram first) |
| 9. Admin UI | Streamlit dashboard connecting to DB + n8n webhooks | Built last so all underlying data and trigger endpoints already exist |
| 10. Reverse proxy + TLS | Caddy in front of all services | Productionize after flows are validated |

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1-50 concurrent bot users | Single n8n container in main (non-queue) mode; all fits on 4GB VPS |
| 50-200 concurrent bot users | Enable n8n queue mode with Redis; separate n8n worker container; upgrade VPS to 8GB |
| 200+ concurrent bot users | Evolution API horizontal scaling is difficult (WhatsApp session is stateful per number); consider multiple WhatsApp numbers; move to managed PostgreSQL |

### Scaling Priorities

1. **First bottleneck:** n8n webhook processing — each inbound message spawns a workflow execution. At ~100 concurrent, the single n8n process becomes the bottleneck. Fix: queue mode with 2-4 workers.
2. **Second bottleneck:** Ollama LLM inference on CPU — response latency degrades under concurrent requests. Fix: switch to OpenAI API for chatbot (faster, predictable latency) and reserve Ollama for batch tasks like copy generation.
3. **Third bottleneck:** PostgreSQL connection pool — n8n + Admin UI + Evolution API all connecting. Fix: add PgBouncer connection pooler between services and PostgreSQL.

## Anti-Patterns

### Anti-Pattern 1: Storing Chatbot State Inside n8n Execution

**What people do:** Use n8n's "Wait" node or static data to hold conversation state between webhook calls.

**Why it's wrong:** n8n static data has concurrency issues; Wait nodes consume execution slots; state is lost on container restart. Two messages from the same user arriving within seconds cause race conditions.

**Do this instead:** Store all conversation state in PostgreSQL `conversations` table. Every n8n execution is stateless — read state at start, write at end. Use `SELECT ... FOR UPDATE` to prevent concurrent execution races.

### Anti-Pattern 2: All Logic in One Giant Workflow

**What people do:** Build a single 50-node n8n workflow that handles WhatsApp chatbot + campaign + social publishing in one graph.

**Why it's wrong:** Debugging is impossible. A single error stops all automation. Concurrent executions of the same workflow can conflict.

**Do this instead:** Separate workflows per domain (chatbot-inbound, campaign-blast, social-publish, calendar-booking). Use sub-workflows for shared operations (send-wa-message, classify-intent). Each workflow has one trigger and one responsibility.

### Anti-Pattern 3: Sending WhatsApp Blasts Without Rate Limiting

**What people do:** Use n8n's loop to send 200 messages as fast as possible.

**Why it's wrong:** WhatsApp Web (which Evolution API uses) will flag the number as spam and ban the session if messages are sent too fast. Account recovery is manual and slow.

**Do this instead:** Split In Batches with explicit delays (3-5 seconds between messages, 30+ seconds between batches). Log each send to PostgreSQL before executing so a cancelled/failed blast is resumable.

### Anti-Pattern 4: Admin UI Triggering PostgreSQL Writes Directly for Actions

**What people do:** Admin UI has direct DB write access and inserts campaign records, updates patient data, triggers sends — all bypassing n8n.

**Why it's wrong:** Automation logic is now split between n8n workflows and the UI backend. Testing, debugging, and auditing become inconsistent. n8n's execution log (which is your audit trail) is bypassed.

**Do this instead:** Admin UI writes only to n8n webhooks for any action that has side effects. Admin UI may do direct DB reads (read-only connection string). This keeps n8n as the single source of truth for all automation execution history.

### Anti-Pattern 5: Skipping the Reverse Proxy and Exposing n8n Directly

**What people do:** Open port 5678 on the VPS firewall and point Evolution API webhooks directly to n8n's port.

**Why it's wrong:** n8n's webhook URLs are not secret by default. Anyone can trigger your workflows. No TLS. n8n port is publicly visible.

**Do this instead:** All services communicate over Docker's internal network. Only Caddy binds to host ports 80/443. All webhook URLs use HTTPS subdomains (n8n.yourdomain.com). Set n8n webhook authentication where possible.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Evolution API | n8n HTTP Request node calls REST API; Evolution API POSTs webhooks to n8n endpoint | Webhook URL must be reachable from within Docker network: `http://n8n:5678/webhook/...` |
| Google Calendar API | n8n built-in Google Calendar node (OAuth2) | Credential stored in n8n; sub-workflow for availability check + event creation |
| Facebook / Instagram Graph API | n8n HTTP Request node (no native node for all endpoints) | Requires approved Facebook App; token refresh automation needed |
| X (Twitter) API v2 | n8n HTTP Request with OAuth 1.0a | Free tier severely rate-limited (1500 tweets/month); confirm tier before building |
| TikTok Content Posting API | n8n HTTP Request | Most complex auth flow; build last; requires business account |
| OpenAI / Ollama | n8n HTTP Request to Ollama (`http://ollama:11434/v1/chat/completions`) or OpenAI node | Ollama uses OpenAI-compatible API — same n8n node works for both, swap base URL |
| Stability AI / DALL-E | n8n HTTP Request for image generation | Optional; needed for AI-generated campaign images |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Evolution API → n8n | HTTP webhook (POST) over Docker internal network | Evolution API pushes; n8n receives. Configure webhook URL at Evolution API startup. |
| n8n → Evolution API | HTTP REST (POST) over Docker internal network | n8n calls Evolution API to send messages. Uses `http://evolution-api:8080` as base URL. |
| n8n → PostgreSQL | PostgreSQL protocol (native n8n Postgres node) | n8n connects with a dedicated user with CRUD but not DDL privileges |
| n8n → Ollama | HTTP REST over Docker internal network | `http://ollama:11434` — OpenAI-compatible endpoint |
| Admin UI → PostgreSQL | PostgreSQL protocol (read-only user) | Direct queries for display data only |
| Admin UI → n8n | HTTP webhook (POST) | Admin UI fires trigger webhooks; n8n returns immediate 200 ACK, processes async |
| Caddy → all services | HTTP reverse proxy over Docker internal network | Services never expose ports to host; only Caddy does |

## Sources

- n8n documentation (training knowledge, Aug 2025): self-hosted deployment, queue mode, webhook architecture, sub-workflow patterns
- Evolution API v2 documentation (training knowledge): webhook event model, REST API for send/receive, Docker deployment
- WhatsApp automation community patterns (training knowledge): rate limiting practices, session management, chatbot state machine patterns
- Docker Compose multi-service patterns (training knowledge): service dependency ordering, internal networking, volume management
- Confidence note: All findings are from training data (Aug 2025 cutoff). Web tools were unavailable during this research session. Core architectural patterns for these well-established tools are unlikely to have changed materially, but version-specific details (Evolution API v2 exact webhook payload schema, n8n node names) should be verified against current official documentation before implementation.

---
*Architecture research for: AI Social Media Manager + WhatsApp CRM on n8n/VPS*
*Researched: 2026-03-27*
