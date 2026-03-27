# Project Research Summary

**Project:** AI Social Media Manager & WhatsApp CRM for Dermatology Clinics
**Domain:** WhatsApp automation + social media scheduling + CRM (single-tenant, self-hosted VPS)
**Researched:** 2026-03-27
**Confidence:** MEDIUM

## Executive Summary

This is a two-system product fused into one: a WhatsApp CRM automation platform (chatbot, bulk messaging, appointment booking) and a social media scheduling tool (Instagram + Facebook), unified by a "single action launches both channels" differentiator. No competitor in the SMB clinic space combines these two surfaces atomically. The recommended implementation centers on n8n as the automation backbone, Evolution API as the WhatsApp bridge, PostgreSQL as the single data store, and Streamlit as the admin UI — all containerized with Docker Compose on a Hostinger VPS. This is the most pragmatic self-hosted stack for a solo developer: it avoids per-execution SaaS billing, keeps patient data on-premises, and eliminates the need for a Meta Business API verification (which can take weeks).

The recommended build order starts with infrastructure (Docker Compose scaffold + PostgreSQL schema), then WhatsApp connectivity (Evolution API + QR pairing), then the chatbot (n8n workflows + LLM), then calendar booking, then outbound campaigns, then social publishing, and finally the admin UI. This order respects hard dependencies: you cannot build the chatbot before the WhatsApp bridge works, and you cannot build the unified campaign feature before both the campaign blast and social publishing paths are independently validated. Social media API approval (Meta App Review) is a multi-week external process that must be initiated on Day 1 regardless of when the feature is built.

The two dominant risks are WhatsApp number banning (from unthrottled bulk sends) and LLM hallucinations in a medical context. Both are non-recoverable in their worst forms — a banned number loses the clinic's primary patient communication channel, and a hallucinated medical answer creates legal liability. Both must be addressed in architecture, not patched after the fact: rate limiting with jitter is non-negotiable before the first production campaign, and the AI chatbot must use Retrieval-Augmented Generation (RAG) with a strict escalation policy from day one.

## Key Findings

### Recommended Stack

The core stack is n8n (workflow orchestrator), Evolution API v2 (WhatsApp bridge), PostgreSQL 16 (all persistence), Redis 7 (n8n queue mode), Caddy 2 (reverse proxy + automatic HTTPS), and Streamlit 1.35+ (admin UI). For AI, start with OpenAI gpt-4o-mini rather than local Ollama unless the VPS has confirmed 8+ GB RAM — the 80% FAQ resolution criterion is harder to hit with 3B parameter models, and gpt-4o-mini costs negligibly for single-clinic volume. The entire stack runs in Docker Compose on one VPS with no Kubernetes complexity.

**Core technologies:**
- **n8n (self-hosted):** Workflow orchestrator for all automation — has native nodes for WhatsApp, Google Calendar, Meta API, PostgreSQL, and HTTP webhooks. Eliminates custom code for 70-80% of flows.
- **Evolution API v2:** WhatsApp Web bridge using Baileys. Operational in hours vs. weeks for Meta's official BSP. Pin to a specific release tag; never use latest/main.
- **PostgreSQL 16:** Single database for all structured data — patients, conversations, appointments, campaign logs. Shared by n8n, Evolution API, and Admin UI.
- **Redis 7:** n8n queue mode backend and Evolution API session cache. Required for production stability under concurrent load.
- **Caddy 2:** Reverse proxy with zero-config Let's Encrypt HTTPS. All services stay on Docker's internal network; only Caddy exposes ports 80/443.
- **Streamlit 1.35+:** Admin UI for patient CRM, campaign launch, and conversation view. Fastest path for a Python developer to a functional internal tool without a front-end build pipeline.
- **OpenAI gpt-4o-mini (default) / Ollama (optional):** AI chatbot and copy generation. Default to OpenAI to de-risk MVP; migrate to Ollama in Phase 2 if VPS has 8+ GB RAM and cost matters.

**What to avoid:** Kubernetes, MongoDB, WhatsApp Business Cloud API (requires Meta verification), LangChain (overkill for FAQ+booking), n8n Cloud (billing), and Streamlit without Caddy auth in front.

### Expected Features

**Must have (table stakes — v1):**
- Patient CSV/Excel import with phone normalization
- Contact list with search, filter, and tag/segment management
- WhatsApp session management (connect, reconnect, status visibility)
- Message template creation and preview
- WhatsApp broadcast to segment (with rate limiting)
- Chatbot FAQ auto-reply (hours, location, pricing, services)
- Human handoff with escalation and conversation inbox
- Google Calendar appointment booking via chatbot
- Instagram + Facebook post scheduling
- Unified campaign trigger (one action launches WA blast + social post)
- Admin metrics dashboard (messages sent, bot resolution %, appointments booked, posts published)

**Should have (competitive differentiators — v1.x):**
- Appointment reminders (24h + 1h before via n8n scheduled trigger)
- Post-appointment follow-up message (review/return booking prompt)
- AI-generated copy + image for promotions
- Campaign delivery analytics by patient segment
- Consent/opt-out management (RGPD-lite boolean flag, auto-exclude from broadcasts)

**Defer (v2+):**
- Multi-tenant / multi-clinic support (requires data isolation rewrite)
- Mobile PWA (doubles UI surface)
- TikTok and X (Twitter) auto-posting (API complexity, content format mismatch)
- Full EMR / clinical history (regulatory risk, scope explosion)
- In-app payment collection (PCI surface, PSP integration)
- Deep BI analytics / Metabase embedding

### Architecture Approach

The architecture follows a webhook-driven event loop where n8n is the single entry point for all automation. Evolution API emits webhooks on every inbound WhatsApp message; n8n receives them, queries PostgreSQL for conversation state, calls the LLM, and sends replies back through Evolution API. Conversation state is stored as a state machine in PostgreSQL (not in n8n execution memory), making it resilient to restarts and inspectable by the admin UI. The admin UI reads directly from PostgreSQL (read-only connection) and triggers actions exclusively through n8n webhook endpoints — keeping all automation logic and audit history inside n8n.

**Major components:**
1. **Evolution API (container):** WhatsApp session management, inbound/outbound message routing, webhook emission to n8n
2. **n8n (container):** Workflow orchestrator — receives all webhooks, runs all business logic, calls external APIs, writes results to PostgreSQL. One workflow per domain: `whatsapp.chatbot.inbound`, `whatsapp.campaign.blast`, `social.publish`, `calendar.booking`
3. **PostgreSQL (container):** Single source of truth — patients, conversations (with state machine column), appointments, campaign logs, workflow errors
4. **Redis (container):** n8n queue mode backend; prevents RAM exhaustion during campaign spikes
5. **Streamlit Admin UI (container):** Patient CRM, campaign launcher, conversation monitor, dashboard — reads from DB, writes through n8n webhooks
6. **Caddy (container):** Reverse proxy, automatic HTTPS, WebSocket proxying for n8n UI
7. **Ollama (optional container):** Local LLM inference — only viable with 8+ GB RAM; 3B models usable on CPU, 7B+ are too slow for interactive chatbot

### Critical Pitfalls

1. **WhatsApp number banned from bulk sends** — enforce 3-8 second delays with jitter between each message; never send more than 200-300 messages/day on a new number; personalize every message; implement opt-out in seconds. Rate limiting must be built before the first production campaign, not retrofitted.

2. **LLM hallucinations giving wrong medical or scheduling information** — implement RAG so the LLM only answers from the clinic's verified knowledge base; for scheduling, always query Google Calendar for actual availability (never let the LLM decide); hard-code escalation for any medical question not in the knowledge base. Build this correctly from day one — a patient incident from hallucinated medical advice is a legal and reputational catastrophe.

3. **Evolution API session instability under long-running deployments** — use Evolution API v2 (multi-device), persist session credentials on a Docker volume, implement a 5-minute cron health check that alerts on disconnect, configure `restart: always` in Docker Compose. Sessions can drop randomly; auto-recovery must be operational before any production traffic.

4. **Social media API approval blocking launch timeline** — Meta App Review for publishing permissions takes 2-6 weeks with a non-trivial rejection rate. Submit the app review request in the first week of the project, before building any social publishing code. Use Buffer or a similar approved intermediary as a fallback if the review is delayed.

5. **Google Calendar token expiry breaking appointment booking silently** — use a Google Service Account (server-to-server, never expires) instead of OAuth user credentials (7-day expiry in Testing mode). Implement a daily health check workflow that creates and deletes a test event.

## Implications for Roadmap

Based on research, the dependency graph and pitfall prevention requirements suggest a 7-phase structure:

### Phase 1: Infrastructure Foundation
**Rationale:** Every other component depends on the database schema, Docker Compose topology, and security baseline. Starting here also forces the Meta App Review submission immediately — an external process with a multi-week wait that cannot start later without delaying the social publishing phase.
**Delivers:** Docker Compose stack with PostgreSQL, Redis, Caddy; initial DB schema (patients, conversations, appointments, campaign_log, workflow_errors tables with indexes); `.env` structure; Caddy routing; n8n installed and connected to PostgreSQL; n8n naming conventions and error handler sub-workflow established; Meta App registration submitted.
**Addresses:** Patient data storage prerequisite; n8n queue overwhelm prevention (concurrency limits set here); n8n workflow spaghetti (naming conventions enforced from day one); security baseline (no services exposed directly, Caddy auth).
**Avoids:** n8n RAM exhaustion, patient data unencrypted in DB, services exposed without reverse proxy.

### Phase 2: WhatsApp Core
**Rationale:** WhatsApp connectivity is the dependency for chatbot, appointment booking, campaign blast, and conversation inbox. It must be validated before any automation is built on top. Evolution API session stability monitoring must be operational before production traffic.
**Delivers:** Evolution API v2 connected and pairing with clinic's WhatsApp number; session health monitoring workflow (5-minute cron alert); QR code reconnection procedure documented; WhatsApp send/receive verified end-to-end with a test echo workflow in n8n.
**Addresses:** Evolution API session instability pitfall; WhatsApp session status indicator (table stakes feature).
**Avoids:** Building automation on an unvalidated bridge; session drops going undetected.

### Phase 3: CRM Core
**Rationale:** Patient data is the input required by both the campaign blast and the chatbot (for personalization and opt-out filtering). Building CRM before automation ensures the data model is correct before it is consumed.
**Delivers:** Patient CSV/Excel import (with phone normalization, duplicate handling, malformed row handling); contact list with search and filter; patient tagging and segmentation; message template management; consent/opt-out flag; Streamlit admin UI pages for patient CRM.
**Addresses:** CSV import, contact list, segmentation, message templates (all P1 table stakes); consent management (P2 differentiator, needed before any campaign).
**Avoids:** Campaign blast without segmentation (broadcast spam risk, ban risk).

### Phase 4: AI Chatbot + Appointment Booking
**Rationale:** These two features share the same inbound WhatsApp message flow and the same LLM call. The chatbot FAQ is the prerequisite for the appointment booking flow (booking is triggered by chatbot intent classification). This is the highest-complexity phase; it must be built with RAG and conversation locking from the start.
**Delivers:** n8n inbound chatbot workflow with PostgreSQL conversation state machine; intent classification via LLM (RAG from clinic FAQ knowledge base); FAQ responses (hours, location, pricing, services); human escalation with handoff message; conversation inbox in Streamlit; Google Calendar availability check + appointment booking sub-workflow (using Service Account credentials); typing indicator via Evolution API; per-conversation message queue lock; appointment confirmation message sent via WhatsApp.
**Addresses:** Chatbot FAQ auto-reply, human handoff, conversation inbox, Google Calendar booking (all P1); LLM hallucination prevention; Ollama latency benchmarking (decide local vs. cloud here).
**Avoids:** LLM hallucinations, session state stored in n8n (anti-pattern), single monolithic chatbot workflow (anti-pattern), Google Calendar token expiry (Service Account from day one).
**Research flag:** This phase warrants deeper research during planning — the RAG implementation pattern (FAQ as structured JSON vs. vector store), conversation state machine design, and Evolution API typing indicator API calls should be validated against current Evolution API v2 docs before implementation begins.

### Phase 5: Campaign Blast
**Rationale:** Outbound bulk messaging requires validated patient segmentation (Phase 3) and a healthy WhatsApp session (Phase 2). It is simpler than inbound chatbot because there is no AI involved, but it is the highest-risk phase for account banning. Rate limiting architecture must be the first thing built in this phase.
**Delivers:** WhatsApp broadcast to segment (Split In Batches with 3-8s jitter delay); campaign launch UI in Streamlit with confirmation step ("You are about to send to N patients. Confirm?"); campaign progress tracking in PostgreSQL (campaign_log); campaign status dashboard; opt-out honored immediately on any STOP keyword; campaign cancellation flag checked mid-blast.
**Addresses:** WhatsApp broadcast (P1 table stakes); campaign delivery analytics by segment (P2).
**Avoids:** WhatsApp number ban from unthrottled sends (the single most catastrophic pitfall); accidental campaign trigger without confirmation.

### Phase 6: Social Media Publishing
**Rationale:** Social publishing is architecturally independent from WhatsApp. It can be developed in parallel with Phase 5 if resources allow, but depends on Meta App Review approval (submitted in Phase 1). Instagram first (higher clinic value), Facebook second.
**Delivers:** n8n social publish workflow for Instagram + Facebook via Meta Graph API; post scheduling with datetime; image attachment; Streamlit scheduling UI; post status tracking in PostgreSQL (social_posts table); unified campaign trigger (single action fans out to WhatsApp blast + social post simultaneously — the core differentiator).
**Addresses:** Instagram + Facebook scheduling (P1); unified campaign (P1 — core differentiator).
**Avoids:** TikTok complexity (deferred to v2); building social publishing without API approval (anti-pattern).
**Research flag:** Meta Graph API token refresh automation and Instagram media container two-step publish flow should be validated against current Meta developer docs before implementation — these APIs change frequently.

### Phase 7: Automation Layer + Polish
**Rationale:** Appointment reminders, follow-up messages, AI copy generation, and admin dashboard polish are high-value additions that depend on the validated core (booking, campaigns, social) being stable. These are v1.x features: add after the first clinic validates the core flow.
**Delivers:** Appointment reminder workflow (24h + 1h before, n8n scheduled trigger on Google Calendar events); post-appointment follow-up message (N hours after event end time); AI-generated campaign copy + image (GPT/DALL-E via n8n HTTP node); campaign delivery analytics by segment; full admin metrics dashboard; Metabase integration (if VPS RAM allows).
**Addresses:** Appointment reminders (P2), post-appointment follow-up (P2), AI copy + image (P2), campaign analytics (P2).
**Avoids:** Adding automation before core flow is validated with real clinic users.

### Phase Ordering Rationale

- Phases 1-2 are non-negotiable prerequisites: nothing works without infrastructure and WhatsApp connectivity.
- Phase 3 (CRM) before Phase 4 (Chatbot) because the chatbot needs patient data for personalization and opt-out checks.
- Phase 4 (Chatbot + Booking) is the most complex and highest-risk phase; isolating it ensures focused attention.
- Phase 5 (Campaign Blast) after Phase 4 because the patient segment data model is fully validated, and the WhatsApp send infrastructure is proven.
- Phase 6 (Social) can run in parallel with Phase 5 if resources allow — they share no dependencies after Phase 1.
- Phase 7 (Automation Layer) is deliberately last: add enhancements only after the core loop is validated with a real clinic.
- The unified campaign feature (the core differentiator) lands in Phase 6 because it requires both Phase 5 (WA blast) and Phase 6 (social publishing) to be independently operational first.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (AI Chatbot + Booking):** RAG implementation pattern for FAQ, Evolution API typing indicator API, conversation state machine design, and per-conversation locking in n8n — all require validation against current Evolution API v2 docs and n8n AI Agent node capabilities.
- **Phase 6 (Social Publishing):** Meta Graph API for Instagram publishing uses a two-step media container flow that changes with API versions; token refresh automation for long-running n8n credentials needs verification. Check current Meta Graph API version (v19+ per STACK.md) before building.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Infrastructure):** Docker Compose multi-service setup, Caddy configuration, and PostgreSQL schema design are well-documented, established patterns.
- **Phase 2 (WhatsApp Core):** Evolution API v2 Docker deployment and webhook configuration are well-documented in the Evolution API GitHub repository.
- **Phase 3 (CRM Core):** CSV import, patient segmentation, and Streamlit admin UI are standard patterns with no novel integration challenges.
- **Phase 5 (Campaign Blast):** n8n Split In Batches with delay is a documented pattern; the architecture decisions are clear from pitfalls research.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Core technology choices are well-established. Version numbers (Evolution API v2.x tag, n8n 1.40+) should be verified against Docker Hub and GitHub releases before pinning in docker-compose. No live web search was available during research. |
| Features | MEDIUM | Feature landscape for WhatsApp CRM and social scheduling tools is stable and well-understood. Competitor analysis (WATI, Respond.io, Buffer) is from training data through Aug 2025; spot-check current pricing/features before roadmap finalization. |
| Architecture | MEDIUM-HIGH | Webhook-driven n8n architecture, PostgreSQL conversation state machine, and Docker Compose topology are well-established patterns with high community consensus. Anti-patterns are clearly documented. Specific Evolution API v2 webhook payload schemas should be verified against current docs. |
| Pitfalls | MEDIUM | Failure modes are well-documented from community experience. Specific numerical thresholds (exact messages-per-day before WA ban, exact Ollama inference times on VPS CPU) carry LOW confidence and should be treated as starting estimates to validate empirically. |

**Overall confidence:** MEDIUM

### Gaps to Address

- **VPS RAM budget unknown until provisioned:** The Ollama vs. OpenAI decision depends on actual VPS RAM. Research recommends defaulting to OpenAI gpt-4o-mini for MVP and migrating to Ollama in Phase 7 if the VPS has 8+ GB. Validate actual RAM after VPS provisioning.
- **Specific Evolution API v2 webhook payload schema:** Research is based on training data; verify the exact field names and event types against the current Evolution API v2 GitHub documentation before building the n8n chatbot workflow.
- **Meta App Review timeline:** Research estimates 2-6 weeks. Actual timeline depends on app description quality and Meta's current review queue. Have a fallback plan (Buffer/Make integration) ready if approval is delayed past the Phase 6 start date.
- **WhatsApp ban thresholds:** The 200-300 messages/day ceiling and 3-8s delay recommendation are community-derived estimates, not official Meta documentation. Validate empirically by running a small (20-message) test campaign and monitoring account health before scaling.
- **Google Calendar Service Account scope:** Research recommends Service Account over OAuth, but the setup process (granting service account access to the clinic's specific calendar) should be tested in a dev environment before Phase 4 to avoid blocking appointment booking implementation.

## Sources

### Primary (HIGH confidence)
- n8n official documentation (training knowledge, Aug 2025) — webhook architecture, queue mode, Postgres/Redis requirements, Google Calendar node, sub-workflow patterns
- Docker Compose documentation — multi-service topology, internal networking, volume management, dependency ordering
- Google OAuth 2.0 documentation — refresh token expiry in Testing vs. Production mode, Service Account setup

### Secondary (MEDIUM confidence)
- Evolution API v2 GitHub repository and community (training knowledge through Aug 2025) — webhook event model, REST API, Docker deployment, session stability patterns
- WhatsApp automation community patterns — rate limiting practices, session management, number banning thresholds
- Meta Developer Platform documentation — Instagram Content Publishing API, app review process, required permissions
- Competitor feature analysis: WATI, Respond.io, Callbell, ManyChat, Buffer, Metricool (training data through Aug 2025)
- Ollama documentation — model sizes, RAM requirements, CPU inference latency patterns

### Tertiary (LOW confidence)
- Specific WhatsApp rate limit thresholds (messages/day, delay between sends) — community-derived, not officially documented by Meta; treat as starting estimates
- Specific Ollama inference times on CPU-only VPS — varies by hardware; benchmark on actual provisioned VPS before committing to local LLM
- TikTok Content Posting API availability and approval timeline — frequently changing; verify current status before any roadmap commitment

---
*Research completed: 2026-03-27*
*Ready for roadmap: yes*
