"""Inbox page -- Monitor chatbot conversations and reply manually.

Implements decisions D-14 through D-17 from 04-CONTEXT.md:
- D-14: Split-pane layout (conversation list left, chat right)
- D-15: Status badges; human_handoff conversations sorted first
- D-16: Close conversation button per chat
- D-17: Auto-refresh every 10 seconds
"""
import streamlit as st
from components.sidebar import render_sidebar
from components.database import (
    fetch_conversations,
    fetch_messages_for_conversation,
    insert_message,
    update_conversation_state,
)
from components.evolution_api import EvolutionAPIClient, EvolutionAPIError

render_sidebar()

# Auto-refresh every 10 seconds (D-17)
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=10000, key="inbox_refresh")
except ImportError:
    # Fallback: manual refresh button when streamlit-autorefresh not installed
    pass

st.title("Inbox")

# Session state: persist selected conversation across auto-refreshes
st.session_state.setdefault("selected_conversation_id", None)

# --- State filter selector ---
state_options = {"Todas (abiertas)": None, "Human Handoff": "human_handoff", "Bot": "faq_flow"}
selected_filter_label = st.selectbox(
    "Filtrar por estado",
    options=list(state_options.keys()),
    label_visibility="collapsed",
)
state_filter = state_options[selected_filter_label]

# Fetch conversations
conversations = fetch_conversations(state_filter=state_filter)

# --- Split-pane layout (D-14): narrow left, wide right ---
left_col, right_col = st.columns([1, 2])


def _state_badge(state: str) -> str:
    """Return a short badge label for a conversation state."""
    if state == "human_handoff":
        return "HUMANO"
    elif state == "closed":
        return "CERRADA"
    else:
        return "BOT"


def _display_name(conv: dict) -> str:
    """Return patient name or WA contact ID as fallback."""
    first = conv.get("first_name") or ""
    last = conv.get("last_name") or ""
    name = (first + " " + last).strip()
    return name if name else (conv.get("wa_contact_id") or "Desconocido")


with left_col:
    st.subheader("Conversaciones")
    if not conversations:
        st.info("No hay conversaciones abiertas.")
    else:
        for conv in conversations:
            conv_id = str(conv["id"])
            is_handoff = conv["state"] == "human_handoff"
            name = _display_name(conv)
            badge = _state_badge(conv["state"])
            prefix = "[!] " if is_handoff else ""
            last_msg = conv.get("last_message") or ""
            preview = (last_msg[:50] + "...") if len(last_msg) > 50 else last_msg

            # Format timestamp
            ts = conv.get("last_message_at") or conv.get("created_at")
            ts_str = ts.strftime("%d/%m %H:%M") if ts and hasattr(ts, "strftime") else str(ts or "")

            label = f"{prefix}{name} [{badge}]\n{preview}\n{ts_str}"
            is_selected = st.session_state.selected_conversation_id == conv_id

            if st.button(
                label,
                key=f"conv_{conv_id}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                st.session_state.selected_conversation_id = conv_id
                st.rerun()

# --- Right column: chat view ---
with right_col:
    selected_id = st.session_state.get("selected_conversation_id")

    if not selected_id:
        st.info("Selecciona una conversacion para ver el historial")
    else:
        # Find the selected conversation in list
        selected_conv = next(
            (c for c in conversations if str(c["id"]) == selected_id), None
        )

        if selected_conv is None:
            # Conversation may be closed or filtered out
            st.warning("La conversacion ya no esta disponible. Puede haberse cerrado.")
            st.session_state.selected_conversation_id = None
        else:
            name = _display_name(selected_conv)
            badge = _state_badge(selected_conv["state"])
            st.subheader(f"{name} - {badge}")

            # --- Fetch and render messages ---
            messages = fetch_messages_for_conversation(selected_id)

            if not messages:
                st.caption("Sin mensajes aun.")
            else:
                for msg in messages:
                    sender = msg.get("sender", "")
                    content = msg.get("content") or ""
                    created_at = msg.get("created_at")
                    ts_str = created_at.strftime("%H:%M") if created_at and hasattr(created_at, "strftime") else str(created_at or "")

                    if sender == "patient":
                        role = "user"
                    else:
                        role = "assistant"

                    with st.chat_message(role):
                        st.write(content)
                        st.caption(ts_str)

            st.divider()

            # --- Close conversation button (D-16) ---
            col_close, col_spacer = st.columns([1, 3])
            with col_close:
                if st.button("Cerrar conversacion", key="btn_close_conv", type="secondary"):
                    update_conversation_state(selected_id, "closed")
                    st.session_state.selected_conversation_id = None
                    st.success("Conversacion cerrada.")
                    st.rerun()

            # --- Manual reply via chat_input ---
            reply_text = st.chat_input("Escribe tu respuesta...")
            if reply_text:
                wa_number = selected_conv.get("wa_contact_id", "")
                try:
                    client = EvolutionAPIClient()
                    client.send_text_message(wa_number, reply_text)
                    insert_message(selected_id, "outbound", "agent", reply_text)
                    st.rerun()
                except EvolutionAPIError as e:
                    st.error(f"Error al enviar mensaje: {e.message}")
                except Exception as e:
                    st.error(f"Error inesperado: {e}")
