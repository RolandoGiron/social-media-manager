# Roadmap: AI Social Media Manager & CRM

## Overview

From a blank VPS to a clinic admin sending a promotion that simultaneously hits WhatsApp and social media — without touching any system manually. The build order follows hard dependencies: infrastructure first, WhatsApp connectivity second, patient data third, AI chatbot and booking fourth, outbound campaigns fifth, social publishing sixth, and automation polish last. Phase 6 delivers the core differentiator (one action, both channels) only after both blast and social publishing are independently validated.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Infrastructure Foundation** - Docker Compose stack, database schema, security baseline, and Meta App Review submission
- [ ] **Phase 2: WhatsApp Core** - Evolution API connected, session health monitoring, and send/receive validated end-to-end
- [ ] **Phase 3: CRM Core** - Patient import, segmentation, message templates, and admin UI for patient management
- [ ] **Phase 4: AI Chatbot + Appointment Booking** - FAQ chatbot with RAG, human escalation, conversation inbox, and Google Calendar booking
- [ ] **Phase 5: Campaign Blast** - WhatsApp broadcast to segments with rate limiting, confirmation flow, and cancellation
- [ ] **Phase 6: Social Media Publishing** - Instagram and Facebook scheduling plus the unified campaign trigger (one action, both channels)
- [ ] **Phase 7: Automation Layer + Dashboard** - Appointment reminders, campaign delivery analytics, and admin metrics dashboard

## Phase Details

### Phase 1: Infrastructure Foundation
**Goal**: The full service stack runs on the VPS, the database schema is ready for all future data, and the Meta App Review is submitted
**Depends on**: Nothing (first phase)
**Requirements**: None (scaffolding phase — enables all subsequent requirements)
**Success Criteria** (what must be TRUE):
  1. All containers start cleanly with `docker compose up -d` and pass health checks
  2. n8n UI is accessible via HTTPS through Caddy with no services exposed directly on non-standard ports
  3. PostgreSQL database is reachable from n8n and contains all required tables (patients, conversations, appointments, campaign_log, workflow_errors)
  4. Meta App Review request is submitted and confirmation email received
**Plans:** 2 plans

Plans:
- [x] 01-01-PLAN.md — Docker Compose stack, PostgreSQL schema, Caddy reverse proxy, operational scripts
- [x] 01-02-PLAN.md — Meta App Review submission guide and human checkpoint

### Phase 2: WhatsApp Core
**Goal**: The clinic's WhatsApp number is connected and the system automatically alerts on disconnection
**Depends on**: Phase 1
**Requirements**: INFRA-01, INFRA-02, INFRA-03
**Success Criteria** (what must be TRUE):
  1. Admin can scan QR from the UI and the WhatsApp session shows as connected
  2. Session status (connected/disconnected) is visible on every page of the admin UI
  3. When the WhatsApp session drops, the admin receives an alert within 5 minutes without manual checking
  4. A message sent via n8n test workflow is received on the clinic's WhatsApp number and vice versa
**Plans:** 2/3 plans executed

Plans:
- [x] 02-01-PLAN.md — Evolution API client, env vars, test scaffolds
- [x] 02-02-PLAN.md — Streamlit multipage UI with sidebar status and QR page
- [x] 02-03-PLAN.md — n8n workflows for disconnect alert and message stub
**UI hint**: yes

### Phase 3: CRM Core
**Goal**: The admin can import, search, tag, and segment patients, and create message templates ready for campaigns
**Depends on**: Phase 2
**Requirements**: CRM-01, CRM-02, CRM-03, WA-01
**Success Criteria** (what must be TRUE):
  1. Admin can upload a CSV/Excel file with 100+ patient rows and see them imported with phone numbers normalized to +52 MX format and duplicates flagged
  2. Admin can search patients by name or phone number and filter by tag/segment from the patient list
  3. Admin can create a custom tag (e.g., "acne"), assign it to patients, and filter by that tag to see only matching patients
  4. Admin can create a message template with `{{nombre}}` and `{{fecha}}` variables and preview the rendered output before saving
**Plans:** 3 plans

Plans:
- [x] 03-01-PLAN.md — Database helper module, pure business logic (phone normalization, CSV parsing, template variables), and test suite
- [ ] 03-02-PLAN.md — Pacientes page: patient import, list, search, filter, pagination, and tag management
- [ ] 03-03-PLAN.md — Plantillas page: template editor with live preview, navigation wiring, and visual checkpoint
**UI hint**: yes

### Phase 4: AI Chatbot + Appointment Booking
**Goal**: Patients receive automatic FAQ answers on WhatsApp, the chatbot books appointments in Google Calendar, and the admin can monitor and respond to all conversations
**Depends on**: Phase 3
**Requirements**: BOT-01, BOT-02, BOT-03, BOT-04, CAL-01, CAL-02
**Success Criteria** (what must be TRUE):
  1. Patient sends a question about clinic hours, location, or pricing and receives an accurate answer from the knowledge base within 10 seconds, with a typing indicator while the LLM processes
  2. Patient asks a question the bot cannot answer or sends a medical complaint, and the chatbot sends a handoff message and flags the conversation for human response
  3. Patient requests an appointment, the chatbot checks Google Calendar availability, and books the appointment without human intervention — patient receives a WhatsApp confirmation with date, time, and clinic details
  4. Admin can view the full conversation history (bot and patient messages) and send a manual reply from the inbox UI
**Plans**: TBD
**UI hint**: yes

### Phase 5: Campaign Blast
**Goal**: The admin can send a WhatsApp broadcast to a patient segment safely, with rate limiting that prevents number banning and a confirmation gate before any mass send
**Depends on**: Phase 3
**Requirements**: WA-02, WA-03, WA-04
**Success Criteria** (what must be TRUE):
  1. Admin selects a patient segment and initiates a broadcast — a confirmation screen shows the exact recipient count ("Estas a punto de enviar a N pacientes. Confirmar?") before any message is sent
  2. A broadcast of 50+ messages is delivered with automatic delays between sends (3-8 seconds with jitter) and no messages are sent in bulk without pausing
  3. Admin can cancel a broadcast in progress and remaining messages are not sent
**Plans**: TBD
**UI hint**: yes

### Phase 6: Social Media Publishing
**Goal**: The admin can schedule posts on Instagram and Facebook and launch a single action that simultaneously sends a WhatsApp broadcast and publishes on social media
**Depends on**: Phase 5
**Requirements**: SOCIAL-01, SOCIAL-02, SOCIAL-03
**Success Criteria** (what must be TRUE):
  1. Admin can compose a post with an image and caption, select a scheduled date/time, and see it appear in a list of scheduled posts with status (pendiente/publicado/error)
  2. A scheduled post publishes automatically to Instagram and Facebook at the specified time without manual action
  3. Admin triggers the unified campaign action once and both the WhatsApp broadcast to the selected segment and the social post publish — both complete from a single click
**Plans**: TBD
**UI hint**: yes

### Phase 7: Automation Layer + Dashboard
**Goal**: Appointment reminders run automatically, the admin has a metrics dashboard showing system health and campaign performance, and campaign delivery analytics are visible per segment
**Depends on**: Phase 6
**Requirements**: CAL-03, DASH-01, DASH-02, DASH-03
**Success Criteria** (what must be TRUE):
  1. Patient with a booked appointment receives a WhatsApp reminder automatically 24 hours before and again 1 hour before, without admin action
  2. Admin can view a dashboard with current totals: messages sent, bot resolution percentage, appointments booked, and posts published
  3. Admin can see per-segment delivery metrics for a campaign: how many patients in segment X received and read the message
  4. Admin can view the n8n workflow error log from the admin UI to diagnose operational issues without accessing n8n directly
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Infrastructure Foundation | 0/2 | Planning complete | - |
| 2. WhatsApp Core | 2/3 | In Progress|  |
| 3. CRM Core | 0/3 | Planning complete | - |
| 4. AI Chatbot + Appointment Booking | 0/? | Not started | - |
| 5. Campaign Blast | 0/? | Not started | - |
| 6. Social Media Publishing | 0/? | Not started | - |
| 7. Automation Layer + Dashboard | 0/? | Not started | - |
