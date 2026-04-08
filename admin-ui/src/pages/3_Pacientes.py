"""Pacientes page -- CRM patient management: import, list, search, filter, tag CRUD, bulk assign.

Implements decisions D-01 through D-08 from 03-CONTEXT.md.
"""
import streamlit as st
import pandas as pd
from components.sidebar import render_sidebar
from components.database import (
    fetch_patients,
    insert_patients,
    fetch_existing_phones,
    fetch_tags_with_counts,
    fetch_tags_for_patients,
    create_tag,
    delete_tag,
    assign_tags_to_patients,
    fetch_patient_by_id,
    insert_patient,
    update_patient,
    delete_patients,
)
from components.patients import parse_import_file, build_preview, normalize_sv_phone

render_sidebar()

PAGE_SIZE = 25

# --- Session state initialization ---
st.session_state.setdefault("pacientes_mode", "list")
st.session_state.setdefault("current_page", 0)
st.session_state.setdefault("import_preview", None)
st.session_state.setdefault("import_file_processed", False)

# --- Page header row (D-03) ---
col_title, col_btn = st.columns([3, 1])
with col_title:
    st.title("Pacientes")
with col_btn:
    if st.session_state.pacientes_mode == "list":
        if st.button(
            "Importar pacientes",
            icon=":material/upload_file:",
            use_container_width=True,
        ):
            st.session_state.pacientes_mode = "import"
            st.session_state.import_preview = None
            st.session_state.import_file_processed = False
            st.rerun()

# =============================================================================
# IMPORT MODE (D-01, D-02, D-03)
# =============================================================================
if st.session_state.pacientes_mode == "import":
    uploaded_file = st.file_uploader(
        "Sube un archivo CSV o Excel con los datos de pacientes",
        type=["csv", "xlsx", "xls"],
        key="import_file",
    )

    # Process uploaded file once
    if uploaded_file is not None and not st.session_state.import_file_processed:
        try:
            df = parse_import_file(uploaded_file)
            existing_phones = fetch_existing_phones()
            preview_df = build_preview(df, existing_phones)
            st.session_state.import_preview = preview_df
            st.session_state.import_file_processed = True
        except ValueError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Error al procesar el archivo: {e}")

    # Show preview if available
    if st.session_state.import_preview is not None:
        preview_df = st.session_state.import_preview

        st.subheader("Vista previa de importacion")
        st.dataframe(preview_df, use_container_width=True, hide_index=True)

        nuevos = len(preview_df[preview_df["estado"] == "Nuevo"])
        duplicados = len(preview_df[preview_df["estado"] == "Duplicado"])
        errores = len(preview_df[preview_df["estado"] == "Error"])

        st.markdown(
            f"**{nuevos}** nuevos / **{duplicados}** duplicados ignorados / **{errores}** con errores"
        )

        col_import, col_discard = st.columns(2)
        with col_import:
            if st.button(
                f"Importar {nuevos} nuevos",
                disabled=(nuevos == 0),
                use_container_width=True,
            ):
                new_rows = preview_df[preview_df["estado"] == "Nuevo"]
                patients = []
                for _, row in new_rows.iterrows():
                    enfermedad_raw = row.get("enfermedad", "")
                    notes_val = "" if pd.isna(enfermedad_raw) else str(enfermedad_raw).strip()
                    patients.append(
                        {
                            "first_name": row["nombre"],
                            "last_name": row["apellido"],
                            "phone": str(row["telefono"]),
                            "phone_normalized": row["tel_normalizado"],
                            "notes": notes_val,
                        }
                    )
                with st.spinner("Importando pacientes..."):
                    try:
                        count = insert_patients(patients)
                        st.success(f"Se importaron {count} pacientes exitosamente.")
                    except Exception as e:
                        st.error(f"Error al importar: {e}")
                st.session_state.pacientes_mode = "list"
                st.session_state.import_preview = None
                st.session_state.import_file_processed = False
                st.rerun()

        with col_discard:
            if st.button("Descartar importacion", use_container_width=True):
                st.session_state.pacientes_mode = "list"
                st.session_state.import_preview = None
                st.session_state.import_file_processed = False
                st.rerun()

# =============================================================================
# LIST MODE (D-04, D-05, D-06, D-07, D-08)
# =============================================================================
elif st.session_state.pacientes_mode == "list":

    # --- Filter bar (D-04, D-07) ---
    col_search, col_tags, _col_spacer = st.columns([3, 2, 1])

    with col_search:
        search = st.text_input(
            "",
            placeholder="Buscar por nombre o telefono...",
            key="patient_search",
            label_visibility="collapsed",
        )

    # Fetch tags for filter and management
    try:
        tags = fetch_tags_with_counts()
    except Exception:
        tags = []
        st.error("Error al cargar etiquetas.")

    tag_options = {t["name"]: str(t["id"]) for t in tags}

    with col_tags:
        selected_tag_names = st.multiselect(
            "Filtrar por etiquetas",
            options=list(tag_options.keys()),
            key="tag_filter",
        )

    selected_tag_ids = [tag_options[name] for name in selected_tag_names]

    # --- Tag management expander (D-07, D-08) ---
    with st.expander("Nueva etiqueta"):
        tag_col_name, tag_col_color, tag_col_btn = st.columns([3, 1, 1])
        with tag_col_name:
            tag_name = st.text_input(
                "Nombre de etiqueta", max_chars=50, key="new_tag_name"
            )
        with tag_col_color:
            tag_color = st.color_picker("Color", value="#6366f1", key="new_tag_color")
        with tag_col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(
                "Crear etiqueta",
                disabled=not tag_name.strip() if tag_name else True,
                use_container_width=True,
            ):
                try:
                    create_tag(tag_name.strip(), tag_color)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al crear etiqueta: {e}")

    # Display existing tags with delete option
    if tags:
        tag_cols = st.columns(min(len(tags), 4))
        for idx, t in enumerate(tags):
            with tag_cols[idx % min(len(tags), 4)]:
                color_hex = t.get("color", "#6366f1")
                count = t.get("patient_count", 0)
                st.markdown(
                    f'<span style="color:{color_hex}; font-weight:bold;">{t["name"]}</span>'
                    f" ({count})",
                    unsafe_allow_html=True,
                )
                if count == 0:
                    if st.button(
                        "Eliminar",
                        key=f"del_tag_{t['id']}",
                        use_container_width=True,
                    ):
                        try:
                            delete_tag(str(t["id"]))
                            st.rerun()
                        except ValueError as e:
                            st.warning(str(e))
                        except Exception as e:
                            st.error(f"Error al eliminar: {e}")
                elif st.button(
                    "Eliminar",
                    key=f"del_tag_{t['id']}",
                    use_container_width=True,
                ):
                    st.warning(
                        f"Esta etiqueta esta asignada a {count} pacientes. "
                        "Elimina las asignaciones primero."
                    )

    st.divider()

    # --- Reset page on filter change ---
    _prev_search = st.session_state.get("_prev_search", "")
    _prev_tags = st.session_state.get("_prev_tags", [])
    if search != _prev_search or selected_tag_names != _prev_tags:
        st.session_state.current_page = 0
    st.session_state["_prev_search"] = search
    st.session_state["_prev_tags"] = selected_tag_names

    # --- Patient data table (D-04, D-05, D-06) ---
    try:
        patients, total = fetch_patients(
            search=search,
            tag_ids=selected_tag_ids if selected_tag_ids else None,
            limit=PAGE_SIZE,
            offset=st.session_state.current_page * PAGE_SIZE,
        )
    except Exception as e:
        patients, total = [], 0
        st.error(f"Error al cargar pacientes: {e}")

    if not patients and not search and not selected_tag_names:
        # Empty state -- no patients at all
        st.info("No hay pacientes registrados")
        st.markdown(
            "Importa tu primer archivo CSV o Excel para comenzar a gestionar "
            "tu base de pacientes."
        )
        if st.button("Importar pacientes", key="empty_import_cta"):
            st.session_state.pacientes_mode = "import"
            st.session_state.import_preview = None
            st.session_state.import_file_processed = False
            st.rerun()

    elif not patients:
        st.info("No se encontraron pacientes con ese criterio de busqueda.")

    else:
        # Build display DataFrame
        patient_ids = [str(p["id"]) for p in patients]

        try:
            tags_map = fetch_tags_for_patients(patient_ids)
        except Exception:
            tags_map = {}

        MONTH_ABBR = {
            1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
            7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic",
        }

        rows = []
        for p in patients:
            pid = str(p["id"])
            ptags = tags_map.get(pid, [])
            tag_names = ", ".join(t["name"] for t in ptags)

            created = p["created_at"]
            if hasattr(created, "strftime"):
                date_str = f"{created.day:02d} {MONTH_ABBR.get(created.month, '')} {created.year}"
            else:
                date_str = str(created)

            rows.append(
                {
                    "id": pid,
                    "Nombre": f'{p["first_name"]} {p["last_name"]}',
                    "Telefono": p["phone_normalized"],
                    "Notas": p.get("notes", "") or "",
                    "Etiquetas": tag_names,
                    "Fuente": p.get("source", ""),
                    "Registrado": date_str,
                }
            )

        display_df = pd.DataFrame(rows)
        visible_columns = ["Nombre", "Telefono", "Notas", "Etiquetas", "Fuente", "Registrado"]

        event = st.dataframe(
            display_df[visible_columns],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="multi-row",
            key="patient_table",
        )

        # --- Bulk action bar (D-06) ---
        if event and event.selection and event.selection.rows:
            selected_ids = [
                display_df.iloc[i]["id"] for i in event.selection.rows
            ]

            st.caption(f"{len(selected_ids)} pacientes seleccionados")

            bulk_col_tags, bulk_col_btn, bulk_col_delete = st.columns([3, 1, 1])
            with bulk_col_tags:
                tag_assign = st.multiselect(
                    "Etiquetas a asignar",
                    options=[t["name"] for t in tags],
                    key="assign_tags",
                )
            with bulk_col_btn:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button(
                    "Asignar etiquetas",
                    disabled=not tag_assign,
                    use_container_width=True,
                ):
                    assign_tag_ids = [
                        tag_options[name] for name in tag_assign
                    ]
                    try:
                        assign_tags_to_patients(selected_ids, assign_tag_ids)
                        st.success(
                            f"Etiquetas asignadas a {len(selected_ids)} pacientes."
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al asignar etiquetas: {e}")
            with bulk_col_delete:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button(
                    "Borrar seleccionados",
                    icon=":material/delete:",
                    type="secondary",
                    use_container_width=True,
                ):
                    st.session_state["confirm_bulk_delete"] = True
                    st.session_state["bulk_delete_ids"] = selected_ids

            # Bulk delete confirmation
            if st.session_state.get("confirm_bulk_delete"):
                bulk_ids = st.session_state.get("bulk_delete_ids", [])
                st.warning(
                    f"Estas a punto de borrar {len(bulk_ids)} pacientes. "
                    "Esta accion no se puede deshacer."
                )
                confirm_col, cancel_col = st.columns(2)
                with confirm_col:
                    if st.button("Confirmar borrado", type="primary", use_container_width=True):
                        try:
                            count = delete_patients(bulk_ids)
                            st.success(f"Se borraron {count} pacientes.")
                            st.session_state.pop("confirm_bulk_delete", None)
                            st.session_state.pop("bulk_delete_ids", None)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al borrar pacientes: {e}")
                with cancel_col:
                    if st.button("Cancelar", use_container_width=True):
                        st.session_state.pop("confirm_bulk_delete", None)
                        st.session_state.pop("bulk_delete_ids", None)
                        st.rerun()

            # --- Edit form for single selected patient ---
            if len(event.selection.rows) == 1:
                selected_row_idx = event.selection.rows[0]
                selected_patient_id = display_df.iloc[selected_row_idx]["id"]
                try:
                    patient_data = fetch_patient_by_id(selected_patient_id)
                except Exception:
                    patient_data = None

                if patient_data:
                    with st.expander(
                        f"Editar: {patient_data['first_name']} {patient_data['last_name']}",
                        expanded=True,
                    ):
                        with st.form("edit_patient_form"):
                            edit_col1, edit_col2 = st.columns(2)
                            with edit_col1:
                                edit_nombre = st.text_input(
                                    "Nombre *", value=patient_data.get("first_name", "")
                                )
                                edit_telefono = st.text_input(
                                    "Telefono *", value=patient_data.get("phone", "")
                                )
                                edit_notas = st.text_area(
                                    "Notas", value=patient_data.get("notes", "") or ""
                                )
                            with edit_col2:
                                edit_apellido = st.text_input(
                                    "Apellido *", value=patient_data.get("last_name", "")
                                )
                                edit_email = st.text_input(
                                    "Email", value=patient_data.get("email", "") or ""
                                )

                            edit_submit = st.form_submit_button(
                                "Guardar cambios", use_container_width=True
                            )

                        if edit_submit:
                            if not edit_nombre.strip() or not edit_apellido.strip() or not edit_telefono.strip():
                                st.error("Nombre, apellido y telefono son obligatorios.")
                            else:
                                phone_norm, phone_err = normalize_sv_phone(edit_telefono.strip())
                                if phone_err:
                                    st.error(f"Telefono invalido: {phone_err}")
                                else:
                                    try:
                                        update_patient(
                                            patient_id=selected_patient_id,
                                            first_name=edit_nombre.strip(),
                                            last_name=edit_apellido.strip(),
                                            phone=edit_telefono.strip(),
                                            phone_normalized=phone_norm,
                                            email=edit_email.strip(),
                                            notes=edit_notas.strip(),
                                        )
                                        st.success("Paciente actualizado exitosamente.")
                                        st.rerun()
                                    except Exception as e:
                                        if "uq_patients_phone_normalized" in str(e):
                                            st.error("Ya existe un paciente con ese numero de telefono.")
                                        else:
                                            st.error(f"Error al actualizar: {e}")

                        # Individual delete button
                        if st.button(
                            "Borrar paciente",
                            icon=":material/delete:",
                            type="secondary",
                            key="individual_delete",
                        ):
                            st.session_state["confirm_individual_delete"] = selected_patient_id

                        if st.session_state.get("confirm_individual_delete") == selected_patient_id:
                            st.warning("Esta accion no se puede deshacer.")
                            del_col1, del_col2 = st.columns(2)
                            with del_col1:
                                if st.button("Confirmar borrado", type="primary", key="confirm_ind_del", use_container_width=True):
                                    try:
                                        delete_patients([selected_patient_id])
                                        st.success("Paciente eliminado.")
                                        st.session_state.pop("confirm_individual_delete", None)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error al borrar: {e}")
                            with del_col2:
                                if st.button("Cancelar", key="cancel_ind_del", use_container_width=True):
                                    st.session_state.pop("confirm_individual_delete", None)
                                    st.rerun()

        # --- Create new patient form ---
        with st.expander("Nuevo paciente"):
            with st.form("create_patient_form"):
                create_col1, create_col2 = st.columns(2)
                with create_col1:
                    new_nombre = st.text_input("Nombre *", key="new_nombre")
                    new_telefono = st.text_input("Telefono *", key="new_telefono")
                    new_notas = st.text_area("Notas", key="new_notas")
                with create_col2:
                    new_apellido = st.text_input("Apellido *", key="new_apellido")
                    new_email = st.text_input("Email", key="new_email")
                    new_fuente = st.text_input("Fuente", value="manual", key="new_fuente")

                create_submit = st.form_submit_button(
                    "Crear paciente", use_container_width=True
                )

            if create_submit:
                if not new_nombre.strip() or not new_apellido.strip() or not new_telefono.strip():
                    st.error("Nombre, apellido y telefono son obligatorios.")
                else:
                    phone_norm, phone_err = normalize_sv_phone(new_telefono.strip())
                    if phone_err:
                        st.error(f"Telefono invalido: {phone_err}")
                    else:
                        try:
                            insert_patient(
                                first_name=new_nombre.strip(),
                                last_name=new_apellido.strip(),
                                phone=new_telefono.strip(),
                                phone_normalized=phone_norm,
                                email=new_email.strip(),
                                notes=new_notas.strip(),
                                source=new_fuente.strip() or "manual",
                            )
                            st.success("Paciente creado exitosamente.")
                            st.rerun()
                        except Exception as e:
                            if "uq_patients_phone_normalized" in str(e):
                                st.error("Ya existe un paciente con ese numero de telefono.")
                            else:
                                st.error(f"Error al crear paciente: {e}")

        # --- Pagination (D-05) ---
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        start = st.session_state.current_page * PAGE_SIZE + 1
        end = min(start + PAGE_SIZE - 1, total)

        col_prev, col_caption, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button(
                "Anterior",
                disabled=(st.session_state.current_page == 0),
                use_container_width=True,
            ):
                st.session_state.current_page -= 1
                st.rerun()
        with col_caption:
            st.caption(f"Mostrando {start}-{end} de {total} pacientes")
        with col_next:
            if st.button(
                "Siguiente",
                disabled=(st.session_state.current_page >= total_pages - 1),
                use_container_width=True,
            ):
                st.session_state.current_page += 1
                st.rerun()
