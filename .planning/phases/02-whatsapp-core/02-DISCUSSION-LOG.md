# Phase 2: WhatsApp Core - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-03-28
**Phase:** 02-whatsapp-core
**Mode:** discuss
**Areas analyzed:** QR scanning UX, Session status display, Disconnection alert channel, n8n workflow structure

## Assumptions Presented

### QR Scanning UX
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Iframe embed of Evolution API manager is lowest-effort and most reliable | Confident | docker-compose.yml: Evolution API has SERVER_URL and exposes manager UI |

### Session Status Display
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Streamlit sidebar is the right place for persistent status | Confident | admin-ui/src/app.py uses layout="wide" with sidebar; polling every 60s is sufficient for single-admin |

### Disconnection Alert
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| WhatsApp-to-admin is most effective given admin's phone is always available | Likely | No SMTP or Telegram config in .env.example; WhatsApp most direct for clinic admin |

### n8n Workflow Structure
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Separate workflows per event type is more maintainable | Confident | Evolution API sends multiple event types; separate workflows allow independent enable/disable |

## Corrections Made

No corrections — all assumptions confirmed by user.

## Gray Areas Selected

User selected all 4 gray areas for discussion:
1. QR scanning UX → iframe embed
2. Session status display → sidebar badge, poll every 60s
3. Disconnection alert → WhatsApp message to admin's personal number
4. n8n workflow structure → separate workflows per event type
