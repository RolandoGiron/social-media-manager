"""Shared sidebar component with WhatsApp session status. Per D-03, D-04, D-05."""
import os
import time

import streamlit as st
from components.evolution_api import EvolutionAPIClient, EvolutionAPIError

POLL_INTERVAL_SECONDS = 60  # Per D-04


def render_whatsapp_status(state: str) -> str:
    """Return a status string for the given WhatsApp connection state.

    This is a pure function (no Streamlit calls) for testability.
    """
    if state == "open":
        clinic_number = os.environ.get("CLINIC_WHATSAPP_NUMBER", "")
        line = ":green_circle: **Conectado**"
        if clinic_number:
            line += f"\nNumero: {clinic_number}"
        return line
    elif state == "close":
        return ":red_circle: **Desconectado**"
    elif state == "connecting":
        return ":orange_circle: **Conectando...**"
    else:
        return ":orange_circle: **Estado desconocido**"


def get_cached_connection_state(
    last_check_time: float,
    last_state: str,
    client: EvolutionAPIClient | None = None,
) -> tuple[str, bool]:
    """Return (state, was_cached) respecting the 60s polling interval.

    If last_check_time is within POLL_INTERVAL_SECONDS, returns cached state.
    Otherwise fetches fresh state from Evolution API.
    """
    now = time.time()
    if now - last_check_time < POLL_INTERVAL_SECONDS:
        return last_state, True

    if client is None:
        client = EvolutionAPIClient()

    try:
        state = client.get_connection_state()
    except (EvolutionAPIError, Exception):
        state = "unknown"

    return state, False


def render_sidebar():
    """Render WhatsApp status in sidebar. Call from app.py before pg.run()."""
    client = EvolutionAPIClient()

    # Poll every 60 seconds using session_state timestamp (per D-04)
    now = time.time()
    last_check = st.session_state.get("wa_last_check", 0)

    if now - last_check > POLL_INTERVAL_SECONDS:
        try:
            state = client.get_connection_state()
            st.session_state["wa_state"] = state
            st.session_state["wa_last_check"] = now
            if state == "open":
                st.session_state["wa_last_connected"] = time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
        except EvolutionAPIError:
            st.session_state["wa_state"] = "unknown"
        except Exception:
            st.session_state["wa_state"] = "unknown"

    state = st.session_state.get("wa_state", "unknown")

    with st.sidebar:
        st.markdown("---")
        st.markdown("**WhatsApp**")
        status_text = render_whatsapp_status(state)
        for line in status_text.split("\n"):
            if line.startswith("Numero:"):
                st.caption(line)
            else:
                st.markdown(line)

        last_connected = st.session_state.get("wa_last_connected")
        if last_connected:
            st.caption(f"Ultima conexion: {last_connected}")
