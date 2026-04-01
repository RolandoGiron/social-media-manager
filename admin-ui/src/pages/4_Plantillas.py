"""Plantillas de Mensaje page. Per D-09, D-10, D-11."""
import streamlit as st
import pandas as pd
from components.sidebar import render_sidebar
from components.database import fetch_templates, insert_template, delete_template
from components.templates import extract_variables, render_preview

render_sidebar()

# Session state initialization
st.session_state.setdefault("plantillas_mode", "list")
st.session_state.setdefault("edit_template_id", None)

# Spanish month abbreviation mapping
_MONTH_ABBR_ES = {
    "Jan": "ene",
    "Feb": "feb",
    "Mar": "mar",
    "Apr": "abr",
    "May": "may",
    "Jun": "jun",
    "Jul": "jul",
    "Aug": "ago",
    "Sep": "sep",
    "Oct": "oct",
    "Nov": "nov",
    "Dec": "dic",
}


def _format_date_es(dt) -> str:
    """Format a datetime to '01 abr 2026' Spanish format."""
    if dt is None:
        return ""
    if isinstance(dt, str):
        return dt
    en_str = dt.strftime("%d %b %Y")
    for en, es in _MONTH_ABBR_ES.items():
        en_str = en_str.replace(en, es)
    return en_str


st.title("Plantillas de Mensaje")

# ---------------------------------------------------------------------------
# Editor mode
# ---------------------------------------------------------------------------
if st.session_state.plantillas_mode == "editor":
    col_editor, col_preview = st.columns([1, 1])

    with col_editor:
        template_name = st.text_input(
            "Nombre de plantilla",
            placeholder="Ej: Promocion mensual, Recordatorio de cita...",
            key="tpl_name",
        )
        category = st.selectbox(
            "Categoria",
            options=["general", "promocion", "recordatorio"],
            key="tpl_category",
        )
        body = st.text_area(
            "Cuerpo del mensaje",
            placeholder="Escribe tu mensaje. Usa {{nombre}}, {{fecha}} u otras variables entre llaves dobles.",
            height=300,
            key="tpl_body",
        )

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            save_clicked = st.button("Guardar plantilla", type="primary")
        with btn_col2:
            discard_clicked = st.button("Descartar cambios")

        if save_clicked:
            if not template_name.strip():
                st.error("El nombre de la plantilla es obligatorio.")
            elif not body.strip():
                st.error("El cuerpo del mensaje no puede estar vacio.")
            else:
                try:
                    variables = extract_variables(body)
                    insert_template(
                        template_name.strip(), body.strip(), variables, category
                    )
                    st.success("Plantilla guardada exitosamente.")
                    st.session_state.plantillas_mode = "list"
                    st.session_state.edit_template_id = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar la plantilla: {e}")

        if discard_clicked:
            st.session_state.plantillas_mode = "list"
            st.session_state.edit_template_id = None
            st.rerun()

    with col_preview:
        st.subheader("Vista previa")
        if body and body.strip():
            rendered = render_preview(body)
            with st.container(border=True):
                st.markdown(rendered)

            vars_found = extract_variables(body)
            if vars_found:
                st.caption(f"Variables detectadas: {', '.join(vars_found)}")
            else:
                st.caption("No se detectaron variables.")
        else:
            st.info("Escribe un mensaje en el editor para ver la vista previa.")

# ---------------------------------------------------------------------------
# List mode
# ---------------------------------------------------------------------------
else:
    if st.button("Nueva plantilla", icon=":material/add:"):
        st.session_state.plantillas_mode = "editor"
        st.session_state.edit_template_id = None
        st.rerun()

    try:
        templates = fetch_templates(active_only=True)
    except Exception as e:
        st.error(f"Error al cargar plantillas: {e}")
        templates = []

    if not templates:
        st.info("No hay plantillas creadas")
        st.markdown(
            "Crea tu primera plantilla de mensaje para usarla en campanas de WhatsApp."
        )
    else:
        # Build display DataFrame
        display_data = []
        for t in templates:
            variables_str = ", ".join(t.get("variables") or [])
            created_str = _format_date_es(t.get("created_at"))
            display_data.append(
                {
                    "Nombre": t["name"],
                    "Categoria": t.get("category", "general"),
                    "Variables": variables_str,
                    "Creada": created_str,
                }
            )

        display_df = pd.DataFrame(display_data)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # Delete actions per template
        for t in templates:
            with st.expander(f"Acciones: {t['name']}"):
                st.warning(
                    f"Eliminar plantilla: Estas seguro de que deseas eliminar "
                    f"'{t['name']}'? Esta accion no se puede deshacer."
                )
                if st.button("Eliminar", key=f"del_{t['id']}"):
                    try:
                        delete_template(str(t["id"]))
                        st.success("Plantilla eliminada.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al eliminar plantilla: {e}")
