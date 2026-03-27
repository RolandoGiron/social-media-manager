# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-27)

**Core value:** El dueño de la clínica puede lanzar una promoción dirigida — que llega a WhatsApp de los pacientes relevantes Y se publica en redes sociales — sin tocar ningún sistema manualmente.
**Current focus:** Phase 1 — Infrastructure Foundation

## Current Position

Phase: 1 of 7 (Infrastructure Foundation)
Plan: 0 of ? in current phase
Status: Ready to plan
Last activity: 2026-03-27 — Roadmap created, project initialized

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Init]: Evolution API over Meta Business API — zero per-message cost, no approval friction
- [Init]: n8n as orchestrator — low-code flows, reduces custom code, integrates natively with all APIs
- [Init]: OpenAI gpt-4o-mini as default LLM (Ollama optional if VPS has 8+ GB RAM confirmed in Phase 4)
- [Init]: Single-tenant v1 — reduces MVP complexity; multi-tenant deferred to v2

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 6 dependency]: Meta App Review must be submitted in Phase 1 — review takes 2-6 weeks. Delay here blocks social publishing. Have Buffer/Make fallback ready.
- [Phase 4 dependency]: Google Calendar Service Account setup should be tested before Phase 4 to avoid blocking appointment booking implementation.
- [Phase 2]: Evolution API v2 webhook payload schema should be verified against current GitHub docs before building chatbot workflow (field names may have changed).

## Session Continuity

Last session: 2026-03-27
Stopped at: Roadmap and State initialized. Ready to plan Phase 1.
Resume file: None
