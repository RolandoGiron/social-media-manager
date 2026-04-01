# Phase 3: CRM Core - Research

**Researched:** 2026-04-01
**Domain:** Streamlit CRUD UI + PostgreSQL patient management
**Confidence:** HIGH

## Summary

Phase 3 builds two new Streamlit pages (Pacientes, Plantillas) that perform direct PostgreSQL CRUD operations against an existing schema. The schema is already defined (`001_schema.sql`) with `patients`, `tags`, `patient_tags`, and `message_templates` tables -- no DDL work needed. The existing admin UI follows established patterns: multipage navigation via `st.navigation`, shared sidebar via `render_sidebar()`, environment-based DB config, and direct `psycopg2` queries (no ORM).

The core technical challenges are: (1) CSV/Excel parsing with phone normalization to +52 MX E.164 format, (2) duplicate detection against `phone_normalized` unique constraint, (3) paginated patient list with trigram search and tag filtering, (4) `st.dataframe` row selection for bulk tag assignment, and (5) live template preview with `{{variable}}` extraction via regex. All are well-served by Streamlit's native widgets and pandas for data processing.

**Primary recommendation:** Use `psycopg2.extras.execute_values()` for batch inserts, `pandas` for CSV/Excel parsing and preview transformation, and `st.dataframe(on_select="rerun", selection_mode="multi-row")` for row selection. Keep all DB logic in a new `components/database.py` helper module following the `evolution_api.py` pattern. No external libraries beyond what is already in `requirements.txt` are needed.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** CSV import shows preview table (first N rows with normalization + status column) before committing. Summary row with totals. Admin clicks "Importar X nuevos" to confirm.
- **D-02:** Duplicate phone numbers (matched on `phone_normalized`) are skipped silently -- counted in summary, no row-by-row resolution.
- **D-03:** CSV Import flow accessible via "Importar pacientes" button in patient list page header -- not a separate page.
- **D-04:** `st.dataframe` table with search bar + tag multiselect filter above it.
- **D-05:** Pagination at 25 patients per page using manual LIMIT/OFFSET queries.
- **D-06:** Tag assignment uses checkbox row selection + bulk action: select patients, pick tags, click "Asignar etiquetas".
- **D-07:** Tags created inline within patient list page -- "Nueva etiqueta" expander with name + color picker.
- **D-08:** Deleting a tag assigned to patients is blocked with count message. No cascade delete.
- **D-09:** Live side-by-side template preview: left column editor, right column rendered preview with sample values.
- **D-10:** Open variable system -- any `{{variable}}` syntax valid. Variables extracted from body at save time, stored in `variables TEXT[]`.
- **D-11:** Template category dropdown: general / promocion / recordatorio.
- **D-12:** New sidebar pages: "Pacientes" and "Plantillas" added to `st.navigation` in a new "CRM" group.

### Claude's Discretion
- Exact color picker implementation (st.color_picker default is fine)
- Preview sample values for variables (hardcoded "Ana", "15 de enero", etc.)
- Column widths and table styling in st.dataframe
- Error message wording for invalid CSV format
- Phone normalization logic details (strip spaces, add +52 prefix if local MX format detected)

### Deferred Ideas (OUT OF SCOPE)
- Opt-in/opt-out consent management per patient (PRIV-01, v2)
- Patient detail/edit page
- Template versioning or edit history
- Bulk patient export to CSV
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CRM-01 | Import patients from CSV/Excel with phone normalization (+52 MX) and duplicate detection | pandas read_csv/read_excel + phone normalization function + execute_values batch insert + UNIQUE constraint handling |
| CRM-02 | Paginated patient list with search by name/phone and filter by tag/segment | pg_trgm ILIKE search (index exists) + tag JOIN filter + manual LIMIT/OFFSET pagination |
| CRM-03 | Create custom tags and assign to patients for segmentation | Inline tag CRUD + st.dataframe multi-row selection + bulk INSERT into patient_tags |
| WA-01 | Create message templates with {{variable}} placeholders and live preview | Regex extraction `r'\{\{(\w+)\}\}'` + side-by-side st.columns layout + real-time substitution |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **No ORM** -- direct psycopg2 queries (established pattern from Phase 2)
- **Streamlit 1.35+** for admin UI (currently 1.55.0 installed locally)
- **Python 3.11** in Docker image (3.13 installed locally -- tests will work in both)
- **PostgreSQL 16** as sole persistence
- **All services in Docker Compose** -- Streamlit runs as separate Docker service
- **Streamlit behind Caddy basic auth** in production
- **DATABASE_URL** env var available for DB connections
- **Pages in `admin-ui/src/pages/`**, components in `admin-ui/src/components/`
- **Every page must call `render_sidebar()`**

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Streamlit | 1.55.0 (installed) | Admin UI framework | Already in use; `st.dataframe` with selection, `st.file_uploader`, `st.navigation` cover all UI needs |
| psycopg2-binary | latest (installed) | PostgreSQL driver | Already in requirements.txt; direct SQL per project convention |
| pandas | 2.3.3 (installed) | CSV/Excel parsing and data transformation | Already in requirements.txt; `read_csv`, `read_excel` handle all import formats |
| openpyxl | installed | Excel (.xlsx) file reading engine for pandas | Already in requirements.txt; required for `pd.read_excel()` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| psycopg2.extras | (bundled) | `execute_values()` for batch INSERT | Use for CSV import -- 10x faster than executemany |
| re (stdlib) | -- | Regex for `{{variable}}` extraction | Use `r'\{\{(\w+)\}\}'` pattern at template save time |
| io (stdlib) | -- | BytesIO for file_uploader to pandas bridge | `pd.read_csv(io.BytesIO(uploaded_file.read()))` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| psycopg2 | SQLAlchemy | Project explicitly avoids ORMs; psycopg2 is the established pattern |
| Manual phone normalization | phonenumbers library | phonenumbers is overkill for single-country +52 normalization; simple string operations suffice |
| Manual pagination | streamlit-aggrid | Adds external dependency; `st.dataframe` with manual LIMIT/OFFSET meets requirements |

**Installation:** No new packages needed -- all dependencies are already in `admin-ui/requirements.txt`.

## Architecture Patterns

### Recommended Project Structure
```
admin-ui/src/
├── app.py                      # Add Pacientes + Plantillas to st.navigation
├── components/
│   ├── sidebar.py              # Existing -- no changes needed
│   ├── evolution_api.py        # Existing -- reference pattern for DB helper
│   └── database.py             # NEW: DB connection + query helpers
├── pages/
│   ├── 1_Dashboard.py          # Existing
│   ├── 2_WhatsApp.py           # Existing
│   ├── 3_Pacientes.py          # NEW: Patient list + import + tag management
│   └── 4_Plantillas.py         # NEW: Template editor + list
└── tests/
    ├── conftest.py             # Extend with DB fixtures
    ├── test_database.py        # NEW: DB helper unit tests
    ├── test_patients.py        # NEW: Phone normalization + import logic
    └── test_templates.py       # NEW: Variable extraction tests
```

### Pattern 1: Database Helper Module
**What:** Centralized DB connection and query functions in `components/database.py`
**When to use:** Every DB operation across both new pages
**Example:**
```python
# Source: follows evolution_api.py pattern
import os
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor

def get_connection():
    """Get a PostgreSQL connection using DATABASE_URL env var."""
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

def fetch_patients(search: str = "", tag_ids: list = None, limit: int = 25, offset: int = 0):
    """Fetch paginated patients with optional search and tag filter."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            conditions = []
            params = []

            if search:
                conditions.append("(first_name || ' ' || last_name) ILIKE %s OR phone_normalized ILIKE %s")
                params.extend([f"%{search}%", f"%{search}%"])

            if tag_ids:
                conditions.append("""
                    id IN (SELECT patient_id FROM patient_tags WHERE tag_id = ANY(%s))
                """)
                params.append(tag_ids)

            where = "WHERE " + " AND ".join(conditions) if conditions else ""

            # Count total
            cur.execute(f"SELECT COUNT(*) FROM patients {where}", params)
            total = cur.fetchone()["count"]

            # Fetch page
            cur.execute(f"""
                SELECT p.id, p.first_name, p.last_name, p.phone_normalized,
                       p.source, p.created_at
                FROM patients p {where}
                ORDER BY p.created_at DESC
                LIMIT %s OFFSET %s
            """, params + [limit, offset])
            rows = cur.fetchall()

            return rows, total
    finally:
        conn.close()
```

### Pattern 2: Phone Normalization Function
**What:** Pure function that normalizes Mexican phone numbers to +52 E.164 format
**When to use:** During CSV import preview and before INSERT
**Example:**
```python
import re

def normalize_mx_phone(raw: str) -> tuple[str, str | None]:
    """Normalize a Mexican phone number to E.164 format (+52XXXXXXXXXX).

    Returns (normalized, error_message). error_message is None if valid.

    Mexico format: +52 followed by 10 digits (no "1" prefix since Aug 2020).
    """
    # Strip all non-digit characters
    digits = re.sub(r'\D', '', raw)

    # Remove country code if present
    if digits.startswith("52") and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith("521") and len(digits) == 13:
        # Old format with "1" -- strip it
        digits = digits[3:]

    if len(digits) != 10:
        return "", f"Numero invalido: {raw} ({len(digits)} digitos, se esperan 10)"

    return f"+52{digits}", None
```

### Pattern 3: Template Variable Extraction
**What:** Regex-based extraction of `{{variable}}` placeholders from template body
**When to use:** At save time to populate `variables TEXT[]` column, and at preview time for live substitution
**Example:**
```python
import re

VARIABLE_PATTERN = re.compile(r'\{\{(\w+)\}\}')

SAMPLE_VALUES = {
    "nombre": "Ana",
    "fecha": "15 de enero de 2026",
    "clinica": "Clinica Dermatologica",
    "telefono": "+52 55 1234 5678",
    "hora": "10:00 AM",
}

def extract_variables(body: str) -> list[str]:
    """Extract unique variable names from template body."""
    return list(dict.fromkeys(VARIABLE_PATTERN.findall(body)))

def render_preview(body: str) -> str:
    """Substitute variables with sample values for preview."""
    def replacer(match):
        var_name = match.group(1)
        return SAMPLE_VALUES.get(var_name, f"[{var_name}]")
    return VARIABLE_PATTERN.sub(replacer, body)
```

### Pattern 4: CSV Import with Preview
**What:** Two-phase import: parse + preview, then commit on confirmation
**When to use:** The entire CSV/Excel import flow
**Example:**
```python
import pandas as pd
import io

def parse_import_file(uploaded_file) -> pd.DataFrame:
    """Parse CSV or Excel file into a DataFrame."""
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(uploaded_file)
    else:
        raise ValueError("Formato no soportado")

    # Normalize column names to lowercase
    df.columns = [c.strip().lower() for c in df.columns]

    # Validate required columns
    required = {"nombre", "apellido", "telefono"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Columnas faltantes: {', '.join(missing)}")

    return df

def build_preview(df: pd.DataFrame, existing_phones: set[str]) -> pd.DataFrame:
    """Add normalization and status columns for preview."""
    preview = df.copy()
    normalized = []
    statuses = []

    for _, row in preview.iterrows():
        phone_norm, error = normalize_mx_phone(str(row["telefono"]))
        normalized.append(phone_norm)
        if error:
            statuses.append("Error")
        elif phone_norm in existing_phones:
            statuses.append("Duplicado")
        else:
            statuses.append("Nuevo")

    preview["tel_normalizado"] = normalized
    preview["estado"] = statuses
    return preview
```

### Pattern 5: Streamlit Page State Management
**What:** Using `st.session_state` to manage page modes (list vs import, list vs editor)
**When to use:** Both Pacientes and Plantillas pages need mode switching
**Example:**
```python
# In 3_Pacientes.py
if "pacientes_mode" not in st.session_state:
    st.session_state.pacientes_mode = "list"  # "list" or "import"
if "current_page" not in st.session_state:
    st.session_state.current_page = 0
```

### Anti-Patterns to Avoid
- **Loading full dataset into st.dataframe:** Always use SQL LIMIT/OFFSET -- never `SELECT * FROM patients` into a DataFrame. Even 1000 patients will cause performance issues with Streamlit's rerun model.
- **Using `cursor.executemany()` for batch inserts:** Use `execute_values()` from `psycopg2.extras` instead -- 10x faster for 100+ rows.
- **Storing DataFrame in session_state:** DataFrames are large; store query parameters (page, search, filters) in session_state and re-query. Only store the import preview DataFrame temporarily.
- **Not closing DB connections:** Always use try/finally or context managers to close connections. Streamlit reruns the entire script on every interaction.
- **Forgetting `render_sidebar()` call:** Every new page MUST call `render_sidebar()` at the top per established pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSV/Excel parsing | Custom file parser | `pandas.read_csv()` / `pandas.read_excel()` | Handles encoding, delimiters, malformed rows, Excel formats |
| Phone normalization | Full international phone library | Simple regex function for MX-only | We only need +52 format; phonenumbers library is overkill |
| Batch INSERT | Loop of individual INSERTs | `psycopg2.extras.execute_values()` | Single round-trip for 100+ rows |
| Pagination UI | Custom HTML/JS | `st.button("Anterior")` / `st.button("Siguiente")` + session_state | Streamlit-native, no component dependencies |
| Duplicate detection | Application-side dedup | PostgreSQL UNIQUE constraint on `phone_normalized` | DB enforces correctness; preview checks `existing_phones` set |

**Key insight:** This phase is pure CRUD with no external API integrations. Every feature can be built with Streamlit native widgets + psycopg2 + pandas. No external services, no n8n workflows, no Evolution API calls needed.

## Common Pitfalls

### Pitfall 1: Streamlit Rerun Destroys State
**What goes wrong:** Every widget interaction causes a full script rerun. File upload data, preview DataFrames, and selection state disappear unless stored in `st.session_state`.
**Why it happens:** Streamlit's execution model reruns top-to-bottom on every interaction.
**How to avoid:** Store import preview DataFrame in `st.session_state["import_preview"]` after parsing. Store current page number, search query, and selected tags in session_state. Clear state explicitly on mode transitions.
**Warning signs:** Data disappears after clicking a button; uploaded file seems to reset.

### Pitfall 2: st.dataframe Selection Returns Row Indices, Not IDs
**What goes wrong:** `event.selection.rows` returns positional indices (0, 1, 2...) into the displayed DataFrame, not database UUIDs.
**Why it happens:** Streamlit tracks selection by display position.
**How to avoid:** Include the patient UUID in the DataFrame (can be hidden or visible), then map selected indices back to UUIDs: `selected_ids = [df.iloc[i]["id"] for i in event.selection.rows]`.
**Warning signs:** Wrong patients get tagged; tags applied to different patients than selected.

### Pitfall 3: Mexican Phone Number "+521" Legacy Format
**What goes wrong:** Some CSV files contain phone numbers with the old "+521" prefix (used before August 2020) or just 10 digits without country code.
**Why it happens:** Clinics have patient databases accumulated over years with inconsistent formatting.
**How to avoid:** The normalization function must handle all variants: `+52XXXXXXXXXX`, `+521XXXXXXXXXX` (strip the 1), `52XXXXXXXXXX`, `XXXXXXXXXX` (add +52), and numbers with spaces/dashes/parentheses.
**Warning signs:** Valid numbers rejected; duplicates not detected because normalization is inconsistent.

### Pitfall 4: Connection Leak on Streamlit Rerun
**What goes wrong:** Each rerun opens a new DB connection. If not closed, connections accumulate until PostgreSQL hits `max_connections` (set to 50 per CLAUDE.md).
**Why it happens:** Streamlit reruns the script on every interaction; connections opened at module level persist.
**How to avoid:** Always use try/finally to close connections. Consider `@st.cache_resource` for a connection pool if performance requires it, but start simple with per-request connections.
**Warning signs:** "too many connections" errors after extended use.

### Pitfall 5: pg_trgm Search Requires Minimum Query Length
**What goes wrong:** Very short search queries (1-2 chars) with trigram ILIKE return too many results or perform poorly.
**Why it happens:** pg_trgm works best with 3+ character queries.
**How to avoid:** Only execute search query when input is 3+ characters. For shorter input, show full paginated list. For phone search (numeric input), use exact prefix match on `phone_normalized` instead of trigram.
**Warning signs:** Search feels slow on short queries; irrelevant results returned.

### Pitfall 6: Bulk Tag Assignment INSERT Conflicts
**What goes wrong:** If a patient already has a tag and the admin assigns it again, the INSERT into `patient_tags` fails on the PRIMARY KEY constraint.
**Why it happens:** `patient_tags` has `PRIMARY KEY (patient_id, tag_id)`.
**How to avoid:** Use `INSERT INTO patient_tags ... ON CONFLICT (patient_id, tag_id) DO NOTHING`. This silently skips existing assignments.
**Warning signs:** Error messages when re-assigning tags to patients who already have them.

## Code Examples

### Database Helper -- Batch Insert Patients
```python
# Source: psycopg2 docs + project convention
from psycopg2.extras import execute_values

def insert_patients(patients: list[dict]) -> int:
    """Batch insert patients. Returns count of inserted rows.

    patients: list of dicts with keys: first_name, last_name, phone, phone_normalized, source
    Skips duplicates via ON CONFLICT.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO patients (first_name, last_name, phone, phone_normalized, source)
                VALUES %s
                ON CONFLICT (phone_normalized) DO NOTHING
            """
            values = [
                (p["first_name"], p["last_name"], p["phone"], p["phone_normalized"], "csv_import")
                for p in patients
            ]
            execute_values(cur, sql, values)
            inserted = cur.rowcount
        conn.commit()
        return inserted
    finally:
        conn.close()
```

### Fetch Tags with Patient Count (for D-08 delete blocking)
```python
def fetch_tags_with_counts() -> list[dict]:
    """Fetch all tags with the count of assigned patients."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT t.id, t.name, t.color, t.created_at,
                       COUNT(pt.patient_id) AS patient_count
                FROM tags t
                LEFT JOIN patient_tags pt ON t.id = pt.tag_id
                GROUP BY t.id
                ORDER BY t.name
            """)
            return cur.fetchall()
    finally:
        conn.close()
```

### st.dataframe with Row Selection
```python
# Source: Streamlit docs - st.dataframe on_select parameter
import streamlit as st
import pandas as pd

# Display table with selection enabled
event = st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="multi-row",
    key="patient_table",
)

# Access selected rows
if event.selection.rows:
    selected_indices = event.selection.rows
    selected_ids = [display_df.iloc[i]["id"] for i in selected_indices]
    st.caption(f"{len(selected_ids)} pacientes seleccionados")
```

### Pagination Controls
```python
# Manual pagination with LIMIT/OFFSET
PAGE_SIZE = 25

col1, col2, col3 = st.columns([1, 3, 1])
with col1:
    if st.button("Anterior", disabled=st.session_state.current_page == 0):
        st.session_state.current_page -= 1
        st.rerun()
with col3:
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    if st.button("Siguiente", disabled=st.session_state.current_page >= total_pages - 1):
        st.session_state.current_page += 1
        st.rerun()
with col2:
    start = st.session_state.current_page * PAGE_SIZE + 1
    end = min(start + PAGE_SIZE - 1, total)
    st.caption(f"Mostrando {start}-{end} de {total} pacientes")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `st.dataframe` read-only | `st.dataframe(on_select="rerun")` with selection | Streamlit 1.35+ | Enables row selection without st.data_editor |
| `cursor.executemany()` | `psycopg2.extras.execute_values()` | Long-standing recommendation | 10x faster batch inserts |
| MX phone +521 prefix | +52 (10 digits, no "1") | August 2020 | Must strip legacy "1" prefix in normalization |
| `st.experimental_rerun()` | `st.rerun()` | Streamlit 1.27+ | Use `st.rerun()` for page transitions |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.3 |
| Config file | none (runs from `admin-ui/src/`) |
| Quick run command | `cd /home/rolando/Desarrollo/social-media-manager/admin-ui/src && python -m pytest tests/ -x -q` |
| Full suite command | `cd /home/rolando/Desarrollo/social-media-manager/admin-ui/src && python -m pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CRM-01 | Phone normalization (all MX variants) | unit | `pytest tests/test_patients.py::test_normalize_mx_phone -x` | Wave 0 |
| CRM-01 | CSV parsing (valid, invalid, missing columns) | unit | `pytest tests/test_patients.py::test_parse_import_file -x` | Wave 0 |
| CRM-01 | Preview build (nuevo/duplicado/error classification) | unit | `pytest tests/test_patients.py::test_build_preview -x` | Wave 0 |
| CRM-01 | Batch insert with ON CONFLICT | unit (mocked DB) | `pytest tests/test_database.py::test_insert_patients -x` | Wave 0 |
| CRM-02 | Search query builder (name + phone + tags) | unit | `pytest tests/test_database.py::test_fetch_patients -x` | Wave 0 |
| CRM-02 | Pagination offset calculation | unit | `pytest tests/test_patients.py::test_pagination -x` | Wave 0 |
| CRM-03 | Tag CRUD (create, fetch with counts, delete blocking) | unit (mocked DB) | `pytest tests/test_database.py::test_tag_operations -x` | Wave 0 |
| CRM-03 | Bulk tag assignment with ON CONFLICT DO NOTHING | unit (mocked DB) | `pytest tests/test_database.py::test_assign_tags -x` | Wave 0 |
| WA-01 | Variable extraction regex | unit | `pytest tests/test_templates.py::test_extract_variables -x` | Wave 0 |
| WA-01 | Preview rendering with sample values | unit | `pytest tests/test_templates.py::test_render_preview -x` | Wave 0 |
| WA-01 | Template save (name + body validation) | unit | `pytest tests/test_templates.py::test_template_validation -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd admin-ui/src && python -m pytest tests/ -x -q`
- **Per wave merge:** `cd admin-ui/src && python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_database.py` -- covers DB helper functions (connection, queries, batch insert)
- [ ] `tests/test_patients.py` -- covers phone normalization, CSV parsing, preview build, pagination
- [ ] `tests/test_templates.py` -- covers variable extraction, preview rendering, validation
- [ ] `tests/conftest.py` -- extend with mock DB connection fixture

## Open Questions

1. **Column name mapping flexibility in CSV**
   - What we know: Decision requires columns `nombre`, `apellido`, `telefono`
   - What's unclear: Should the system also accept common English alternatives (`name`, `last_name`, `phone`) or other Spanish variants (`tel`, `celular`)?
   - Recommendation: Start strict with the three required column names. Add a column mapping UI in a future iteration if users complain about CSV format requirements.

2. **Connection pooling**
   - What we know: Streamlit reruns create a new connection per interaction. PostgreSQL `max_connections=50`.
   - What's unclear: Under normal single-admin use, will per-request connections cause issues?
   - Recommendation: Start with simple per-request connections (open/close). If connection errors appear, add `@st.cache_resource` connection pool. At single-tenant scale with one admin, connection pressure will be minimal.

## Sources

### Primary (HIGH confidence)
- [Streamlit st.dataframe docs](https://docs.streamlit.io/develop/api-reference/data/st.dataframe) -- on_select, selection_mode API verified
- [Streamlit st.navigation docs](https://docs.streamlit.io/develop/api-reference/navigation/st.navigation) -- grouped dictionary syntax verified
- [psycopg2.extras docs](https://www.psycopg.org/docs/extras.html) -- execute_values() for batch inserts
- `postgres/init/001_schema.sql` -- schema verified: patients, tags, patient_tags, message_templates tables with all required columns and indexes
- `admin-ui/src/app.py` + `components/` -- existing patterns verified in codebase

### Secondary (MEDIUM confidence)
- [Mexico phone format guide](https://www.sent.dm/resources/mx) -- +52 E.164 format, 10 digits, no "1" prefix since 2020
- [Streamlit row selection tutorial](https://docs.streamlit.io/develop/tutorials/elements/dataframe-row-selections) -- event.selection.rows returns list[int]

### Tertiary (LOW confidence)
- None -- all findings verified with primary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and verified in project
- Architecture: HIGH -- extends established patterns from Phase 2 codebase
- Pitfalls: HIGH -- based on Streamlit execution model (documented) and PostgreSQL constraints (schema verified)

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (stable domain, no fast-moving dependencies)
