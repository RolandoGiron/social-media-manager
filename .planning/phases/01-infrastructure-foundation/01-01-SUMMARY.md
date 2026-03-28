---
phase: 01-infrastructure-foundation
plan: 01
subsystem: infra
tags: [docker-compose, postgresql, redis, caddy, n8n, evolution-api, streamlit]

# Dependency graph
requires: []
provides:
  - "Docker Compose stack with 6 services (postgres, redis, n8n, evolution-api, streamlit, caddy)"
  - "PostgreSQL schema with 11 tables covering patients, conversations, appointments, campaigns, social posts"
  - "Caddy reverse proxy with HTTPS and basicauth for admin UI"
  - "Operational scripts for backup and deployment"
affects: [02-whatsapp-core, 03-chatbot-ai, 04-calendar-booking, 05-campaigns, 06-social-publishing, 07-admin-ui]

# Tech tracking
tech-stack:
  added: [postgres:16-alpine, redis:7-alpine, n8nio/n8n:latest, atendai/evolution-api:v2.2.3, caddy:2-alpine, python:3.11-slim, streamlit]
  patterns: [docker-internal-networking, caddy-reverse-proxy, healthcheck-on-all-services, uuid-primary-keys, timestamptz-timestamps, updated_at-triggers]

key-files:
  created:
    - docker-compose.yml
    - docker-compose.override.yml
    - .env.example
    - caddy/Caddyfile
    - postgres/init/001_schema.sql
    - postgres/init/002_seed.sql
    - scripts/backup.sh
    - scripts/deploy.sh
    - admin-ui/Dockerfile
    - admin-ui/requirements.txt
    - admin-ui/src/app.py
  modified: []

key-decisions:
  - "Only Caddy exposes host ports (80/443); all services communicate over Docker internal network"
  - "PostgreSQL max_connections=50 per VPS memory optimization guidance"
  - "Redis maxmemory 64mb with allkeys-lru eviction policy"
  - "Evolution API pinned to v2.2.3 for stability"
  - "n8n concurrency capped at 8 to prevent VPS RAM exhaustion"

patterns-established:
  - "Docker internal networking: services reference each other by container service name"
  - "UUID primary keys via gen_random_uuid() on all tables"
  - "TIMESTAMPTZ for all timestamp columns"
  - "update_updated_at trigger function shared across tables"
  - "Conversation state machine with CHECK constraint enum"
  - "Partial unique index for active conversations per WhatsApp contact"

requirements-completed: []

# Metrics
duration: 2min
completed: 2026-03-28
---

# Phase 1 Plan 1: Docker Compose Infrastructure Summary

**Docker Compose stack with 6 services, PostgreSQL schema (11 tables with state machines, triggers, and GIN search), Caddy reverse proxy, and operational scripts**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-28T06:58:10Z
- **Completed:** 2026-03-28T07:00:57Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- Complete Docker Compose stack with postgres, redis, n8n, evolution-api, streamlit, and caddy -- all with healthchecks and restart policies
- PostgreSQL schema covering 11 tables: patients, tags, patient_tags, conversations, messages, appointments, message_templates, campaign_log, campaign_recipients, workflow_errors, social_posts
- Caddy reverse proxy routing 3 subdomains with basicauth on admin UI
- Backup script with pg_dump and 30-day retention, deploy script for stack updates

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Docker Compose stack, .env.example, and Caddyfile** - `414cee7` (feat)
2. **Task 2: Create PostgreSQL schema and operational scripts** - `80a5cc6` (feat)

## Files Created/Modified
- `docker-compose.yml` - Full 6-service stack definition with healthchecks and internal networking
- `docker-compose.override.yml` - Dev overrides exposing postgres and n8n ports
- `.env.example` - Environment variable template with all required secrets documented
- `caddy/Caddyfile` - Reverse proxy with 3 subdomain routes and basicauth
- `postgres/init/001_schema.sql` - 11-table schema with extensions, indexes, constraints, triggers
- `postgres/init/002_seed.sql` - Dermatology tags and message template seed data
- `scripts/backup.sh` - PostgreSQL backup with gzip compression and retention cleanup
- `scripts/deploy.sh` - Docker Compose pull and restart script
- `admin-ui/Dockerfile` - Python 3.11 Streamlit container with healthcheck
- `admin-ui/requirements.txt` - Streamlit and database dependencies
- `admin-ui/src/app.py` - Placeholder admin panel page

## Decisions Made
- Only Caddy exposes host ports (80/443) -- all inter-service communication over Docker internal bridge network (per ARCHITECTURE.md anti-pattern 5)
- PostgreSQL max_connections=50 and Redis maxmemory=64mb per VPS memory optimization in STACK.md
- Evolution API pinned to v2.2.3 (not :latest) for stability per PITFALLS.md guidance
- n8n concurrency capped at 8 to prevent RAM exhaustion during campaign webhook spikes (per PITFALLS.md pitfall 2)
- GIN trigram index on patient names for fast fuzzy search
- Partial unique index on conversations for one active conversation per WhatsApp contact

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs
- `admin-ui/src/app.py` - Placeholder page with info message only; will be built out in Phase 7 (admin UI)

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Docker Compose stack ready for `docker compose up -d` on VPS
- PostgreSQL schema ready for all subsequent phases (chatbot, campaigns, appointments, social)
- n8n, Evolution API, and Caddy configured for internal-only networking
- Blocker: VPS domain and DNS must be configured before Caddy can provision HTTPS certificates

## Self-Check: PASSED

- All 11 created files verified present on disk
- Commit 414cee7 (Task 1) verified in git log
- Commit 80a5cc6 (Task 2) verified in git log

---
*Phase: 01-infrastructure-foundation*
*Completed: 2026-03-28*
