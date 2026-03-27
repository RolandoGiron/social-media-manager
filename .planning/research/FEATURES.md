# Feature Research

**Domain:** AI Social Media Manager + WhatsApp CRM for dermatology clinics (small business)
**Researched:** 2026-03-27
**Confidence:** MEDIUM (training data through Aug 2025; web research unavailable in this session — findings based on known competitors: WATI, Respond.io, Trengo, Callbell, ManyChat, Metricool, Buffer, Later, Hootsuite)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete or unusable for a clinic admin.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| CSV/Excel patient import | Every clinic has a spreadsheet; no import = manual re-entry | LOW | Parse name, phone, condition/interest columns; normalize phone format (MX +52) |
| Contact list view with search/filter | Core CRM expectation; can't operate without seeing who you have | LOW | Paginated table; filter by tag/segment; show last contacted date |
| Patient tagging / segmentation | Required to send targeted campaigns vs broadcast spam | LOW-MEDIUM | Tag by condition (acne, rosácea, etc.), visit status, consent; stored in PostgreSQL |
| WhatsApp message send (single contact) | Basic chat capability; precondition for mass send | MEDIUM | Via Evolution API; requires active WA session management |
| WhatsApp broadcast / mass send to segment | Core value delivery — without this there's no marketing automation | MEDIUM | Must respect WA rate limits to avoid ban; queue with delay between sends |
| Message template management | WhatsApp requires templates for outbound marketing messages | MEDIUM | Store templates with variables ({{name}}, {{date}}); preview before send |
| Chatbot auto-reply (FAQ) | Clinics receive same questions 50+ times/day; staff time savings | HIGH | n8n flow + LLM; handle: hours, location, pricing, services |
| Human handoff / escalation | Without this, bot blocks real inquiries and frustrates patients | MEDIUM | Keyword or confidence-threshold trigger; assign conversation to staff inbox |
| Conversation inbox (human view) | Staff must see and respond to escalated chats | MEDIUM | Per-contact thread view; show bot history; reply from web UI |
| Google Calendar appointment booking via chatbot | Stated as MVP success criterion; zero manual intervention | HIGH | Check availability via Calendar API; create event; send confirmation on WA |
| Social post scheduling (Instagram + Facebook) | Any social media tool must schedule; posting manually defeats the purpose | MEDIUM | Meta Graph API; schedule datetime; attach image/caption |
| Admin dashboard with key metrics | Clinic owner needs to see if system is working | LOW-MEDIUM | Show: messages sent, bot resolution rate, appointments booked, posts published |
| Active WhatsApp session status indicator | Evolution API sessions can disconnect; must surface this visibly | LOW | Show connected/disconnected; alert when session needs QR scan |

### Differentiators (Competitive Advantage)

Features that set this product apart from generic WhatsApp tools or generic social schedulers. Align with the Core Value: "launch a promotion that reaches WhatsApp + social media simultaneously, without touching any system manually."

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Unified campaign: social post + WhatsApp blast from single action | No competitor in the SMB clinic space links these two channels atomically | HIGH | Single form: write copy, pick segment, schedule → n8n fans out to both channels |
| AI-generated copy + image for promotions | Clinic admins are not copywriters; reduces barrier to launching campaigns | HIGH | GPT/Claude for copy; DALL-E or Stable Diffusion for image; clinic can edit before send |
| Dermatology-specific chatbot intents out of the box | Generic chatbots require configuration; specialty pre-training accelerates onboarding | MEDIUM | Pre-load FAQ patterns: "¿cuánto cuesta una limpieza facial?", "¿aceptan seguros?" |
| Appointment reminder automation (24h + 1h before) | Reduces no-shows — high pain point for dermatology clinics | MEDIUM | n8n scheduled trigger; query upcoming Calendar events; send WA reminder |
| Post-appointment follow-up message | Drives reviews and repeat visits; no tool in the SMB space does this automatically | MEDIUM | Trigger N hours after appointment end time; ask for Google review or return booking |
| Campaign performance by segment | Know which patient segment responded; most SMB tools don't segment analytics | MEDIUM | Track WA message delivery/read per broadcast job; correlate with segment tags |
| Consent management (RGPD-lite) | Clinics handle health-adjacent data; having opt-in/opt-out tracking reduces liability | LOW-MEDIUM | Boolean consent flag per contact; auto-exclude opt-outs from broadcasts |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Full EMR / clinical history | "While we're at it, track treatments too" | Scope explosion; regulatory risk (NOM-024 Mexico); out of stated scope | Stay at contact + segmentation + appointment link only |
| In-app payment collection | "Patients could pay the deposit via WhatsApp" | Requires PSP integration, PCI compliance surface, tax handling; massive v1 scope risk | Defer to v2; link to external payment URL in WA message if needed |
| Multi-clinic / multi-tenant admin | "My cousin also has a clinic" | Rewrites data isolation, billing, auth layers; contradicts single-tenant MVP decision | Architecture designed for it, but UI/data isolation deferred to v2 |
| Real-time WhatsApp inbox with websocket push | "I want it to update instantly like WhatsApp Web" | Requires persistent socket connections; adds infra complexity on constrained VPS | Polling every 5-10s is sufficient for a clinic's volume; perceived real-time |
| Mobile app (iOS/Android) | "I manage everything from my phone" | Doubles UI surface; slows v1 delivery significantly | Progressive Web App (PWA) approach or responsive web; add native app in v2 |
| Deep analytics / BI dashboards | "I want a Metabase-style analytics view" | Complex aggregation queries; charting library weight; low v1 ROI | Simple counters + last-7-days summaries satisfy MVP; embed Metabase in v2 if needed |
| Automated TikTok posting | "We should be on TikTok" | TikTok's API for business posting requires approval; video-first format doesn't fit still-image promotion workflow | Manual TikTok; focus automation on Instagram + Facebook where Meta API is stable |
| AI chatbot that handles complaints / refunds | "Let the bot handle everything" | LLM hallucinations in medical-adjacent context are liability; patients expect human empathy for problems | Hard-code escalation for complaint keywords; bot only handles informational queries |

---

## Feature Dependencies

```
[Patient Import (CSV)]
    └──requires──> [Contact Storage (PostgreSQL)]
                       └──required by──> [Segmentation / Tagging]
                                              └──required by──> [WhatsApp Broadcast]
                                              └──required by──> [Campaign Analytics by Segment]

[WhatsApp Session (Evolution API)]
    └──required by──> [WA Single Send]
                          └──required by──> [WA Broadcast]
                          └──required by──> [Chatbot Auto-Reply]
                                                └──required by──> [Appointment Booking via Bot]
                                                └──required by──> [Human Handoff]
                                                └──required by──> [Appointment Reminders]

[Google Calendar API auth]
    └──required by──> [Appointment Booking via Bot]
    └──required by──> [Appointment Reminders]

[Social Post Scheduling (Meta Graph API)]
    └──required by──> [Unified Campaign (WA + Social)]
    └──enhanced by──> [AI Copy + Image Generation]

[Message Template Management]
    └──required by──> [WA Broadcast]
    └──enhances──> [AI Copy Generation]

[Human Handoff]
    └──required by──> [Conversation Inbox]

[Consent Management]
    └──enhances──> [WA Broadcast] (filters opt-outs)
```

### Dependency Notes

- **WA Broadcast requires Segmentation:** Without segments, broadcast is an undifferentiated blast — high unsubscribe/ban risk on Evolution API.
- **Appointment Booking requires both WA Session AND Google Calendar auth:** These are independent integrations that must both be working before the booking flow can be tested end-to-end.
- **Unified Campaign requires Social Scheduling:** You cannot fan out to both channels until the social posting path is independently functional.
- **Human Handoff requires Conversation Inbox:** Handing off to a human who has no interface to respond is worse than no handoff.
- **AI Copy Generation enhances but does not block Unified Campaign:** The campaign flow works without AI copy; AI is an enhancement layer.

---

## MVP Definition

### Launch With (v1)

Minimum viable to hit the four stated MVP success criteria from PROJECT.md.

- [ ] Patient import from CSV — validates 100 patients migrated
- [ ] Contact list with tags/segments — precondition for targeted broadcast
- [ ] WhatsApp session management (Evolution API connect/reconnect) — infrastructure prerequisite
- [ ] Message template creation and preview — required before any WA send
- [ ] WhatsApp broadcast to segment — validates "promotion reaches WhatsApp of relevant patients"
- [ ] Chatbot FAQ auto-reply (location, hours, prices, services) — validates 80% FAQ resolution
- [ ] Human handoff / escalation with conversation inbox — required for safe chatbot deployment
- [ ] Google Calendar availability check + appointment booking via bot — validates "one appointment booked without human intervention"
- [ ] Instagram + Facebook post scheduling — validates "promotion published on IG"
- [ ] Unified campaign trigger (one action → WA broadcast + social post) — validates the Core Value
- [ ] Admin dashboard: sent count, bot resolution %, appointments booked, posts published — validates observability

### Add After Validation (v1.x)

Features to add once core flow is proven working with the first clinic.

- [ ] Appointment reminders (24h + 1h) — high ROI, low complexity relative to booking; add once booking works
- [ ] Post-appointment follow-up message — add after reminders are stable
- [ ] AI-generated copy + image for campaigns — add once manual campaign flow is validated
- [ ] Campaign delivery analytics by segment — add after first 2-3 campaigns run
- [ ] Consent / opt-out management — add before scaling to more patients or more clinics

### Future Consideration (v2+)

- [ ] Multi-tenant / multi-clinic support — requires data isolation rewrite; defer until product-market fit
- [ ] Mobile PWA — defer until admin web UI is stable and validated
- [ ] Deeper analytics / Metabase integration — defer until clinic owner asks for it
- [ ] X (Twitter) and TikTok posting — defer; API complexity and content format mismatch
- [ ] AI chatbot for scheduling edge cases (reschedule, cancel) — complex state machine; build after happy path is solid

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Patient CSV import | HIGH | LOW | P1 |
| Contact list + segmentation | HIGH | LOW | P1 |
| WA session management | HIGH | MEDIUM | P1 |
| Message templates | HIGH | LOW | P1 |
| WA broadcast to segment | HIGH | MEDIUM | P1 |
| Chatbot FAQ auto-reply | HIGH | HIGH | P1 |
| Human handoff + inbox | HIGH | MEDIUM | P1 |
| Appointment booking via bot | HIGH | HIGH | P1 |
| Instagram + Facebook scheduling | HIGH | MEDIUM | P1 |
| Unified campaign (WA + social) | HIGH | MEDIUM | P1 |
| Admin metrics dashboard | MEDIUM | LOW | P1 |
| Appointment reminders | HIGH | LOW | P2 |
| Post-appointment follow-up | MEDIUM | LOW | P2 |
| AI copy + image generation | MEDIUM | HIGH | P2 |
| Campaign analytics by segment | MEDIUM | MEDIUM | P2 |
| Consent / opt-out management | MEDIUM | LOW | P2 |
| X/TikTok posting | LOW | HIGH | P3 |
| Mobile PWA | MEDIUM | HIGH | P3 |
| Multi-tenant support | LOW (v1) | HIGH | P3 |
| Full BI analytics | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

Competitors analyzed from training data: WATI, Respond.io, Callbell, ManyChat (WhatsApp); Buffer, Later, Metricool (social scheduling); no competitor combines both in a single SMB-focused product.

| Feature | WATI / Respond.io | Buffer / Metricool | Our Approach |
|---------|-------------------|--------------------|--------------|
| WhatsApp broadcast | Yes (Meta BSP required) | No | Yes, via Evolution API (unofficial, zero cost) |
| Chatbot builder | Visual flow builder | No | n8n flow builder + LLM; no visual UI in v1 |
| Appointment booking | Not native; Calendly webhook integrations | No | Native Google Calendar integration via chatbot |
| Social scheduling | No | Yes (FB, IG, TikTok, X) | Yes (FB + IG only in v1) |
| Unified WA + social campaign | No | No | Yes — core differentiator |
| AI content generation | Partial (WATI AI beta) | Partial (Buffer AI beta) | Yes (v1.x) |
| Contact segmentation | Basic tags | No | Yes — dermatology-specific tags |
| Multi-channel inbox | Yes (Respond.io strength) | No | Basic inbox for escalated chats only |
| Appointment reminders | No (requires Zapier) | No | Yes (v1.x, n8n scheduled) |
| Self-hosted / data ownership | No (all SaaS) | No (all SaaS) | Yes — VPS, PostgreSQL, full data ownership |
| Price for SMB | $40-$100+/mo | $15-$40/mo | Cost of VPS (~$10-20/mo) + API costs |

---

## Sources

- WATI.io feature documentation (training data, verified through mid-2025)
- Respond.io platform documentation (training data)
- Callbell.eu feature list (training data)
- ManyChat WhatsApp capabilities (training data)
- Buffer and Metricool social scheduling feature sets (training data)
- Evolution API documentation patterns (training data + PROJECT.md context)
- Meta Graph API for Instagram/Facebook publishing (training data)
- Google Calendar API capabilities (training data)
- PROJECT.md requirements and constraints (read directly)

**Confidence note:** Web research tools were unavailable in this session. All competitor analysis is from training data (knowledge cutoff Aug 2025). Confidence is MEDIUM: the feature landscape in this space is well-established and unlikely to have changed fundamentally, but specific competitor features may have evolved. Recommend spot-checking WATI and Respond.io current pricing/features before roadmap finalization.

---
*Feature research for: AI Social Media Manager + WhatsApp CRM for dermatology clinics*
*Researched: 2026-03-27*
