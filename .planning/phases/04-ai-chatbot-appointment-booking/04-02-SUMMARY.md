---
phase: 04-ai-chatbot-appointment-booking
plan: "02"
subsystem: admin-ui
tags: [streamlit, inbox, knowledge-base, chatbot, whatsapp, faq]
dependency_graph:
  requires: ["04-01"]
  provides: ["Inbox page for conversation monitoring and manual reply", "Knowledge Base page for FAQ management"]
  affects: ["admin-ui navigation", "chatbot human escalation flow"]
tech_stack:
  added: []
  patterns:
    - "split-pane Streamlit layout with st.columns([1, 2])"
    - "streamlit-autorefresh for 10s inbox polling (with ImportError fallback)"
    - "inline edit forms with st.form inside loop using unique keys"
    - "session_state for cross-rerun selection persistence"
key_files:
  created:
    - admin-ui/src/pages/5_Inbox.py
    - admin-ui/src/pages/6_Knowledge_Base.py
  modified:
    - admin-ui/src/app.py
decisions:
  - "Auto-refresh handled via streamlit-autorefresh with ImportError fallback to avoid hard dependency"
  - "Knowledge Base items grouped by categoria to improve scannability"
  - "Inline edit forms use unique form keys per item_id to avoid Streamlit key collisions"
metrics:
  duration: "~2 min"
  completed_date: "2026-04-08"
  tasks_completed: 1
  tasks_total: 2
  files_modified: 3
---

# Phase 4 Plan 2: Inbox and Knowledge Base Pages Summary

Inbox page (5_Inbox.py) for conversation monitoring and manual WhatsApp reply, plus Knowledge Base page (6_Knowledge_Base.py) for FAQ management, wired into app.py navigation under a new "Chatbot" section.

## What Was Built

**5_Inbox.py** — Full conversation inbox with:
- Split-pane layout: narrow conversation list (left) + wide chat view (right)
- Status badges: BOT / HUMANO / CERRADA based on conversation state
- `[!]` prefix for human_handoff conversations (sorted first by DB query)
- Full chat history using `st.chat_message` with user/assistant roles
- Manual reply via `st.chat_input` that calls `EvolutionAPIClient.send_text_message` and inserts agent message record
- "Cerrar conversacion" button that calls `update_conversation_state` and clears selection
- Auto-refresh every 10 seconds via `streamlit_autorefresh` (interval=10000) with `ImportError` fallback
- Session state persistence of `selected_conversation_id` across auto-refreshes

**6_Knowledge_Base.py** — Full FAQ management with:
- "Agregar nuevo FAQ" expander with form for pregunta, respuesta, categoria (selectbox), is_active
- FAQ items displayed grouped by categoria with active status icon
- Toggle active/inactive per item
- Inline edit form (pre-filled with current values) triggered by Edit button
- Delete with two-step confirmation (click Delete, then confirm)
- `fetch_knowledge_base(active_only=False)` to show all items including inactive

**app.py** — Added 2 page declarations (`5_Inbox.py`, `6_Knowledge_Base.py`) and new "Chatbot" navigation section.

## Tasks

| # | Name | Status | Commit |
|---|------|--------|--------|
| 1 | Inbox page + Knowledge Base page + navigation wiring | Done | b3441e9 |
| 2 | Visual verification of Inbox and Knowledge Base pages | Awaiting human verify | — |

## Deviations from Plan

None — plan executed exactly as written. The `streamlit_autorefresh` ImportError fallback was added as Rule 2 (missing error handling) to prevent hard import failure if the package is not installed.

## Known Stubs

None — all functionality is wired to real database functions and Evolution API client from Plan 01.

## Self-Check: PASSED

Files exist:
- admin-ui/src/pages/5_Inbox.py: FOUND
- admin-ui/src/pages/6_Knowledge_Base.py: FOUND
- admin-ui/src/app.py: FOUND (modified)

Commits:
- b3441e9: feat(04-02): add Inbox and Knowledge Base pages with navigation wiring — FOUND
