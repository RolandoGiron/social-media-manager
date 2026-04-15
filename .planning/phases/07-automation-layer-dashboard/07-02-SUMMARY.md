---
phase: 07-automation-layer-dashboard
plan: "02"
subsystem: ui
tags: [streamlit, postgresql, dashboard, metrics]

requires:
  - phase: 06-appointment-booking
    provides: appointments table with confirmed status
  - phase: 05-campaign-blast
    provides: messages, campaign_log, campaign_recipients, social_posts tables
  - phase: 04-whatsapp-chatbot
    provides: conversations table with human_handoff column
provides:
  - fetch_dashboard_kpis() — 4 KPI values (messages sent, bot resolution %, appointments booked, posts published) for last N days
  - fetch_activity_chart_data() — daily messages+appointments series for last N days with generate_series gaps filled
  - fetch_workflow_errors() — last N workflow_errors rows for error log
  - 1_Dashboard.py — full operational dashboard with KPI cards, activity chart, error log table
affects: [admin-ui, dashboard, 07-03]

tech-stack:
  added: []
  patterns: [streamlit-metric-cards, pandas-line-chart, try-except-graceful-display]

key-files:
  created: []
  modified:
    - admin-ui/src/components/database.py
    - admin-ui/src/pages/1_Dashboard.py

key-decisions:
  - "KPIs use last 30 days hardcoded (no period selector in v1 — D-08)"
  - "Activity chart uses st.line_chart with pandas DataFrame — simplest option (D-09)"
  - "Error log is read-only, no mark-as-resolved (D-11)"
  - "bot_resolution_pct guards division by zero when total_convs == 0"

patterns-established:
  - "Dashboard pattern: try/except around each DB call, fallback to zero-value dict"
  - "Relative time display: secs → mins → hours → days helper function"

requirements-completed: [DASH-01, DASH-03]

duration: 15min
completed: 2026-04-15
---

# Plan 07-02: Dashboard DB Helpers + 1_Dashboard.py

**Replaced the 4-line dashboard stub with a full operational dashboard — 4 KPI cards, 7-day activity chart, and workflow error log.**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-04-15
- **Tasks:** 7/7
- **Files modified:** 2

## Accomplishments

- Added `fetch_dashboard_kpis(days=30)` to `database.py` — counts outbound messages, calculates bot resolution %, confirmed appointments, and published posts; all with zero-division guard
- Added `fetch_activity_chart_data(days=7)` — uses `generate_series` to ensure all 7 days appear even with no activity (LEFT JOIN)
- Added `fetch_workflow_errors(limit=20)` — returns most recent errors ordered by `created_at DESC`
- Replaced 1-line `1_Dashboard.py` stub with 139-line full implementation:
  - `st.columns(4)` row of KPI cards with `help=` tooltips
  - `st.line_chart` with renamed series ("Mensajes enviados", "Citas agendadas")
  - `st.dataframe` error log with relative-time "Hace" column (truncated at 80 chars)
  - All DB calls wrapped in `try/except` with graceful error display

## Self-Check: PASSED

- [x] `fetch_dashboard_kpis` returns 4-key dict
- [x] `fetch_activity_chart_data` returns list with `date`, `messages_sent`, `appointments`
- [x] `fetch_workflow_errors` returns list with `workflow_name`, `node_name`, `error_message`, `created_at`
- [x] `1_Dashboard.py` replaced (139 lines)
- [x] `render_sidebar()` called at top
- [x] 4 KPI cards in `st.columns(4)`
- [x] Activity chart uses `st.line_chart`
- [x] Error log uses `st.dataframe` (read-only)
- [x] Division-by-zero guard in bot_resolution_pct
