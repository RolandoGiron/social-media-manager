<!-- GSD:project-start source:PROJECT.md -->
## Project

**AI Social Media Manager & CRM**

Plataforma de automatización de marketing y atención al cliente para negocios físicos, comenzando con clínicas dermatológicas. Centraliza la gestión de WhatsApp (campañas masivas + chatbot IA), publicación en redes sociales, agendamiento de citas vía Google Calendar, y un CRM ligero para segmentar y activar bases de datos de pacientes. Construida por un solo developer sobre VPS Hostinger con n8n como orquestador central.

**Core Value:** El dueño de la clínica puede lanzar una promoción dirigida — que llega a WhatsApp de los pacientes relevantes Y se publica en redes sociales — sin tocar ningún sistema manualmente.

### Constraints

- **Infraestructura:** VPS Hostinger (recursos limitados) — arquitectura debe ser eficiente; evitar servicios que requieran múltiples VPS
- **WhatsApp:** Evolution API es no-oficial — riesgo de cambios en la API de WhatsApp Web; aceptado conscientemente para arrancar rápido
- **Concurrencia:** Soporte para +100 usuarios concurrentes en el bot — procesamiento asíncrono obligatorio
- **Privacidad:** Datos médicos encriptados en reposo; logs de IA anonimizados aunque normativa local no lo exija
- **Disponibilidad:** 24/7 — el chatbot atiende fuera de horario de la clínica
- **Solo developer:** Scope de v1 debe ser ejecutable por una persona; priorizamos flujos mínimos viables sobre features completas
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Core Technologies
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| n8n | 1.x (latest stable, ~1.40+) | Workflow orchestrator — all automation logic lives here | Purpose-built for API integration workflows; has native nodes for WhatsApp (via HTTP), Google Calendar, social APIs, PostgreSQL, and HTTP webhooks. Eliminates custom code for 70-80% of flows. Self-hosted = no per-execution billing. |
| Evolution API | 2.x (v2 series) | WhatsApp Web bridge — sends/receives messages, manages sessions | Most mature open-source WhatsApp Web implementation. v2 rewrote the REST interface, added multi-session support, and webhook delivery for incoming messages. No Meta Business account required. Built on Baileys (Node.js). |
| PostgreSQL | 16.x | Primary persistent store — patients, conversations, appointments | Single reliable database for all structured data. n8n ships with native Postgres node. Evolution API can persist session state in Postgres. Avoids multi-DB complexity on a resource-constrained VPS. |
| Redis | 7.x | Queue backend for n8n; session cache for Evolution API | n8n in "queue mode" requires Redis for job distribution across workers. Evolution API uses Redis for WebSocket session caching. 7.x is current stable with improved memory efficiency. |
| Docker Compose | v2.x (compose plugin) | Service orchestration on VPS | Single compose file manages all services: n8n, Evolution API, Postgres, Redis, Caddy. Restart policies + named volumes = production-ready without Kubernetes complexity. |
| Caddy | 2.x | Reverse proxy + automatic HTTPS | Caddy auto-provisions Let's Encrypt certs with zero config. On Hostinger VPS with a domain, this eliminates the nginx + certbot maintenance cycle. Native support for WebSocket proxying (needed for n8n UI and Evolution API). |
| Ollama | 0.3.x | Local LLM inference for chatbot responses | Runs models like llama3, mistral, or phi-3-mini entirely on the VPS. Privacy-safe for patient data. Tradeoff: requires 4-8 GB RAM minimum for useful models. See "Stack Patterns by Variant" for the cloud fallback path. |
### Supporting Libraries / Services
| Library / Service | Version | Purpose | When to Use |
|-------------------|---------|---------|-------------|
| Baileys (via Evolution API) | — (bundled) | WhatsApp Web protocol implementation | You never call Baileys directly; Evolution API wraps it. Relevant to know because Evolution API stability depends on Baileys keeping up with WhatsApp Web protocol changes. |
| n8n-nodes-evolution-api (community node) | Latest from npm | Pre-built n8n nodes for Evolution API operations | Use instead of raw HTTP nodes when working with Evolution API in n8n. Check npmjs.com for the current maintained fork — the ecosystem has multiple competing community nodes. |
| Streamlit | 1.35+ | Admin UI for CRM operations (patient import, segmentation, campaign triggers) | Best choice for a solo Python developer who needs a functional internal tool quickly. No front-end build pipeline. Runs as a separate Docker service on an internal port, proxied by Caddy with basic auth. |
| pgAdmin 4 | 8.x | PostgreSQL administration | Run in Docker on an internal port during development. Remove or restrict in production — Caddy basic auth is sufficient. |
| Metabase | 0.49+ (open-source) | Dashboard and metrics (messages responded, appointments booked, engagement) | Alternative to building a custom dashboard in Streamlit. Metabase connects directly to Postgres and provides drag-and-drop dashboards with zero code. Runs ~512 MB RAM — evaluate against VPS memory budget. |
| Gotenberg / LibreOffice | — | PDF generation for reports | Only if clinic needs PDF appointment confirmations. Defer to v2. |
| Google Calendar API (REST) | v3 | Appointment booking via chatbot | n8n has a native Google Calendar node. Use OAuth2 service account for the clinic's calendar. The n8n credential manager handles token refresh. |
| Meta Graph API | v19+ | Facebook + Instagram publishing | n8n has native Facebook Graph API node. Required for Instagram post scheduling (Business accounts only). |
| TikTok for Business API | v2 | TikTok post publishing | Less mature than Meta API. n8n has HTTP node fallback. Verify TikTok API availability in your region before committing. |
| OpenAI API | gpt-4o-mini or gpt-4o | Cloud AI fallback if Ollama quality is insufficient | gpt-4o-mini is the cost-efficient choice (~$0.15/1M input tokens). Use only if Ollama on the VPS RAM budget produces unacceptable chatbot quality. n8n has a native OpenAI node. |
### Development Tools
| Tool | Purpose | Notes |
|------|---------|-------|
| Docker Compose (local) | Mirror production environment on dev machine | Use the same compose file with `ENVIRONMENT=development` overrides. Never develop directly against the production VPS. |
| n8n (local Docker) | Develop and test workflows without risk | Export workflows as JSON and commit to git. n8n CLI (`n8n export:workflow`) automates this. |
| DBeaver | PostgreSQL GUI for development | Free, cross-platform, handles Postgres well. Better than pgAdmin for query work. |
| git | Version control for compose files, n8n workflow JSONs, Streamlit code | Store the entire `.planning/` directory, all compose files, n8n exported workflows, and Streamlit app in a single private repo. |
| Portainer CE (optional) | Docker management UI on VPS | Useful for monitoring container health without SSH. Adds ~256 MB RAM. Evaluate against memory budget. |
## Installation
# All services run via Docker Compose — no direct npm/pip installs on the host.
# Recommended directory layout on VPS:
#   /opt/clinic-crm/
#     docker-compose.yml
#     .env                   # secrets — never committed
#     n8n/                   # n8n data volume mount
#     postgres/              # postgres data volume mount
#     evolution/             # evolution api data volume mount
#     streamlit/             # streamlit app source
# Core services pull (verify tags on Docker Hub before using):
# Streamlit app dependencies (in requirements.txt, installed inside Docker):
# streamlit>=1.35
# psycopg2-binary
# pandas
# openpyxl        # for Excel import
# python-dotenv
## Alternatives Considered
| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| n8n (self-hosted) | Make.com / Zapier | Only if you have zero developer capacity and accept recurring SaaS cost + vendor lock-in. For a solo developer who can maintain a VPS, n8n self-hosted is strictly better. |
| Evolution API v2 | Twilio WhatsApp API | When you need Meta-approved official delivery guarantees and per-message cost is acceptable. Twilio requires a verified WhatsApp Business account (days/weeks approval). Evolution API is operational in hours. |
| Evolution API v2 | WPPConnect | WPPConnect is an older project with less active maintenance. Evolution API has better REST API design and a more active community as of 2025. |
| Caddy | Nginx + Certbot | Use Nginx if you already have deep Nginx expertise or need advanced load-balancing configs. Caddy is simpler for VPS single-node deployments. |
| PostgreSQL 16 | MySQL / MariaDB | Only if you're migrating from an existing MySQL setup. Postgres has better JSON support, which is useful for storing n8n execution metadata and Evolution API message payloads. |
| Ollama (local) | OpenAI API | Use OpenAI when: VPS has < 8 GB RAM, response quality from local models is below 80% FAQ resolution target, or latency > 3s is unacceptable. gpt-4o-mini is the economic cloud choice. |
| Streamlit | Retool / AppSmith | Retool/AppSmith make sense if you want richer UI components without writing Python. Streamlit is better for a Python-fluent developer who wants everything in code and version control. |
| Streamlit | n8n built-in UI (forms/webhooks) | n8n's form trigger node can handle simple data entry. Use for lightweight internal triggers. Streamlit is needed for bulk CSV import, patient segmentation, and campaign dashboards. |
| Metabase | Grafana + Prometheus | Grafana/Prometheus is overkill for a single-tenant CRM dashboard. Metabase queries Postgres directly without a metrics pipeline. |
| Redis 7 | Valkey | Valkey is the Redis fork after the license change. Both work identically for n8n queue mode. Redis 7 has more ecosystem tooling; Valkey is the future-proof choice if license is a concern. |
## What NOT to Use
| Avoid | Why | Use Instead |
|-------|-----|-------------|
| n8n Cloud | Monthly billing scales with executions; loses the privacy/cost advantage of self-hosting. For a single clinic, self-hosted is ~$0/month beyond VPS cost. | n8n self-hosted on Docker |
| Kubernetes / K8s | Massive operational overhead for a single-developer, single-tenant deployment on one VPS. Hostinger VPS doesn't have the resource headroom for a K8s control plane. | Docker Compose with restart policies |
| MongoDB | n8n, Evolution API, and PostgreSQL all assume relational structure. Introducing a second database type adds operational complexity with no benefit at this scale. | PostgreSQL for all persistence |
| WhatsApp Business Cloud API (Meta official) | Requires Meta business verification (days/weeks), per-message costs, and won't work with an existing personal/business number that already has a contact list. Evolution API uses the existing number immediately. | Evolution API v2 |
| LangChain (heavy framework) | Overkill for FAQ chatbot and appointment booking. Adds Python dependency complexity, slower cold starts, and more failure surface. n8n's AI Agent node (built on LangChain concepts) is sufficient. | n8n AI Agent node + Ollama/OpenAI node directly |
| Separate VPS per service | Hostinger single VPS is the constraint. Docker Compose on one host handles all services within ~4-8 GB RAM budget if services are configured properly. | All services on one Docker Compose stack |
| Streamlit in production without auth | Streamlit has no built-in authentication. Exposing the admin UI directly is a security risk. | Caddy basic auth or IP allowlist in front of Streamlit |
| Latest/unstable Evolution API tags | Evolution API main branch can be unstable. WhatsApp Web protocol changes can break Baileys (the underlying library) without warning. | Pin to a specific release tag (e.g., v2.1.1); update deliberately after testing |
## Stack Patterns by Variant
- Skip Ollama — it requires minimum 4 GB just for phi-3-mini (3.8B), leaving no headroom for other services
- Use OpenAI gpt-4o-mini as the AI backend
- Disable Metabase; use Streamlit charts instead
- Set PostgreSQL `max_connections=50`, n8n `EXECUTIONS_DATA_MAX_AGE=168` (prune old executions)
- Total estimated footprint: n8n ~512 MB, Evolution API ~256 MB, Postgres ~256 MB, Redis ~64 MB, Caddy ~32 MB, Streamlit ~256 MB = ~1.4 GB baseline, leaving headroom for Ollama only if 8 GB+
- Run Ollama with llama3.2:3b or phi-3-mini:3.8b — adequate for FAQ + appointment FAQ
- Run Metabase for the dashboard requirement
- Set Ollama `OLLAMA_NUM_PARALLEL=1` to prevent memory thrashing from concurrent requests
- Upgrade to mistral:7b if response quality is insufficient and RAM allows
- Add session persistence via Postgres (Evolution API supports `DATABASE_CONNECTION_CLIENT_NAME=postgresql`)
- Enable `CONFIG_SESSION_PHONE_CLIENT` and `CONFIG_SESSION_PHONE_NAME` in Evolution API env to set a stable device name
- Set up n8n workflow to alert on Evolution API connection webhook events (QRCODE_UPDATED, CONNECTION_UPDATE)
- Start with n8n + Meta Graph API + Google OAuth — no Evolution API needed
- Add Evolution API as Phase 2 once social publishing workflow is proven stable
- This reduces initial complexity significantly
- Switch from local Ollama to OpenAI gpt-4o-mini immediately — don't optimize local models; the cost is negligible at single-clinic scale
- Build a FAQ knowledge base as a static JSON file loaded into the n8n AI Agent's system prompt — structured context outperforms fine-tuning for FAQ use cases
## Version Compatibility
| Package | Compatible With | Notes |
|---------|-----------------|-------|
| n8n 1.x | PostgreSQL 14, 15, 16 | n8n uses `typeorm` for Postgres; all modern Postgres versions work. Pin to Postgres 16. |
| n8n 1.x | Redis 6.x, 7.x | Queue mode tested with both. Redis 7 preferred for memory efficiency. |
| Evolution API v2.x | Node.js 20 (internal) | The Docker image handles Node version; don't expose the Node runtime directly. |
| Evolution API v2.x | PostgreSQL 15, 16 | v2 added Postgres persistence support. Earlier v1.x was Redis-only for session storage. |
| Streamlit 1.35+ | Python 3.9, 3.10, 3.11 | Use Python 3.11 in the Streamlit Docker image for latest stdlib support. |
| Caddy 2.x | n8n websockets | Caddy 2 handles WebSocket upgrade automatically — no special config needed for n8n UI. |
| Ollama 0.3.x | CUDA (Nvidia GPU) optional | On a CPU-only VPS, Ollama works but inference is 5-15x slower. 3B parameter models are usable (~2-4s/response on modern CPU). 7B+ models are too slow for interactive chatbot use on CPU. |
## Critical Decisions Summary
### Decision 1: Ollama vs. OpenAI for the Chatbot
### Decision 2: Streamlit vs. n8n Forms for Admin UI
### Decision 3: Evolution API Session Stability
## Sources
- Training data (architecture knowledge, library ecosystems) — covers through August 2025
- n8n official docs (https://docs.n8n.io) — HIGH confidence on n8n capabilities and Postgres/Redis requirements
- Evolution API GitHub (https://github.com/EvolutionAPI/evolution-api) — MEDIUM confidence on v2.x API design; verify current release tag before deploying
- Ollama documentation (https://ollama.com/library) — MEDIUM confidence on model sizes and RAM requirements
- Docker Hub tags: n8nio/n8n, atendai/evolution-api, ollama/ollama — verify latest stable tags at deploy time
- Note: No live web search was available during this research session. All version numbers should be verified against official sources before production pinning.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
