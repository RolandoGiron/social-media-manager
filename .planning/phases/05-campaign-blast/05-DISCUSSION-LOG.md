# Phase 5: Campaign Blast - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-12
**Phase:** 05-campaign-blast
**Mode:** discuss
**Areas discussed:** UI Location, Progress UX

## Gray Areas Presented

### UI Location
| Option | Description |
|--------|-------------|
| Nueva página 'Campañas' (selected) | New sidebar page 7_Campañas.py — dedicated broadcast workflow |
| Desde página Pacientes | Launch from patient list after filtering by tag |

### Progress UX
| Option | Description |
|--------|-------------|
| Progreso en tiempo real (selected) | Auto-refreshing progress bar with live sent/total count and cancel button |
| Historial de campañas | Campaign history table with status; admin checks back |

## Decisions Made

### UI Location
- **User chose:** Nueva página 'Campañas' (Recommended)
- Dedicated `7_Campañas.py` sidebar page for full campaign workflow

### Progress UX
- **User chose:** Progreso en tiempo real (Recommended)
- Auto-refresh every 5s polling `campaign_log`, progress bar with cancel button

## Pre-decided (No User Input Needed)

The following were decided from codebase analysis and prior context — not presented to user:

- DB schema: `campaign_log` + `campaign_recipients` already exist — no migration
- n8n handles rate-limited sends (3-8s jitter loop), Streamlit triggers via webhook
- Cancellation: DB flag `status='cancelled'` checked by n8n before each send iteration
- Campaign naming: auto-generated from tag + date (Claude's discretion)
- Template rendering: reuse `extract_variables()` / `render_preview()` from templates component
- Evolution API send: reuse `sub-send-wa-message.json` pattern
