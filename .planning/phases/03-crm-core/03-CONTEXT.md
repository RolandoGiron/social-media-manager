# Phase 3: CRM Core - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

The admin can import patients from CSV/Excel, search and filter the patient list by name/phone/tag, create custom tags and assign them to patients in bulk, and create message templates with variable placeholders and a live preview. All interactions are in the Streamlit admin UI with direct PostgreSQL queries — no n8n involvement for CRUD in this phase.

Message sending (campaigns) is NOT in scope — that is Phase 5. This phase only delivers the data management layer that campaigns will consume.

</domain>

<decisions>
## Implementation Decisions

### CSV Import UX
- **D-01:** Show a preview table (first N rows with normalization applied + status column: ✓ Nuevo / ⚠ Duplicado / ✗ Error) before committing to the database. Summary row shows totals. Admin clicks "Importar X nuevos" to confirm, or "Cancelar" to discard.
- **D-02:** Duplicate phone numbers (matched on `phone_normalized`) are skipped silently — not imported, counted in the summary ("3 duplicados ignorados"). No row-by-row resolution UI.
- **D-03:** The CSV Import flow is accessible via an "Importar pacientes" button in the patient list page header — not a separate sidebar page. Import and list share the same Streamlit page context.

### Patient List + Search
- **D-04:** Streamlit `st.dataframe` table with search bar + tag multiselect filter above it. Layout: filters row at top, then the table below.
- **D-05:** Pagination at 25 patients per page using manual LIMIT/OFFSET queries against PostgreSQL.
- **D-06:** Tag assignment uses checkbox row selection + bulk action: admin selects one or more patients via row checkboxes, picks tags from a multiselect, and clicks "Asignar etiquetas". Efficient for batch operations.

### Tag Management
- **D-07:** Tags are created and managed inline within the patient list page — no dedicated sidebar page. A "Nueva etiqueta" expander (name + color picker) lives in the tag filter section of the patient list.
- **D-08:** Deleting a tag that is assigned to patients is blocked with a count message: "Esta etiqueta está asignada a N pacientes. Elimina las asignaciones primero." No cascade delete.

### Message Template Editor
- **D-09:** Live side-by-side preview: left column is the text area where admin types the template body; right column shows the rendered preview with sample values substituted in real time ({{nombre}} → "Ana", {{fecha}} → "15 de enero").
- **D-10:** Open variable system — any `{{variable}}` syntax is valid. No fixed whitelist enforced by the editor. Variables are stored in the `variables TEXT[]` column by extracting all `{{...}}` matches from the body at save time.
- **D-11:** Template category dropdown with options: general / promoción / recordatorio. Maps to the existing `category TEXT` column in `message_templates`.

### Streamlit Navigation Structure
- **D-12:** New sidebar pages for this phase: "Pacientes" (patient list + import + tag management) and "Plantillas" (template editor + template list). Both added to the `st.navigation` call in `app.py`.

### Claude's Discretion
- Exact color picker implementation (st.color_picker default is fine)
- Preview sample values for variables (hardcoded "Ana", "15 de enero", etc.)
- Column widths and table styling in st.dataframe
- Error message wording for invalid CSV format
- Phone normalization logic details (strip spaces, add +52 prefix if local MX format detected)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Database Schema
- `postgres/init/001_schema.sql` — Full schema: `patients`, `tags`, `patient_tags`, `message_templates` tables with indexes. `patients` has `phone_normalized` unique constraint and gin_trgm name search index. `message_templates` has `variables TEXT[]` and `category TEXT` columns.

### Requirements
- `.planning/REQUIREMENTS.md` §CRM — CRM-01, CRM-02, CRM-03 are the patient management requirements
- `.planning/REQUIREMENTS.md` §WA — WA-01 is the message template requirement (all 4 in scope for this phase)
- `.planning/ROADMAP.md` §Phase 3 — Success criteria (4 items) define done

### Existing Admin UI (extend, don't replace)
- `admin-ui/src/app.py` — Streamlit entrypoint with `st.navigation` — add new pages here
- `admin-ui/src/components/sidebar.py` — Shared sidebar pattern; new pages must call `render_sidebar()`
- `admin-ui/src/components/evolution_api.py` — DB connection pattern to follow for new DB helper

### Prior Phase Context
- `.planning/phases/02-whatsapp-core/02-CONTEXT.md` — Established Streamlit patterns (multipage, sidebar component, polling)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `admin-ui/src/components/sidebar.py`: `render_sidebar()` — every new page must call this at the top
- `admin-ui/src/app.py`: `st.navigation()` pattern — add new `st.Page()` entries for Pacientes and Plantillas pages
- `postgres/init/001_schema.sql`: `patients` table with `phone_normalized` unique constraint and `gin_trgm_ops` index on `(first_name || ' ' || last_name)` — use pg_trgm ILIKE for name search, exact match on `phone_normalized` for phone search

### Established Patterns
- Streamlit pages live in `admin-ui/src/pages/` — filename convention `N_PageName.py`
- Components (reusable helpers) live in `admin-ui/src/components/`
- Environment variables accessed via `os.environ.get()` — `DATABASE_URL` is available for DB connections
- No ORM — direct psycopg2/psycopg queries following the pattern in `evolution_api.py`

### Integration Points
- Phase 5 (Campaign Blast) will SELECT from `patients` JOIN `patient_tags` WHERE `tag_id IN (...)` — tag assignment in this phase must be correct for campaigns to work
- Phase 5 will SELECT from `message_templates` — template `variables TEXT[]` must be populated at save time
- `campaign_log.segment_tags UUID[]` references tag IDs created in this phase

</code_context>

<specifics>
## Specific Ideas

- Patient list page has an "Importar pacientes" CTA button in the page header that toggles the import flow inline (not a separate page)
- Preview table for CSV import shows a "Estado" column with color-coded badges: ✓ Nuevo (green), ⚠ Duplicado (yellow), ✗ Error (red)
- Tag chips in the patient list display with the color stored in `tags.color` (default `#6366f1`)
- Template preview substitutes fixed sample values: {{nombre}} → "Ana", {{fecha}} → "15 de enero de 2026", {{clinica}} → "Clínica Dermatológica"

</specifics>

<deferred>
## Deferred Ideas

- Opt-in/opt-out consent management per patient — v2 requirement (PRIV-01), explicitly out of scope for v1
- Patient detail/edit page (editing individual patient records after import) — not in Phase 3 success criteria; defer
- Template versioning or edit history — not required for MVP
- Bulk patient export to CSV — useful but not in Phase 3 requirements; defer

</deferred>

---

*Phase: 03-crm-core*
*Context gathered: 2026-04-01*
