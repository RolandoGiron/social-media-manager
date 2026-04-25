"""8_Publicaciones.py — Phase 6 standalone social publishing (SOCIAL-01, SOCIAL-03)."""
import os
from datetime import date, datetime, time, timedelta

import requests
import streamlit as st

from components.database import (
    delete_social_post,
    fetch_social_posts,
    insert_social_post,
)
from components.sidebar import render_sidebar
from components.social_posts import (
    ALLOWED_IMAGE_EXTS,
    MAX_IMAGE_BYTES,
    MX_TZ,
    combine_local_datetime,
    save_uploaded_image,
    status_label,
)

render_sidebar()

# ---------- Session state defaults ----------
st.session_state.setdefault("pubs_caption", "")
st.session_state.setdefault("pubs_image_bytes", None)
st.session_state.setdefault("pubs_image_name", None)
st.session_state.setdefault("pubs_platforms", ["Instagram", "Facebook"])
st.session_state.setdefault("pubs_date", date.today())
st.session_state.setdefault("pubs_time", (datetime.now() + timedelta(minutes=15)).time())


def _trigger_social_webhook(post_id: str) -> bool:
    base_url = os.environ.get("N8N_WEBHOOK_BASE_URL", "http://n8n:5678")
    url = f"{base_url}/webhook/social-publish"
    try:
        resp = requests.post(url, json={"post_id": post_id}, timeout=5)
        return 200 <= resp.status_code < 300
    except requests.RequestException:
        return False


def _truncate(text: str, n: int = 60) -> str:
    return text if len(text) <= n else text[: n - 1] + "\u2026"


def _format_dt(dt: datetime | None) -> str:
    if dt is None:
        return "\u2014"
    return dt.astimezone(MX_TZ).strftime("%d/%m/%Y %H:%M")


st.title("Publicaciones")

# Mock mode banner -- shown when MOCK_SOCIAL is "true" (default per .env.example)
if os.environ.get("MOCK_SOCIAL", "true").lower() == "true":
    st.info(
        "Modo prueba activo (MOCK_SOCIAL=true). "
        "Las publicaciones se simulan sin llamar a Meta API."
    )

# =============================================================================
# COMPOSER
# =============================================================================
st.subheader("Crear publicaci\u00f3n")

caption = st.text_area(
    "Caption",
    key="pubs_caption",
    height=120,
    max_chars=2200,
)

uploaded = st.file_uploader(
    "Imagen",
    type=["jpg", "jpeg", "png", "webp"],
    key="pubs_uploader",
)
if uploaded is not None:
    raw = uploaded.getvalue()
    if len(raw) > MAX_IMAGE_BYTES:
        st.error("La imagen excede 8 MB. Usa una imagen m\u00e1s peque\u00f1a.")
        st.session_state.pubs_image_bytes = None
        st.session_state.pubs_image_name = None
    else:
        st.session_state.pubs_image_bytes = raw
        st.session_state.pubs_image_name = uploaded.name

if st.session_state.pubs_image_bytes:
    st.image(st.session_state.pubs_image_bytes, width=300)

platforms = st.multiselect(
    "Plataformas",
    options=["Instagram", "Facebook"],
    default=st.session_state.pubs_platforms,
    key="pubs_platforms",
)

col1, col2 = st.columns(2)
with col1:
    pub_date = st.date_input(
        "Fecha de publicaci\u00f3n",
        key="pubs_date",
        min_value=date.today(),
    )
with col2:
    pub_time = st.time_input("Hora de publicaci\u00f3n", key="pubs_time")

scheduled_at = combine_local_datetime(pub_date, pub_time)
now_mx = datetime.now(MX_TZ)
in_future = scheduled_at > now_mx
if not in_future:
    st.caption("La fecha debe ser futura.")

button_disabled = (
    not caption.strip()
    or st.session_state.pubs_image_bytes is None
    or not platforms
    or not in_future
)

if st.button(
    "Programar publicaci\u00f3n",
    type="primary",
    use_container_width=True,
    disabled=button_disabled,
):
    try:
        rel_path = save_uploaded_image(
            st.session_state.pubs_image_bytes,
            st.session_state.pubs_image_name or "image.jpg",
        )
    except ValueError as exc:
        st.error(f"{exc}")
        st.stop()

    try:
        row = insert_social_post(
            caption=caption,
            image_url=rel_path,
            platforms=platforms,
            scheduled_at=scheduled_at,
        )
    except Exception:  # pragma: no cover -- DB failure surface
        st.error("Error al guardar la publicaci\u00f3n. Intenta de nuevo.")
        st.stop()

    if not _trigger_social_webhook(str(row["id"])):
        st.error(
            "Error al programar la publicaci\u00f3n. "
            "Verifica que n8n est\u00e9 activo e intenta de nuevo."
        )
        st.stop()

    st.success(
        f"Publicaci\u00f3n programada para {pub_date.strftime('%d/%m/%Y')} "
        f"a las {pub_time.strftime('%H:%M')}."
    )
    # Delete keys so setdefault at top restores defaults on next run.
    # Direct assignment fails for widget-bound keys (pubs_caption).
    for key in ("pubs_caption", "pubs_image_bytes", "pubs_image_name", "pubs_uploader"):
        st.session_state.pop(key, None)
    st.rerun()

st.markdown("---")

# =============================================================================
# LIST
# =============================================================================
st.subheader("Publicaciones programadas")

posts = fetch_social_posts(limit=100)

if not posts:
    st.info("Sin publicaciones programadas. Crea tu primera publicaci\u00f3n arriba.")
else:
    rows = [
        {
            "Caption": _truncate(p["caption"]),
            "Plataformas": ", ".join(p["platforms"] or []),
            "Fecha programada": _format_dt(p.get("scheduled_at")),
            "Estado": status_label(p["status"]),
        }
        for p in posts
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)

    for p in posts:
        if p["status"] in ("draft", "scheduled"):
            if st.button(
                "Eliminar publicaci\u00f3n",
                type="secondary",
                key=f"del_{p['id']}",
            ):
                delete_social_post(str(p["id"]))
                st.rerun()
        if p["status"] == "failed":
            err = p.get("error_message") or "error desconocido"
            st.error(f"Error en '{_truncate(p['caption'])}': {err}")
