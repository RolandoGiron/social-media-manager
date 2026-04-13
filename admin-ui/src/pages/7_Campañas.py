"""7_Campañas.py — Phase 5 broadcast launch + monitor (WA-02, WA-03, WA-04)."""
import os
from datetime import datetime

import requests
import streamlit as st

from components.database import (
    cancel_campaign,
    fetch_campaign_history,
    fetch_campaign_status,
    fetch_patients_by_tags,
    fetch_tags_with_counts,
    fetch_templates,
    insert_campaign,
    insert_campaign_recipients,
)
from components.sidebar import render_sidebar
from components.templates import render_preview

render_sidebar()

# ---------- Session state defaults ----------
st.session_state.setdefault("campanas_mode", "setup")
st.session_state.setdefault("campanas_selected_tag_ids", [])
st.session_state.setdefault("campanas_selected_template_id", None)
st.session_state.setdefault("campanas_active_campaign_id", None)
st.session_state.setdefault("campanas_recipient_count", 0)

SPANISH_MONTHS = {
    1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
    7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic",
}


def _format_date(dt: datetime) -> str:
    return f"{dt.day} {SPANISH_MONTHS[dt.month]} {dt.year}"


def _trigger_n8n_webhook(campaign_id: str) -> bool:
    base_url = os.environ.get("N8N_WEBHOOK_BASE_URL", "http://n8n:5678")
    url = f"{base_url}/webhook/campaign-blast"
    try:
        resp = requests.post(url, json={"campaign_id": campaign_id}, timeout=5)
        return 200 <= resp.status_code < 300
    except requests.RequestException:
        return False


st.title("Campañas")

# =============================================================================
# SETUP VIEW (campanas_mode == "setup")
# =============================================================================
if st.session_state.campanas_mode == "setup":
    st.subheader("Configurar campaña")

    # Load tags and build options
    try:
        tags = fetch_tags_with_counts()
    except Exception:
        tags = []
        st.error("Error al cargar etiquetas.")

    name_to_id = {tag["name"]: str(tag["id"]) for tag in tags}

    selected_tag_names = st.multiselect(
        "Segmento (etiquetas)",
        options=list(name_to_id.keys()),
        key="campanas_tag_names_widget",
    )
    selected_tag_ids = [name_to_id[name] for name in selected_tag_names]
    st.session_state.campanas_selected_tag_ids = selected_tag_ids

    # Load templates and build options
    try:
        templates = fetch_templates(active_only=True)
    except Exception:
        templates = []
        st.error("Error al cargar plantillas.")

    name_to_tpl = {tpl["name"]: tpl for tpl in templates}

    selected_tpl_name = st.selectbox(
        "Plantilla de mensaje",
        options=[None] + list(name_to_tpl.keys()),
        format_func=lambda x: "— Selecciona —" if x is None else x,
        key="campanas_template_widget",
    )
    selected_template = name_to_tpl.get(selected_tpl_name) if selected_tpl_name else None
    if selected_template:
        st.session_state.campanas_selected_template_id = str(selected_template["id"])
    else:
        st.session_state.campanas_selected_template_id = None

    # Fetch recipients and compute count
    if selected_tag_ids:
        try:
            patients = fetch_patients_by_tags(selected_tag_ids)
        except Exception:
            patients = []
            st.error("Error al obtener pacientes del segmento.")
    else:
        patients = []

    count = len(patients)
    st.session_state.campanas_recipient_count = count
    st.caption(f"{count} pacientes en este segmento")

    if count == 0 and selected_tag_ids:
        st.warning("No hay pacientes en el segmento seleccionado.")

    # Template preview
    if selected_template:
        st.subheader("Vista previa")
        preview_text = render_preview(selected_template["body"])
        st.text_area(
            "Mensaje",
            value=preview_text,
            disabled=True,
            height=160,
            key="campanas_preview_area",
        )

    st.markdown("---")

    # Confirmation gate (WA-03)
    st.markdown(f"Estás a punto de enviar a **{count} pacientes**. ¿Confirmar?")
    col1, col2 = st.columns([1, 1])
    can_confirm = bool(selected_tag_ids) and selected_template is not None and count > 0
    with col1:
        confirm = st.button(
            "Confirmar y enviar",
            type="primary",
            use_container_width=True,
            disabled=not can_confirm,
        )
    with col2:
        reset = st.button("Cancelar", use_container_width=True)

    if reset:
        st.session_state.campanas_selected_tag_ids = []
        st.session_state.campanas_selected_template_id = None
        st.session_state.campanas_recipient_count = 0
        st.rerun()

    if confirm:
        # Auto-name per D-06: "{tag_name} · {dd mmm yyyy}"
        primary_tag_name = next(
            (t["name"] for t in tags if str(t["id"]) == str(selected_tag_ids[0])),
            "campaña",
        )
        campaign_name = f"{primary_tag_name} · {_format_date(datetime.now())}"

        try:
            row = insert_campaign(
                campaign_name=campaign_name,
                template_id=selected_template["id"],
                segment_tags=[str(tid) for tid in selected_tag_ids],
                total_recipients=count,
            )
            new_id = row["id"]
            insert_campaign_recipients(new_id, [str(p["id"]) for p in patients])
        except Exception as exc:
            st.error("Error al guardar la campaña. Intenta de nuevo.")
            st.caption(f"Detalle técnico: {exc}")
            st.stop()

        if not _trigger_n8n_webhook(str(new_id)):
            st.error("Error al iniciar la campaña. Verifica que n8n esté activo e intenta de nuevo.")
            st.stop()

        st.session_state.campanas_active_campaign_id = str(new_id)
        st.session_state.campanas_mode = "progress"
        st.rerun()

# =============================================================================
# PROGRESS VIEW (campanas_mode == "progress")
# =============================================================================
elif st.session_state.campanas_mode == "progress":
    active_id = st.session_state.campanas_active_campaign_id

    campaign = fetch_campaign_status(active_id) if active_id else None

    if campaign is None:
        st.error("Campaña no encontrada.")
        if st.button("Volver al inicio", use_container_width=True):
            st.session_state.campanas_mode = "setup"
            st.session_state.campanas_active_campaign_id = None
            st.rerun()
        st.stop()

    st.subheader("Enviando campaña")
    st.caption(campaign["campaign_name"])

    total_recipients = campaign["total_recipients"]
    sent_count = campaign["sent_count"]
    failed_count = campaign["failed_count"]

    # Zero-division guard (RESEARCH Pitfall 4)
    progress_val = (sent_count / total_recipients) if total_recipients > 0 else 0.0
    st.progress(progress_val)
    st.markdown(f"Enviando... {sent_count} / {total_recipients} mensajes")

    if failed_count > 0:
        st.error(f"{failed_count} mensajes fallaron.")

    # Status branching
    status = campaign["status"]
    if status == "in_progress":
        if st.button("Cancelar campaña", use_container_width=True):
            cancel_campaign(active_id)
            st.rerun()
    elif status == "pending":
        # Show warning only if campaign is older than 30 seconds
        created_at = campaign.get("created_at")
        if created_at:
            elapsed = (datetime.now(created_at.tzinfo) - created_at).total_seconds()
            if elapsed > 30:
                st.warning("La campaña está en cola. n8n puede estar procesando o no responde.")
    elif status == "completed":
        st.success(f"Campaña completada. {sent_count} mensajes enviados.")
        if st.button("Nueva campaña", use_container_width=True, key="btn_nueva_completed"):
            for key in [
                "campanas_mode",
                "campanas_selected_tag_ids",
                "campanas_selected_template_id",
                "campanas_active_campaign_id",
                "campanas_recipient_count",
            ]:
                st.session_state.pop(key, None)
            st.session_state.setdefault("campanas_mode", "setup")
            st.rerun()
    elif status == "cancelled":
        st.warning(f"Campaña cancelada. {sent_count} mensajes enviados antes de cancelar.")
        if st.button("Nueva campaña", use_container_width=True, key="btn_nueva_cancelled"):
            for key in [
                "campanas_mode",
                "campanas_selected_tag_ids",
                "campanas_selected_template_id",
                "campanas_active_campaign_id",
                "campanas_recipient_count",
            ]:
                st.session_state.pop(key, None)
            st.session_state.setdefault("campanas_mode", "setup")
            st.rerun()

    # Auto-refresh while campaign is active
    try:
        from streamlit_autorefresh import st_autorefresh
        if campaign["status"] in ("pending", "in_progress"):
            st_autorefresh(interval=5000, key="campanas_progress_refresh")
    except ImportError:
        pass

# =============================================================================
# HISTORY SECTION (always rendered)
# =============================================================================
st.markdown("---")
st.subheader("Historial de campañas")
try:
    history = fetch_campaign_history(limit=50)
except Exception:
    history = []
    st.error("Error al cargar el historial de campañas.")

if not history:
    st.info("Sin campañas enviadas")
    st.caption("Selecciona un segmento y una plantilla para enviar tu primera campaña.")
else:
    import pandas as pd

    df = pd.DataFrame([
        {
            "Nombre": h["campaign_name"],
            "Segmento": h["segment_tag_names"] or "—",
            "Enviados": f"{h['sent_count']} / {h['total_recipients']}",
            "Fallidos": h["failed_count"],
            "Estado": h["status"],
            "Fecha": h["created_at"].strftime("%Y-%m-%d %H:%M") if h["created_at"] else "",
        }
        for h in history
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)
