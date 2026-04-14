"""7_Campañas.py — Phase 5 broadcast launch + monitor (WA-02, WA-03, WA-04).

Phase 6 extension: Step 3 — optional social post linked to campaign (SOCIAL-02).
"""
import os
from datetime import date, datetime, timedelta

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
    insert_social_post,
)
from components.sidebar import render_sidebar
from components.social_posts import (
    MX_TZ,
    combine_local_datetime,
    save_uploaded_image,
)
from components.templates import render_preview

render_sidebar()

# ---------- Session state defaults ----------
st.session_state.setdefault("campanas_mode", "setup")
st.session_state.setdefault("campanas_selected_tag_ids", [])
st.session_state.setdefault("campanas_selected_template_id", None)
st.session_state.setdefault("campanas_active_campaign_id", None)
st.session_state.setdefault("campanas_recipient_count", 0)
# Phase 6 Step 3 — social publishing extension
st.session_state.setdefault("campanas_publish_social", False)
st.session_state.setdefault("campanas_social_caption", "")
st.session_state.setdefault("campanas_social_image_bytes", None)
st.session_state.setdefault("campanas_social_image_name", None)
st.session_state.setdefault("campanas_social_platforms", ["Instagram", "Facebook"])
st.session_state.setdefault("campanas_social_date", date.today())
st.session_state.setdefault("campanas_social_time", (datetime.now() + timedelta(minutes=15)).time())

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


def _trigger_n8n_social_webhook(post_id: str) -> bool:
    base_url = os.environ.get("N8N_WEBHOOK_BASE_URL", "http://n8n:5678")
    url = f"{base_url}/webhook/social-publish"
    try:
        resp = requests.post(url, json={"post_id": post_id}, timeout=5)
        return 200 <= resp.status_code < 300
    except requests.RequestException:
        return False


def _handle_launch_campaign(recipient_ids: list, recipient_count: int) -> None:
    """Handle the launch campaign confirm action.

    Runs the existing Phase 5 path (insert + WA webhook) then optionally
    adds a linked social_posts row and triggers the social webhook (Phase 6 Step 3).
    This function is extracted to allow unit testing without executing the full
    module-level Streamlit render.
    """
    tags = st.session_state.get("_campanas_tags_cache", [])
    selected_tag_ids = st.session_state.get("campanas_selected_tag_ids", [])
    selected_template = st.session_state.get("_campanas_selected_template_cache")

    primary_tag_name = next(
        (t["name"] for t in tags if str(t["id"]) == str(selected_tag_ids[0])),
        "campa\u00f1a",
    ) if selected_tag_ids else "campa\u00f1a"
    campaign_name = f"{primary_tag_name} \u00b7 {_format_date(datetime.now())}"

    try:
        row = insert_campaign(
            campaign_name=campaign_name,
            template_id=selected_template["id"],
            segment_tags=[str(tid) for tid in selected_tag_ids],
            total_recipients=recipient_count,
        )
        new_id = row["id"]
        insert_campaign_recipients(new_id, recipient_ids)
    except Exception as exc:
        st.error("Error al guardar la campa\u00f1a. Intenta de nuevo.")
        st.caption(f"Detalle t\u00e9cnico: {exc}")
        st.stop()

    # Phase 6 Step 3: optionally create a social post linked to this campaign
    social_post_id = None
    if st.session_state.get("campanas_publish_social"):
        try:
            rel_path = save_uploaded_image(
                st.session_state.campanas_social_image_bytes,
                st.session_state.campanas_social_image_name or "image.jpg",
            )
            social_row = insert_social_post(
                caption=st.session_state.campanas_social_caption,
                image_url=rel_path,
                platforms=st.session_state.campanas_social_platforms,
                scheduled_at=combine_local_datetime(
                    st.session_state.campanas_social_date,
                    st.session_state.campanas_social_time,
                ),
                campaign_id=str(new_id),
            )
            social_post_id = str(social_row["id"])
        except Exception:
            st.warning(
                "Campa\u00f1a WA preparada, pero el post social fall\u00f3 al guardarse. "
                "Rev\u00edsalo en Publicaciones."
            )

    if not _trigger_n8n_webhook(str(new_id)):
        st.error("Error al iniciar la campa\u00f1a. Verifica que n8n est\u00e9 activo e intenta de nuevo.")
        st.stop()

    # Best-effort: trigger social webhook only after WA webhook succeeded
    if social_post_id and not _trigger_n8n_social_webhook(social_post_id):
        st.warning(
            "Campa\u00f1a WA iniciada, pero el post social fall\u00f3 al encolarse. "
            "Rev\u00edsalo en Publicaciones."
        )

    st.session_state.campanas_active_campaign_id = str(new_id)
    st.session_state.campanas_mode = "progress"
    st.rerun()


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
    # Cache for _handle_launch_campaign (needed after button click)
    st.session_state["_campanas_tags_cache"] = tags

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
    # Cache selected_template for _handle_launch_campaign
    st.session_state["_campanas_selected_template_cache"] = selected_template

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

    # -----------------------------------------------------------------------
    # Step 3 — Publicar también en redes (opcional) — Phase 6 SOCIAL-02
    # -----------------------------------------------------------------------
    st.subheader("Paso 3 \u2014 Publicar tambi\u00e9n en redes (opcional)")
    publish_social = st.checkbox(
        "Publicar en redes sociales junto con la campa\u00f1a WhatsApp",
        key="campanas_publish_social",
    )

    step3_valid = True
    if publish_social:
        social_caption = st.text_area(
            "Caption del post",
            key="campanas_social_caption",
            height=120,
            max_chars=2200,
            help="Puede ser distinto al mensaje de WhatsApp",
        )
        social_uploaded = st.file_uploader(
            "Imagen",
            type=["jpg", "jpeg", "png", "webp"],
            key="campanas_social_uploader",
        )
        if social_uploaded is not None:
            st.session_state.campanas_social_image_bytes = social_uploaded.getvalue()
            st.session_state.campanas_social_image_name = social_uploaded.name
        if st.session_state.campanas_social_image_bytes:
            st.image(st.session_state.campanas_social_image_bytes, width=300)

        social_platforms = st.multiselect(
            "Plataformas",
            options=["Instagram", "Facebook"],
            default=st.session_state.campanas_social_platforms,
            key="campanas_social_platforms",
        )
        sc1, sc2 = st.columns(2)
        with sc1:
            social_date = st.date_input(
                "Fecha de publicaci\u00f3n",
                key="campanas_social_date",
                min_value=date.today(),
            )
        with sc2:
            social_time = st.time_input(
                "Hora de publicaci\u00f3n",
                key="campanas_social_time",
            )
        social_scheduled_at = combine_local_datetime(social_date, social_time)
        step3_valid = bool(
            social_caption.strip()
            and st.session_state.campanas_social_image_bytes
            and social_platforms
            and social_scheduled_at > datetime.now(MX_TZ)
        )
        if not step3_valid:
            st.caption(
                "Completa caption, imagen, plataformas y una fecha futura para lanzar."
            )

    st.markdown("---")

    # Confirmation gate (WA-03)
    gate_msg = f"Est\u00e1s a punto de enviar a **{count} pacientes**"
    if st.session_state.get("campanas_publish_social"):
        gate_msg += " y publicar en redes sociales"
    gate_msg += ". \u00bfConfirmar?"
    st.markdown(gate_msg)
    col1, col2 = st.columns([1, 1])
    can_confirm = bool(selected_tag_ids) and selected_template is not None and count > 0
    with col1:
        confirm = st.button(
            "Lanzar campa\u00f1a",
            type="primary",
            use_container_width=True,
            disabled=not can_confirm or not step3_valid,
        )
    with col2:
        reset = st.button("Cancelar", use_container_width=True)

    if reset:
        st.session_state.campanas_selected_tag_ids = []
        st.session_state.campanas_selected_template_id = None
        st.session_state.campanas_recipient_count = 0
        st.rerun()

    if confirm:
        _handle_launch_campaign(
            recipient_ids=[str(p["id"]) for p in patients],
            recipient_count=count,
        )

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
