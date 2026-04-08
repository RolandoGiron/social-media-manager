"""Knowledge Base page -- Manage FAQ items used by the chatbot.

Implements decisions D-03, D-04 from 04-CONTEXT.md:
- D-03: Admin UI pages for inbox and knowledge base management
- D-04: FAQ items stored in knowledge_base table with pregunta/respuesta/categoria/is_active
"""
import streamlit as st
from components.sidebar import render_sidebar
from components.database import (
    fetch_knowledge_base,
    upsert_knowledge_base_item,
    delete_knowledge_base_item,
)

render_sidebar()

st.title("Knowledge Base")

CATEGORIAS = ["horarios", "ubicacion", "precios", "servicios", "general"]

# Session state for editing
st.session_state.setdefault("kb_edit_item_id", None)
st.session_state.setdefault("kb_confirm_delete_id", None)

# --- Add new FAQ expander ---
with st.expander("Agregar nuevo FAQ", expanded=False):
    with st.form("form_add_faq", clear_on_submit=True):
        new_pregunta = st.text_input("Pregunta")
        new_respuesta = st.text_area("Respuesta")
        new_categoria = st.selectbox("Categoria", options=CATEGORIAS, key="add_cat")
        new_active = st.checkbox("Activo", value=True, key="add_active")
        submitted = st.form_submit_button("Guardar FAQ")

        if submitted:
            if not new_pregunta.strip():
                st.error("La pregunta no puede estar vacia.")
            elif not new_respuesta.strip():
                st.error("La respuesta no puede estar vacia.")
            else:
                upsert_knowledge_base_item(
                    None,
                    new_pregunta.strip(),
                    new_respuesta.strip(),
                    new_categoria,
                    new_active,
                )
                st.success("FAQ agregado exitosamente.")
                st.rerun()

st.divider()

# --- Fetch all items (including inactive) for management ---
items = fetch_knowledge_base(active_only=False)

if not items:
    st.info("No hay items en la Knowledge Base. Agrega el primer FAQ arriba.")
else:
    # Group by categoria
    from collections import defaultdict
    grouped: dict[str, list] = defaultdict(list)
    for item in items:
        grouped[item["categoria"]].append(item)

    for categoria, cat_items in grouped.items():
        st.subheader(categoria.capitalize())

        for item in cat_items:
            item_id = str(item["id"])
            is_active = item.get("is_active", True)
            pregunta = item.get("pregunta", "")
            respuesta = item.get("respuesta", "")
            cat = item.get("categoria", "general")

            active_icon = ":green_circle:" if is_active else ":red_circle:"
            respuesta_preview = (respuesta[:80] + "...") if len(respuesta) > 80 else respuesta

            with st.container():
                col_text, col_actions = st.columns([4, 1])
                with col_text:
                    st.markdown(f"{active_icon} **{pregunta}**")
                    st.caption(respuesta_preview)

                with col_actions:
                    # Toggle active status
                    toggle_label = "Desactivar" if is_active else "Activar"
                    if st.button(toggle_label, key=f"toggle_{item_id}", use_container_width=True):
                        upsert_knowledge_base_item(item_id, pregunta, respuesta, cat, not is_active)
                        st.rerun()

                    # Edit button
                    if st.button("Editar", key=f"edit_{item_id}", use_container_width=True):
                        st.session_state.kb_edit_item_id = item_id
                        st.rerun()

                    # Delete button with confirmation
                    if st.session_state.kb_confirm_delete_id == item_id:
                        st.warning("Confirmar?")
                        if st.button("Si, eliminar", key=f"del_confirm_{item_id}", use_container_width=True, type="primary"):
                            delete_knowledge_base_item(item_id)
                            st.session_state.kb_confirm_delete_id = None
                            st.success("FAQ eliminado.")
                            st.rerun()
                        if st.button("Cancelar", key=f"del_cancel_{item_id}", use_container_width=True):
                            st.session_state.kb_confirm_delete_id = None
                            st.rerun()
                    else:
                        if st.button("Eliminar", key=f"delete_{item_id}", use_container_width=True):
                            st.session_state.kb_confirm_delete_id = item_id
                            st.rerun()

            # --- Inline edit form ---
            if st.session_state.kb_edit_item_id == item_id:
                with st.form(f"form_edit_{item_id}"):
                    st.markdown(f"**Editando:** {pregunta}")
                    edit_pregunta = st.text_input("Pregunta", value=pregunta, key=f"ep_{item_id}")
                    edit_respuesta = st.text_area("Respuesta", value=respuesta, key=f"er_{item_id}")
                    current_cat_idx = CATEGORIAS.index(cat) if cat in CATEGORIAS else 0
                    edit_categoria = st.selectbox("Categoria", options=CATEGORIAS, index=current_cat_idx, key=f"ec_{item_id}")
                    edit_active = st.checkbox("Activo", value=is_active, key=f"ea_{item_id}")

                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.form_submit_button("Guardar cambios", use_container_width=True, type="primary"):
                            if not edit_pregunta.strip():
                                st.error("La pregunta no puede estar vacia.")
                            elif not edit_respuesta.strip():
                                st.error("La respuesta no puede estar vacia.")
                            else:
                                upsert_knowledge_base_item(
                                    item_id,
                                    edit_pregunta.strip(),
                                    edit_respuesta.strip(),
                                    edit_categoria,
                                    edit_active,
                                )
                                st.session_state.kb_edit_item_id = None
                                st.success("FAQ actualizado.")
                                st.rerun()
                    with col_cancel:
                        if st.form_submit_button("Cancelar", use_container_width=True):
                            st.session_state.kb_edit_item_id = None
                            st.rerun()

            st.markdown("---")
