"""1_Dashboard.py — Operational metrics dashboard (DASH-01, DASH-03).

Displays:
  - 4 KPI cards (last 30 days)
  - Activity chart: messages sent + appointments per day (last 7 days)
  - Workflow error log (last 20 errors)
"""
import pandas as pd
import streamlit as st

from components.database import (
    fetch_activity_chart_data,
    fetch_dashboard_kpis,
    fetch_workflow_errors,
)
from components.sidebar import render_sidebar

render_sidebar()

st.title("Dashboard")

# ─────────────────────────────────────────────────────────────────────────────
# KPI Cards  (DASH-01, D-07)
# ─────────────────────────────────────────────────────────────────────────────
try:
    kpis = fetch_dashboard_kpis(days=30)
except Exception as exc:
    st.error(f"Error cargando métricas: {exc}")
    kpis = {
        "messages_sent": 0,
        "bot_resolution_pct": 0.0,
        "appointments_booked": 0,
        "posts_published": 0,
    }

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Mensajes enviados",
        value=f"{kpis['messages_sent']:,}",
        help="Mensajes salientes en los últimos 30 días",
    )

with col2:
    st.metric(
        label="Resolución del bot",
        value=f"{kpis['bot_resolution_pct']:.1f}%",
        help="Conversaciones resueltas por el bot sin handoff humano (últimos 30 días)",
    )

with col3:
    st.metric(
        label="Citas agendadas",
        value=f"{kpis['appointments_booked']:,}",
        help="Citas confirmadas creadas en los últimos 30 días",
    )

with col4:
    st.metric(
        label="Posts publicados",
        value=f"{kpis['posts_published']:,}",
        help="Posts en redes sociales publicados en los últimos 30 días",
    )

st.caption("Período: últimos 30 días")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# Activity Chart  (DASH-01, D-09)
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("Actividad — últimos 7 días")

try:
    chart_rows = fetch_activity_chart_data(days=7)
except Exception as exc:
    chart_rows = []
    st.error(f"Error cargando datos de actividad: {exc}")

if chart_rows:
    df_chart = pd.DataFrame(chart_rows)
    df_chart["date"] = pd.to_datetime(df_chart["date"])
    df_chart = df_chart.set_index("date")
    df_chart = df_chart.rename(columns={
        "messages_sent": "Mensajes enviados",
        "appointments": "Citas agendadas",
    })
    st.line_chart(df_chart)
else:
    st.info("Sin datos de actividad en los últimos 7 días.")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# Workflow Error Log  (DASH-03, D-10, D-11)
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("Errores de workflows (últimos 20)")

try:
    errors = fetch_workflow_errors(limit=20)
except Exception as exc:
    errors = []
    st.error(f"Error cargando log de errores: {exc}")

if not errors:
    st.success("Sin errores recientes en workflows.")
else:
    from datetime import datetime, timezone

    now_utc = datetime.now(timezone.utc)

    def _relative_time(dt) -> str:
        if dt is None:
            return "—"
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = now_utc - dt
        secs = int(delta.total_seconds())
        if secs < 60:
            return f"hace {secs}s"
        if secs < 3600:
            return f"hace {secs // 60}m"
        if secs < 86400:
            return f"hace {secs // 3600}h"
        return f"hace {secs // 86400}d"

    rows = [
        {
            "Workflow": e["workflow_name"] or "—",
            "Nodo": e["node_name"] or "—",
            "Error": (e["error_message"] or "")[:80] + ("…" if len(e["error_message"] or "") > 80 else ""),
            "Hace": _relative_time(e["created_at"]),
        }
        for e in errors
    ]
    df_err = pd.DataFrame(rows)
    st.dataframe(df_err, use_container_width=True, hide_index=True)
    st.caption(f"{len(errors)} error(es) mostrado(s) — solo lectura")
