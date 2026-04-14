# Phase 6: Social Media Publishing - Research

**Researched:** 2026-04-13
**Domain:** Social publishing (Instagram Graph API + Facebook Pages API) + Streamlit file upload + n8n scheduler/webhook workflow
**Confidence:** HIGH for integration patterns (existing codebase), MEDIUM for Meta Graph API specifics (verified against Meta docs, but deployment is gated by App Review and validated via `MOCK_SOCIAL=true`)

## Summary

Phase 6 adds a social publishing layer on top of the existing Phase 5 campaign infrastructure. The work is almost entirely **wiring and extension** — the database table (`social_posts`) already exists from Phase 1, the 3-step session-state pattern already exists in `7_Campañas.py`, the webhook+Postgres n8n pattern already exists in `campaign-blast.json`, and a Streamlit page template already exists in `3_Pacientes.py`.

The only genuinely new pieces are (1) a `/opt/clinic-crm/uploads/` shared volume between the Streamlit and n8n containers, (2) a `social-publish` n8n workflow that calls Meta Graph API (or logs when `MOCK_SOCIAL=true`), (3) a cron-driven dispatcher that scans `social_posts WHERE status='scheduled' AND scheduled_at <= now()`, and (4) a new `8_Publicaciones.py` page plus Step 3 extension to `7_Campañas.py`.

**Primary recommendation:** Treat this phase as an integration phase, not a research phase. Reuse `campaign-blast.json` as the scaffold for `social-publish.json`. Reuse `7_Campañas.py` session-state pattern verbatim. Pin Meta Graph API to `v21.0` in n8n HTTP nodes. Ship with `MOCK_SOCIAL=true` until App Review lands; the DB/UI/workflow paths must all exercise identically in mock mode.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Meta API — Estrategia mientras App Review está pendiente**
- **D-01:** Construir con Meta Graph API real (endpoints de Instagram Graph API y Facebook Pages API vía n8n HTTP nodes). No depender de Buffer ni de otra plataforma intermediaria.
- **D-02:** Variable de entorno `MOCK_SOCIAL=true/false` en el workflow de n8n de publicación. Cuando `MOCK_SOCIAL=true`, el nodo de publicación logea la acción en lugar de llamar a Meta Graph API. Cuando llegue la aprobación de Meta App Review, se cambia la env var y el workflow funciona sin ningún cambio de código.
- **D-03:** La nueva tabla `scheduled_posts` almacena el estado de cada publicación. El admin puede verificar el estado desde la UI aunque la publicación real esté mockeada.

**Flujo Campaña Unificada — Extensión de 7_Campañas.py**
- **D-04:** El flujo unificado vive en 7_Campañas.py (extender, no crear nueva página). Después del flujo existente de Fase 5, se agrega un **Paso 3 opcional**: checkbox "Publicar en redes sociales también".
- **D-05:** Si el checkbox está activado, aparece el composer: caption textarea, file_uploader para imagen, fecha/hora. Caption puede diferir del mensaje WA.
- **D-06:** Botón "Lanzar campaña" dispara ambos canales si checkbox activo: (a) campaign_log + webhook WA blast, y (b) scheduled_posts + webhook social publishing.
- **D-07:** Si checkbox desactivado, comportamiento idéntico a Fase 5 — sin regresión.

**Página Standalone — 8_Publicaciones.py**
- **D-08:** Nueva página 8_Publicaciones.py para SOCIAL-01 y SOCIAL-03: lista de publicaciones programadas con estado + composer standalone.
- **D-09:** Lista muestra: Caption (truncado), Plataforma, Fecha programada, Estado, Acciones. Ordenada por `scheduled_at ASC`.
- **D-10:** Composer standalone usa mismo pattern que Paso 3 de 7_Campañas.py.
- **D-11:** El flujo unificado de 7_Campañas.py también escribe en scheduled_posts — visible en 8_Publicaciones.py.

**Imágenes — Upload y Storage**
- **D-12:** Admin sube imagen vía `st.file_uploader` (JPG, PNG, WEBP). Imagen se guarda en `/opt/clinic-crm/uploads/` (volumen Docker compartido).
- **D-13:** Filename: `{uuid4}.{ext}`. Ruta relativa se guarda en `scheduled_posts.image_path`. n8n lee desde ruta montada.
- **D-14:** Volumen `uploads` declarado en docker-compose.yml y montado en `streamlit` y `n8n`. Caddy sirve `/uploads/` como static si Meta API requiere URL pública.

**n8n — Workflow de Publicación Social**
- **D-15:** Nuevo workflow `social-publish.json`. Disparado por webhook POST con `post_id`. Lee scheduled_posts, construye payload, llama Meta Graph API, actualiza status a `published` o `error`.
- **D-16:** Cron trigger separado `social-scheduler.json` (o Schedule Trigger node integrado) corre cada minuto, busca `status='pending' AND scheduled_at <= now()`, dispara publicación.
- **D-17:** Cuando `MOCK_SOCIAL=true`, el nodo de publicación logea y retorna `{success: true}`. Resto del workflow corre igual.

### Claude's Discretion
- Diseño visual del Paso 3 en 7_Campañas.py (posición del checkbox, expansión/colapso)
- Selector de plataforma en el composer (Instagram y/o Facebook — checkbox múltiple o multiselect)
- Exacto schema de `scheduled_posts` (campos específicos: caption, image_path, platforms[], scheduled_at, status, meta_post_id, error_message, created_at)
- Manejo de errores en n8n cuando Meta Graph API falla (retry automático 1 vez, luego marcar como error)
- Preview de imagen en el composer (st.image antes de guardar)

### Deferred Ideas (OUT OF SCOPE)
- TikTok y X (Twitter) autoposting
- Preview del post como se vería en Instagram (simulación) — v2
- Métricas de engagement (likes, comentarios) — Phase 7 Dashboard
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SOCIAL-01 | Administrador puede programar publicación en Instagram y Facebook con imagen y caption para fecha/hora específica | `8_Publicaciones.py` composer (D-08, D-10) + existing `social_posts` table + Meta Graph API endpoints (Instagram `/ig-user-id/media` + `/media_publish`; Facebook `/page-id/photos`) called from `social-publish.json` |
| SOCIAL-02 | Sistema dispara trigger unificado WA + social desde una sola acción | Step 3 extension of `7_Campañas.py` (D-04 to D-07) — single "Lanzar campaña" button triggers both `campaign-blast` webhook AND `social-publish` webhook in one `st.button` click handler |
| SOCIAL-03 | Administrador puede ver estado de cada publicación programada (pendiente, publicado, error) | `8_Publicaciones.py` list section (D-09) reads `social_posts` ordered by `scheduled_at ASC`; n8n workflow writes `status` transitions |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Actionable directives that constrain research and planning:

1. **Self-hosted n8n only** — no n8n Cloud; workflows live in `n8n/workflows/*.json` committed to git.
2. **Single VPS / Docker Compose** — all services share one compose stack; no separate VPS for this phase.
3. **PostgreSQL is the single persistence layer** — no new databases; Phase 6 must extend existing schema.
4. **Privacy: patient data encrypted at rest** — uploads volume holds post images (marketing content, not PHI), so no extra encryption layer required, but the volume must NOT be a bind into patient-identifying data.
5. **Docker Compose patch must add the `uploads` volume** to both `streamlit` and `n8n` services.
6. **Python inside Streamlit container only** — no pip installs on the host; any new deps go in `admin-ui/requirements.txt`.
7. **n8n workflows committed as JSON** — every workflow change is a git artifact.
8. **Start work through a GSD command** — Edit/Write/workflow changes must flow through `/gsd:execute-phase` for Phase 6 tasks.
9. **24/7 availability** — scheduled posts fire while the admin sleeps; the scheduler must run continuously, not on admin session.
10. **Scope for solo developer** — reuse existing patterns; no new frameworks.

## Standard Stack

### Core (already pinned — do not change)

| Library / Service | Version | Purpose | Why Standard |
|-------------------|---------|---------|--------------|
| n8n | latest (image `n8nio/n8n:latest`) | Workflow runtime for `social-publish.json` and `social-scheduler.json` | Already deployed; native Postgres + Schedule Trigger + HTTP Request nodes cover the entire publish flow with zero custom code [VERIFIED: docker-compose.yml] |
| PostgreSQL | 16-alpine | `social_posts` table persistence | Already deployed; `social_posts` table already exists [VERIFIED: postgres/init/001_schema.sql lines 174-192] |
| Streamlit | ≥1.35 (in admin-ui/requirements.txt) | Admin UI for `8_Publicaciones.py` and Step 3 of `7_Campañas.py` | Already used for all admin pages; `st.file_uploader`, `st.image`, `st.date_input`, `st.time_input` are stdlib widgets [VERIFIED: Phase 5 UI-SPEC inherited] |
| psycopg2 | binary (existing) | DB access from Streamlit | Already used in `admin-ui/src/components/database.py` [VERIFIED: database.py] |
| requests | existing | POST to n8n webhook | Already used in `7_Campañas.py::_trigger_n8n_webhook` [VERIFIED: 7_Campañas.py line 40-47] |

### External APIs

| API | Version | Purpose | Notes |
|-----|---------|---------|-------|
| Instagram Graph API | **v21.0** | Create media container + publish | Called from n8n HTTP Request nodes. Two-step flow: POST `/{ig-user-id}/media` → receive `creation_id` → POST `/{ig-user-id}/media_publish` with `creation_id` [CITED: https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media_publish/] |
| Facebook Graph API (Pages) | **v21.0** | Publish photo to Page | Single-step: POST `/{page-id}/photos` with `url` or `source` + `caption` [CITED: https://developers.facebook.com/docs/graph-api/reference/page/photos/] |

**Pin Meta Graph API version explicitly** in n8n HTTP node URLs (e.g., `https://graph.facebook.com/v21.0/...`). Meta releases quarterly; do not use the unversioned `/v{latest}/` shortcut — it causes silent behavior drift.

### No New Python Packages

`8_Publicaciones.py` and the Step 3 extension introduce **zero new pip dependencies**. Everything uses existing `streamlit` + `psycopg2` + `requests` already pinned from Phase 1. This is a hard requirement per UI-SPEC Registry Safety section.

### Alternatives Considered

| Instead of | Could Use | Tradeoff | Verdict |
|------------|-----------|----------|---------|
| n8n cron + manual Meta API | Buffer / Make.com | External dependency, ongoing cost, vendor lock-in | Rejected by D-01 |
| Instagram API `publish_time` (Meta-native scheduling) | n8n cron scanner | Meta supports `publish_time` on container creation but requires IG Business accounts + has documented quirks; cron pattern is already proven in the codebase and works identically under `MOCK_SOCIAL=true` | Use n8n cron per D-16 |
| Presigned S3 URLs | Local volume + Caddy static | S3 adds infra; local volume is the existing pattern | Use local volume per D-12/D-14 |
| Separate table `scheduled_posts` | Use existing `social_posts` table | **Schema already has `social_posts` from Phase 1** — creating a second table duplicates the concept | **Use `social_posts`** (see Schema Alignment below) |

## Schema Alignment — CRITICAL

**The CONTEXT.md references a table named `scheduled_posts` that does not exist. The schema already contains `social_posts` from Phase 1.**

[VERIFIED: postgres/init/001_schema.sql lines 174-192]

```sql
CREATE TABLE social_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    caption TEXT NOT NULL,
    image_url TEXT,                              -- NOTE: column name is image_url, not image_path
    platforms TEXT[] NOT NULL DEFAULT '{}',
    scheduled_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'scheduled', 'publishing', 'published', 'failed')),
    platform_post_ids JSONB DEFAULT '{}',
    campaign_id UUID REFERENCES campaign_log(id) ON DELETE SET NULL,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_social_posts_status ON social_posts (status);
CREATE INDEX idx_social_posts_scheduled_at ON social_posts (scheduled_at);
```

**Plan implications:**
1. **Rename all `scheduled_posts` references to `social_posts`** in the plan. CONTEXT.md was drafted before the schema was verified.
2. **Status enum is already defined**: `draft / scheduled / publishing / published / failed` — use these exact values, NOT the `pending / published / error` enum from CONTEXT.md D-03 and UI-SPEC.
   - Map UI-SPEC "Pendiente" label → DB value `scheduled`
   - Map UI-SPEC "Publicado" label → DB value `published`
   - Map UI-SPEC "Error" label → DB value `failed`
   - `draft` and `publishing` are internal states (not shown in admin list, or shown as "Pendiente")
3. **Column name mismatch**: CONTEXT.md says `image_path` (D-13), schema says `image_url`. **Use `image_url`** (existing column). Store the local relative path `uploads/{uuid}.jpg` in `image_url` — when Meta API requires a public URL, n8n prepends `https://${DOMAIN}${image_url}` via Caddy static serving.
4. **Foreign key `campaign_id` already exists** in `social_posts` — use it for SOCIAL-02 linkage (the unified campaign flow writes `campaign_id = <new_campaign_log_id>` when Step 3 is active). This is cleaner than a separate join table.
5. **`platform_post_ids JSONB`** already exists — use it to store `{"instagram": "17901234567890", "facebook": "1234567890_1234"}` so later phases can reference Meta post IDs for analytics.

**Decision required from user/planner:** Confirm the rename from `scheduled_posts` → `social_posts` and enum from `pending/published/error` → `scheduled/publishing/published/failed`. The UI copy stays Spanish ("Pendiente"/"Publicado"/"Error") but the DB layer uses the pre-existing enum. **This is Assumption A1 below.**

## Architecture Patterns

### Recommended Project Structure (additive only)

```
admin-ui/src/pages/
├── 7_Campañas.py            # MODIFY: add Step 3 (checkbox + composer)
└── 8_Publicaciones.py       # NEW

admin-ui/src/components/
└── database.py              # ADD: fetch_social_posts(), insert_social_post(), delete_social_post()

n8n/workflows/
├── social-publish.json      # NEW: webhook-triggered publish flow
└── social-scheduler.json    # NEW: cron-triggered dispatcher (every 1 min)

postgres/init/
└── 001_schema.sql           # NO CHANGE — social_posts already exists

docker-compose.yml           # MODIFY: add `uploads` named volume mounted on streamlit + n8n

caddy/Caddyfile              # MODIFY: add /uploads/* static route (only if Meta API needs public URL)

/opt/clinic-crm/uploads/     # NEW shared volume (runtime state, NOT in git)
```

### Pattern 1: Webhook-Triggered n8n Workflow with Postgres Status Update

**Source:** `n8n/workflows/campaign-blast.json` — reuse as scaffold for `social-publish.json`.

**What:** Streamlit POSTs to `http://n8n:5678/webhook/social-publish` with `{"post_id": "uuid"}`. n8n workflow:
1. Webhook Trigger node (`path: social-publish`, method POST, `responseMode: onReceived`)
2. Set node extracts `post_id` from `$json.body.post_id`
3. Postgres node UPDATE `social_posts SET status='publishing' WHERE id = '{{post_id}}'::uuid RETURNING *`
4. IF node branches on `{{$env.MOCK_SOCIAL}} === 'true'`
   - **Mock branch:** Set node logs a fake `platform_post_ids`, returns success
   - **Real branch:** HTTP Request nodes call Meta Graph API (Instagram and/or Facebook depending on `platforms` array)
5. Postgres node UPDATE `social_posts SET status='published', published_at=now(), platform_post_ids='{...}' WHERE id = ...`
6. On error: Postgres node UPDATE `social_posts SET status='failed', error_message=$error.message WHERE id = ...`

**Example (Postgres status update node, reuse from campaign-blast):**
```sql
-- Source: n8n/workflows/campaign-blast.json "Mark In Progress" node
UPDATE social_posts
SET status = 'publishing', updated_at = now()
WHERE id = '{{ $json.post_id }}'::uuid
RETURNING id, caption, image_url, platforms, campaign_id
```

### Pattern 2: Cron-Triggered Dispatcher (social-scheduler)

**Source:** n8n Schedule Trigger node (built-in) — no external cron.

**What:** Schedule Trigger node fires every 1 minute → Postgres node queries:

```sql
SELECT id FROM social_posts
WHERE status = 'scheduled'
  AND scheduled_at <= now()
ORDER BY scheduled_at ASC
LIMIT 20;
```

Then for each row, an HTTP Request node POSTs back to `http://n8n:5678/webhook/social-publish` with the `post_id`. This keeps the publish logic in a single workflow (DRY) and lets `social-scheduler.json` be 3 nodes total.

**Alternative (simpler, single workflow):** Add a Schedule Trigger as an alternative entry point inside `social-publish.json` itself. The Set node branches: if `$json.body.post_id` exists → single-post path; else → SELECT pending posts → Split In Batches → each row enters the publish pipeline. This avoids the HTTP re-entry and is the n8n-idiomatic pattern for "webhook OR cron."

**Recommendation:** Use the **single-workflow approach** unless the planner explicitly wants separation. One JSON file, one credential, one place to debug.

### Pattern 3: Session-State Multi-Step Flow (Step 3 extension)

**Source:** `7_Campañas.py` lines 24-28, 55-175 — extend verbatim.

**What:** The existing `campanas_mode` state machine (`setup` → `progress`) stays untouched. Step 3 fields are added **inside the `setup` branch**, after the preview and before the confirmation gate. The confirmation button handler becomes:

```python
# Source: 7_Campañas.py::confirm block (extended for Step 3)
if confirm:
    # --- existing Phase 5 path (unchanged) ---
    campaign_name = f"{primary_tag_name} · {_format_date(datetime.now())}"
    row = insert_campaign(...)
    new_id = row["id"]
    insert_campaign_recipients(new_id, [...])

    # --- new Step 3 path (only if checkbox on) ---
    social_post_id = None
    if st.session_state.get("campanas_publish_social"):
        image_path = _save_uploaded_image(st.session_state.campanas_social_image_bytes)
        social_post_id = insert_social_post(
            caption=st.session_state.campanas_social_caption,
            image_url=image_path,
            platforms=st.session_state.campanas_social_platforms,
            scheduled_at=_combine_date_time(
                st.session_state.campanas_social_date,
                st.session_state.campanas_social_time,
            ),
            campaign_id=new_id,  # link via existing FK
        )

    # --- trigger WA blast (unchanged) ---
    if not _trigger_n8n_webhook(str(new_id)):
        st.error("Error al iniciar la campaña...")
        st.stop()

    # --- trigger social publish if applicable ---
    if social_post_id and not _trigger_n8n_social_webhook(str(social_post_id)):
        st.warning("Campaña WA iniciada, pero el post social falló al encolarse. Revísalo en Publicaciones.")

    st.session_state.campanas_active_campaign_id = str(new_id)
    st.session_state.campanas_mode = "progress"
    st.rerun()
```

**Key insight:** The social trigger is **best-effort** after the WA blast has been committed. If it fails, the campaign still fires and the admin is told to fix the social side in the standalone page — no rollback, no transactional distributed commit.

### Anti-Patterns to Avoid

- **Distributed transaction across WA + social:** Do not attempt to rollback a `campaign_log` insert if the social webhook fails. The WA side is already hitting Evolution API; it's effectively non-reversible. Best-effort + UI warning is the correct pattern.
- **Storing the image as bytea in Postgres:** Rejected. Use the uploads volume per D-12. Bytea blobs balloon backups and slow queries.
- **Calling Meta Graph API directly from Streamlit:** Rejected. All external API calls flow through n8n for centralized error handling, credential management, and logging (workflow_errors table).
- **Using Streamlit's file_uploader persistence across reruns without `st.session_state`:** Streamlit reruns the script on every interaction; uploaded file bytes must be persisted to `st.session_state` immediately or they disappear on the next widget interaction.
- **Polling `8_Publicaciones.py` with `streamlit_autorefresh`:** Rejected by UI-SPEC — most posts are scheduled hours/days ahead, live polling wastes cycles. Manual refresh is sufficient.
- **Hardcoding Graph API `latest` version:** Always pin `v21.0`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cron / scheduler | `APScheduler` in Streamlit, Python `threading.Timer`, Linux cron | n8n Schedule Trigger node | Streamlit pages are request-scoped and die on no-traffic. n8n runs 24/7 and already handles retries, logging, error surfaces. |
| Multi-step Meta Graph API container flow | Raw `requests.post` in Python | n8n HTTP Request nodes | Credential management, retry policy, error surfacing all free from n8n. |
| Image upload persistence | Custom file server | `st.file_uploader` + local volume + Caddy static | Streamlit handles multipart. Caddy serves static with automatic HTTPS. |
| Status state machine | Custom Python state class | Postgres `CHECK` constraint on `status` column | Already enforced at the schema level. |
| Webhook trigger | Flask sidecar | n8n Webhook Trigger node | Reuse existing n8n; same pattern as `campaign-blast`. |
| Mock/real API switching | `if/else` in code | `MOCK_SOCIAL` env var + n8n IF node | Toggle without code change per D-02. |
| Idempotency for "dispatcher runs publish twice" | Distributed locks | Postgres status transition `scheduled` → `publishing` is the lock | First UPDATE to `publishing` claims the row; second attempt finds no matching row and no-ops. |

**Key insight:** This phase writes almost no custom Python. The Streamlit pages are mostly widget composition + 3 DB helper functions + 2 webhook POST helpers. The workflow logic lives entirely in n8n JSON.

## Common Pitfalls

### Pitfall 1: Streamlit file_uploader loses bytes on rerun
**What goes wrong:** Admin uploads image → fills caption → clicks schedule → handler reads `st.file_uploader` result → it's `None` because another widget interaction cleared it.
**Why it happens:** `st.file_uploader` returns an `UploadedFile` object that is valid only in the rerun where the upload happened. Later reruns return `None` unless the bytes are stashed in `st.session_state`.
**How to avoid:** On first render, stash `uploaded_file.getvalue()` into `st.session_state["pubs_image_bytes"]` immediately. Use the session_state bytes for preview AND for saving to disk on submit.
**Warning signs:** Intermittent "please upload an image" errors after the admin has clearly uploaded one.

### Pitfall 2: Caption HTTPS quirk for Instagram
**What goes wrong:** Instagram `/media` endpoint receives `image_url` but returns `error_code: 2207026` (media fetch failed) because the URL is not publicly reachable.
**Why it happens:** Meta's servers must `GET` the image from a publicly HTTPS-reachable URL. `http://n8n:5678/uploads/...` and `file:///opt/...` both fail.
**How to avoid:** Serve `/uploads/*` via Caddy on the public domain (`https://${ADMIN_SUBDOMAIN}.${DOMAIN}/uploads/{filename}`). Confirm the Caddyfile has a file server block for that path and the directory is mounted into the Caddy container (or reverse-proxied to Streamlit). Under `MOCK_SOCIAL=true` this is unnecessary, so the issue only surfaces post-App-Review — test early.
**Warning signs:** Posts succeed in mock mode but fail immediately on real mode with Meta error 2207026 or 9004.

### Pitfall 3: Instagram two-step publish race condition
**What goes wrong:** Container created successfully → `media_publish` called immediately → returns `error 9007` (media not finished uploading).
**Why it happens:** Meta processes the container asynchronously. For photos it's usually instant, but there's a brief window where polling `GET /{container-id}?fields=status_code` may still return `IN_PROGRESS`.
**How to avoid:** Between `POST /media` and `POST /media_publish`, add a short Wait node (2 seconds) or poll the container status until `status_code === FINISHED`. For Phase 6 MVP, a fixed 3-second Wait is simpler and acceptable for photos.
**Warning signs:** Sporadic `media not ready` errors on real publishes.

### Pitfall 4: Facebook Page Access Token vs User Access Token
**What goes wrong:** Developer uses the user's token from OAuth and gets `(#200) Permissions error` when posting to the Page.
**Why it happens:** `POST /{page-id}/photos` requires a **Page access token** obtained by calling `GET /me/accounts` with the user token, then using the Page-specific token returned. The Page token is long-lived (~60 days after using the long-lived user token as the seed).
**How to avoid:** Store the Page access token as an n8n credential, not the user token. Document the token rotation process (every ~55 days). Phase 1 already has this as an open item; confirm with Phase 1 artifacts.
**Warning signs:** `error_code: 200` / `"The user hasn't authorized the application..."` on Facebook publish.

### Pitfall 5: Dispatcher double-firing during overlapping runs
**What goes wrong:** Cron fires at T=0 and T=60s. If a publish takes >60s, the T=60s run picks up the same `scheduled` row and posts it twice.
**Why it happens:** No row lock between SELECT and UPDATE.
**How to avoid:** Transition status to `publishing` **inside the initial SELECT** using `UPDATE ... RETURNING`:
```sql
UPDATE social_posts
SET status = 'publishing', updated_at = now()
WHERE id IN (
    SELECT id FROM social_posts
    WHERE status = 'scheduled' AND scheduled_at <= now()
    ORDER BY scheduled_at ASC
    LIMIT 20
    FOR UPDATE SKIP LOCKED
)
RETURNING id, caption, image_url, platforms, campaign_id;
```
`FOR UPDATE SKIP LOCKED` + the `publishing` state transition makes dispatcher concurrent-safe.
**Warning signs:** Duplicate Instagram posts at exactly the scheduled minute.

### Pitfall 6: Local time vs UTC on `scheduled_at`
**What goes wrong:** Admin schedules "10:00 AM" → at 10:00 AM local time nothing happens. At 4:00 AM local time the next day, the post goes out.
**Why it happens:** `st.time_input` returns a `datetime.time` in no particular timezone; Postgres `TIMESTAMPTZ` stores UTC. If the Streamlit container runs UTC and the admin thinks in America/Mexico_City, naive `datetime.combine(date, time)` is wrong by 6 hours.
**How to avoid:** Always convert the local-naive datetime using `zoneinfo.ZoneInfo("America/Mexico_City")` before inserting. Postgres handles the conversion to UTC automatically for TIMESTAMPTZ. Display times in the list reading `AT TIME ZONE 'America/Mexico_City'` in the SELECT.
**Warning signs:** Posts fire hours late or early.

### Pitfall 7: Image aspect ratio rejected by Instagram
**What goes wrong:** Admin uploads a 1080x1350 portrait; Instagram rejects with "The aspect ratio is not supported."
**Why it happens:** Instagram feed photos must be between 4:5 and 1.91:1 aspect ratio. [CITED: developers.facebook.com/docs/instagram-platform/content-publishing]
**How to avoid:** MVP approach per UI-SPEC: do not validate aspect ratio in UI. Let Meta return the error, surface it in `error_message`, show in `st.error()` row. Phase 6.x can add `Pillow`-based validation if this becomes common.
**Warning signs:** Posts failing with "aspect ratio" or "resolution too low."

## Code Examples

### Example 1: Streamlit file upload with session_state persistence

```python
# Source: Streamlit official pattern (st.file_uploader)
uploaded = st.file_uploader("Imagen", type=["jpg", "jpeg", "png", "webp"])
if uploaded is not None:
    # Stash bytes immediately so they survive reruns
    st.session_state["pubs_image_bytes"] = uploaded.getvalue()
    st.session_state["pubs_image_name"] = uploaded.name

if "pubs_image_bytes" in st.session_state:
    st.image(st.session_state["pubs_image_bytes"], width=300)
```

### Example 2: Save uploaded image to shared volume

```python
# Pattern: write to shared volume mounted at /opt/clinic-crm/uploads/
import uuid
from pathlib import Path

UPLOADS_DIR = Path("/opt/clinic-crm/uploads")

def save_uploaded_image(image_bytes: bytes, original_name: str) -> str:
    """Save image bytes to uploads volume, return relative path for DB."""
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(original_name).suffix.lower().lstrip(".")
    if ext == "jpeg":
        ext = "jpg"
    filename = f"{uuid.uuid4()}.{ext}"
    (UPLOADS_DIR / filename).write_bytes(image_bytes)
    # Return path as stored in social_posts.image_url
    # n8n reads this as /opt/clinic-crm/uploads/{filename} via the shared volume
    return f"uploads/{filename}"
```

### Example 3: insert_social_post helper (add to database.py)

```python
# Source: pattern from existing insert_campaign() in admin-ui/src/components/database.py
def insert_social_post(
    caption: str,
    image_url: str,
    platforms: list[str],
    scheduled_at,  # datetime with tzinfo
    campaign_id: str | None = None,
) -> dict:
    """Insert a scheduled social post. Returns the inserted row."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO social_posts
                    (caption, image_url, platforms, scheduled_at, status, campaign_id)
                VALUES (%s, %s, %s, %s, 'scheduled', %s)
                RETURNING id, status, scheduled_at
                """,
                (caption, image_url, platforms, scheduled_at, campaign_id),
            )
            row = cur.fetchone()
            conn.commit()
            return row
    finally:
        conn.close()
```

### Example 4: Instagram Graph API two-step publish (n8n HTTP nodes)

```javascript
// Source: https://developers.facebook.com/docs/instagram-platform/content-publishing/
// Step 1: Create media container
// POST https://graph.facebook.com/v21.0/{ig-user-id}/media
// Body (form-urlencoded):
//   image_url: https://admin.example.com/uploads/{filename}
//   caption: {{$json.caption}}
//   access_token: {{$credentials.pageAccessToken}}
// Response: { "id": "{container_id}" }

// Step 2 (after a short Wait): Publish
// POST https://graph.facebook.com/v21.0/{ig-user-id}/media_publish
// Body:
//   creation_id: {container_id}
//   access_token: {{$credentials.pageAccessToken}}
// Response: { "id": "{published_media_id}" }
```

### Example 5: Facebook Page photo publish (single step)

```javascript
// Source: https://developers.facebook.com/docs/graph-api/reference/page/photos/
// POST https://graph.facebook.com/v21.0/{page-id}/photos
// Body:
//   url: https://admin.example.com/uploads/{filename}
//   caption: {{$json.caption}}
//   access_token: {{$credentials.pageAccessToken}}
// Response: { "id": "{photo_id}", "post_id": "{page_id}_{post_id}" }
```

### Example 6: n8n dispatcher SELECT with SKIP LOCKED

```sql
-- n8n Schedule Trigger → Postgres node
-- Prevents double-dispatch even if runs overlap
UPDATE social_posts
SET status = 'publishing', updated_at = now()
WHERE id IN (
    SELECT id FROM social_posts
    WHERE status = 'scheduled' AND scheduled_at <= now()
    ORDER BY scheduled_at ASC
    LIMIT 20
    FOR UPDATE SKIP LOCKED
)
RETURNING id, caption, image_url, platforms, campaign_id;
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Instagram Basic Display API | Instagram Graph API (Business/Creator accounts) | 2020; Basic Display sunset December 2024 | [VERIFIED: Meta deprecation notices] Phase 6 must use Graph API. Account must be linked to a FB Page. |
| Direct `/me/feed` post with `picture` field | `/{page_id}/photos` with `url` field | — | Photos endpoint is the modern pattern for Page photo posts. |
| `publish_actions` permission | `pages_manage_posts`, `instagram_basic`, `instagram_content_publish` | 2018 | App Review required for all three permissions — already flagged in Phase 1 blockers. |

**Deprecated / outdated:**
- `publish_actions` permission — removed years ago.
- Instagram Basic Display API — sunset, irrelevant to publishing.
- `/me/photos` direct upload without a Page token — returns permissions error post-2020.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The phase will rename `scheduled_posts` → `social_posts` and adopt the existing enum (`scheduled/publishing/published/failed`) instead of creating a new table or new enum | Schema Alignment | **HIGH if wrong** — planner writes tasks against non-existent `scheduled_posts` table, migration churn, schema drift. Requires user/planner confirmation. |
| A2 | The Caddy instance can serve `/uploads/*` as static files on the public admin domain when Meta App Review lands | Pitfall 2 | MEDIUM — under `MOCK_SOCIAL=true` there is no blocker, but real publishes will fail until this is wired. Tested late. |
| A3 | The Phase 1 Meta App Review includes permissions `pages_manage_posts`, `instagram_basic`, `instagram_content_publish`, `business_management` | External APIs | HIGH — missing any one blocks real publishes. Phase 1 should be re-audited before Phase 6 turns off `MOCK_SOCIAL`. Phase 1 blockers in STATE.md already flag this. |
| A4 | The IG Business account is already linked to the Facebook Page that has the stored access token | External APIs | HIGH if wrong — linking is a one-time setup in Meta Business Manager; failure here surfaces as `error 24` on the `/media` call. |
| A5 | The `social-scheduler` cron pattern is preferred over Meta-native `publish_time` parameter | Architecture Patterns | LOW — both work. CONTEXT.md D-16 already locks the cron approach. |
| A6 | Adding the `uploads` volume to docker-compose does not require an existing-data migration (fresh volume on next deploy) | docker-compose | LOW — first deploy of Phase 6, no historical data to migrate. |
| A7 | Instagram Graph API v21.0 is the current stable version as of phase execution | Standard Stack | LOW — Meta quarterly release cadence means v22/v23 may exist by execution; verify `graph.facebook.com/v21.0` is still supported at execution time (it will be — Meta supports 2+ years of old versions). |

## Runtime State Inventory

> Phase 6 is primarily additive (new pages, new workflow, new volume) but **does touch** an existing page and adds a volume mount. Inventory is required.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `social_posts` table already exists in `postgres/init/001_schema.sql` (Phase 1 readiness). **No new migration needed** — schema is already in place. If the column name mismatch (A1) is resolved by using `image_url`, no ALTER TABLE is required. If planner insists on `image_path` name, an ALTER TABLE RENAME COLUMN is needed — strongly discouraged. | **None (recommended path)** or ALTER TABLE (discouraged) |
| Live service config | n8n workflows are committed to git as JSON, BUT n8n running in the VPS holds them in its own Postgres. After committing `social-publish.json`/`social-scheduler.json`, they must be **imported into the running n8n instance** (manual or via n8n CLI) or they will not execute. | Document import step in plan; include credential re-bind (postgres + Meta API) since credential IDs are instance-specific |
| OS-registered state | None — no OS cron jobs (n8n handles scheduling), no systemd units added. | None |
| Secrets / env vars | **`MOCK_SOCIAL`** (new env var in n8n service) — must be added to `.env.example` and `.env`. **`META_PAGE_ACCESS_TOKEN`** / **`META_IG_USER_ID`** / **`META_FB_PAGE_ID`** (new n8n credentials) — must be configured in the running n8n instance. These are **not** code-reading env vars; they are n8n credential slots. | Add to `.env.example` (MOCK_SOCIAL only); document credential setup for the rest; do NOT commit tokens |
| Build artifacts / installed packages | No new Python packages. No new Docker images. No new node_modules. | None |

**Canonical question — "After every file in the repo is updated, what runtime systems still have the old string cached, stored, or registered?"** → The running n8n instance will need both new workflows imported. The `uploads/` volume must exist on the VPS filesystem at `/opt/clinic-crm/uploads/` before the first deploy (or the mount creates it as root-owned — ensure correct UID). The running streamlit container does not auto-refresh env vars; a `docker compose up -d streamlit` restart is required after adding `MOCK_SOCIAL` if Streamlit needs to read it for the banner.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| n8n running | Workflow execution | ✓ (Phase 1) | latest | — |
| PostgreSQL | social_posts CRUD | ✓ (Phase 1) | 16-alpine | — |
| Streamlit container | 8_Publicaciones.py | ✓ (Phase 1) | ≥1.35 | — |
| Caddy | HTTPS + static uploads | ✓ (Phase 1) | 2-alpine | — |
| Shared `uploads` volume | Image handoff streamlit↔n8n | ✗ | — | **Blocks** — must be added to docker-compose this phase |
| Meta Page Access Token | Real Instagram/Facebook publishes | ✗ (pending App Review) | — | `MOCK_SOCIAL=true` (D-02) |
| Instagram Business account linked to FB Page | Instagram publishing | Unknown | — | `MOCK_SOCIAL=true` until verified |
| Public HTTPS for `/uploads/*` via Caddy | Meta `image_url` fetch | Partial (Caddy serves admin UI on HTTPS; `/uploads/` route **not yet configured**) | — | Blocks real mode only; mock mode unaffected |

**Missing dependencies with no fallback:**
- Shared `uploads` volume — must be added in this phase (it's part of the work, not a blocker for starting)

**Missing dependencies with fallback:**
- Meta Page Access Token / App Review approval → `MOCK_SOCIAL=true` (D-02)
- Caddy `/uploads/*` route → required only when `MOCK_SOCIAL=false` flips

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (inherited from Phase 5; add to `admin-ui/requirements-dev.txt` if not already) |
| Config file | `admin-ui/pyproject.toml` or `admin-ui/pytest.ini` — verify at Wave 0 |
| Quick run command | `docker compose exec streamlit pytest tests/test_social_posts.py -x` |
| Full suite command | `docker compose exec streamlit pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| SOCIAL-01 | `insert_social_post()` writes a row with status='scheduled' | unit | `pytest tests/test_database.py::test_insert_social_post -x` | ❌ Wave 0 |
| SOCIAL-01 | `save_uploaded_image()` writes bytes to uploads dir and returns valid relative path | unit | `pytest tests/test_uploads.py::test_save_image_returns_path -x` | ❌ Wave 0 |
| SOCIAL-01 | 8_Publicaciones.py composer renders without import errors | smoke | `pytest tests/test_pages.py::test_publicaciones_imports -x` | ❌ Wave 0 |
| SOCIAL-02 | Step 3 active path: single click inserts both campaign_log AND social_posts rows | integration | `pytest tests/test_unified_flow.py::test_unified_campaign_inserts_both -x` | ❌ Wave 0 |
| SOCIAL-02 | Step 3 inactive path: existing Phase 5 behavior unchanged (no social_posts insert) | regression | `pytest tests/test_unified_flow.py::test_phase5_no_regression -x` | ❌ Wave 0 |
| SOCIAL-03 | `fetch_social_posts()` returns rows ordered by scheduled_at ASC | unit | `pytest tests/test_database.py::test_fetch_social_posts_ordering -x` | ❌ Wave 0 |
| SOCIAL-03 | Status label mapping (DB enum → UI Spanish label) is complete | unit | `pytest tests/test_status_map.py -x` | ❌ Wave 0 |
| n8n social-publish.json | `MOCK_SOCIAL=true` executes mock branch and updates status to published | manual | Trigger webhook manually in n8n UI, assert DB row | N/A (manual) |
| n8n social-scheduler | Dispatcher transitions `scheduled` → `publishing` atomically (no double-fire) | manual | INSERT 2 rows scheduled at same timestamp, run scheduler twice in quick succession | N/A (manual) |

### Sampling Rate
- **Per task commit:** `docker compose exec streamlit pytest tests/test_social_posts.py tests/test_database.py -x`
- **Per wave merge:** `docker compose exec streamlit pytest tests/ -x`
- **Phase gate:** Full suite green + manual mock-mode run of end-to-end flow (7_Campañas Step 3 checked + 8_Publicaciones composer) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `admin-ui/tests/test_database.py` — covers SOCIAL-01, SOCIAL-03 DB helpers
- [ ] `admin-ui/tests/test_uploads.py` — covers `save_uploaded_image()`
- [ ] `admin-ui/tests/test_unified_flow.py` — covers SOCIAL-02 integration
- [ ] `admin-ui/tests/test_pages.py` — import smoke for new page
- [ ] `admin-ui/tests/conftest.py` — shared Postgres fixture (reuse Phase 5 fixture if exists; confirm in Wave 0)
- [ ] pytest framework install verification: `docker compose exec streamlit pytest --version`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (admin-only UI already behind Caddy basic auth from Phase 1) | Phase 1 basic auth unchanged |
| V3 Session Management | no | Streamlit session_state (in-memory) unchanged |
| V4 Access Control | yes (Meta Page Access Token) | Store as n8n credential — never in git, never in env var visible to Streamlit |
| V5 Input Validation | yes | File type allowlist (`["jpg","jpeg","png","webp"]`), size cap (8 MB per UI-SPEC), caption max_chars=2200 |
| V6 Cryptography | no (no new crypto paths) | Inherit Caddy HTTPS |
| V12 File Handling | **yes — primary concern** | UUID filenames (no user-controlled path), MIME sniff from Streamlit, directory outside web root except via explicit Caddy route |

### Known Threat Patterns for Streamlit + n8n + Meta Graph API

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via uploaded filename | Tampering | UUID-based filename per D-13; never use `original_name` in the path |
| Arbitrary file type upload (e.g., SVG with embedded script) | Tampering / Elevation | Extension allowlist ≠ MIME allowlist; also restrict to `["jpg","jpeg","png","webp"]` in `st.file_uploader(type=...)` and reject anything else at insert time |
| Serving uploads as user-controlled HTML | Info disclosure / XSS | Caddy serves with `Content-Disposition: attachment` OR locked MIME headers; do not serve `/uploads/*` from the same origin as the admin UI unless absolutely necessary |
| Token exposure in n8n error messages | Info disclosure | n8n masks credentials in logs by default; verify `workflow_errors` table insert does not include `$credentials` in the error details JSON |
| Replay of webhook POST to `/webhook/social-publish` from LAN | Tampering | n8n webhooks live on internal Docker network only (`http://n8n:5678`); no public route. Caddy does **not** expose `/webhook/*` externally. Verify Caddyfile. |
| Scheduler running under compromised n8n credentials could mass-post | Elevation | Rate limit posts per hour at the SQL level: LIMIT 20 per dispatcher run; alerting on >N/hour (deferred to Phase 7 Dashboard) |
| Meta API rate limiting triggers account block | DoS | Dispatcher LIMIT 20 + 1-minute cron = max 20 posts/min theoretical; real volume for single-clinic MVP is <10 posts/day, nowhere near limits |

**Image size cap:** UI-SPEC says 8 MB. Enforce client-side (Streamlit displays error) AND server-side (Python check on `len(image_bytes)` before writing). Reject oversize at both layers.

## Open Questions

1. **Schema naming:** Rename `scheduled_posts` → `social_posts` and `image_path` → `image_url` in CONTEXT.md and plans? (Assumption A1)
   - What we know: `social_posts` table exists from Phase 1 with `image_url` column.
   - What's unclear: Planner may need explicit user approval before renaming CONTEXT.md references.
   - Recommendation: Planner writes tasks against `social_posts` + `image_url`. Flag A1 in PLAN.md assumptions section. Update CONTEXT.md or leave planner note.

2. **Status enum reconciliation:** Use existing `scheduled/publishing/published/failed` or migrate to new `pending/published/error`?
   - What we know: Existing enum is richer (has `publishing` and `failed`); new enum has fewer states.
   - What's unclear: UI-SPEC assumes `pending/published/error` labels.
   - Recommendation: Keep existing DB enum; add a Python mapping dict `{'scheduled':'Pendiente','publishing':'Pendiente','published':'Publicado','failed':'Error','draft':'—'}` in the Streamlit layer. One source of truth, zero schema change.

3. **Meta Page Access Token lifecycle:** Who rotates it every ~55 days?
   - What we know: Long-lived Page tokens expire at ~60 days unless used.
   - What's unclear: There's no operational runbook for rotation.
   - Recommendation: Deferred to Phase 7 dashboard + alerting. For Phase 6, document token expiry as a known operational risk and add a n8n workflow_errors alert when Meta returns `error 190` (expired token).

4. **Caddy `/uploads/*` exposure:** Is serving user-uploaded images via public HTTPS acceptable, given that the uploads are marketing content (not PHI)?
   - What we know: Clinic posts are public marketing — no privacy concerns.
   - What's unclear: Whether Caddy should use a separate subdomain (e.g., `cdn.example.com`) or inline under the admin subdomain.
   - Recommendation: Inline under admin subdomain is simplest for MVP; cdn subdomain is a Phase 2 optimization.

5. **Retry policy on Meta API failures:** CONTEXT.md Claude's Discretion says "retry automático 1 vez, luego marcar como error."
   - What we know: n8n has a built-in "Retry On Fail" option on HTTP nodes.
   - What's unclear: Whether to retry on 4xx (permission errors — don't retry) or only 5xx/network (do retry).
   - Recommendation: Enable n8n HTTP node retry: 1 retry, 2s delay, **only on 5xx and timeout**. Do NOT retry 4xx (permission, validation) — those are permanent failures.

## Sources

### Primary (HIGH confidence)
- `/home/rolando/Desarrollo/social-media-manager/postgres/init/001_schema.sql` — schema verified, `social_posts` table exists
- `/home/rolando/Desarrollo/social-media-manager/admin-ui/src/pages/7_Campañas.py` — session_state pattern verified
- `/home/rolando/Desarrollo/social-media-manager/admin-ui/src/components/database.py` — db helper pattern verified
- `/home/rolando/Desarrollo/social-media-manager/n8n/workflows/campaign-blast.json` — webhook + postgres pattern verified
- `/home/rolando/Desarrollo/social-media-manager/docker-compose.yml` — streamlit/n8n services verified
- `/home/rolando/Desarrollo/social-media-manager/.planning/phases/06-social-media-publishing/06-CONTEXT.md` — user decisions
- `/home/rolando/Desarrollo/social-media-manager/.planning/phases/06-social-media-publishing/06-UI-SPEC.md` — UI contract
- Meta Developer Documentation — Instagram Content Publishing: https://developers.facebook.com/docs/instagram-platform/content-publishing/
- Meta Developer Documentation — IG User `/media_publish`: https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media_publish/
- Meta Developer Documentation — Page `/photos`: https://developers.facebook.com/docs/graph-api/reference/page/photos/

### Secondary (MEDIUM confidence)
- Instagram Graph API Developer Guide 2026 (elfsight): general flow confirmed against Meta docs
- n8n Schedule Trigger docs (training knowledge, pattern verified against existing workflows)

### Tertiary (LOW confidence)
- Exact current Graph API version (`v21.0`) — Meta releases quarterly; verify `graph.facebook.com/v21.0` is still in the 2-year support window at execution time. [ASSUMED] but risk is low.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every library and service is already deployed in Phases 1-5
- Architecture: HIGH — every pattern is a direct reuse of an existing pattern in the codebase
- Meta Graph API specifics: MEDIUM — endpoints and flow are documented but deployment is gated by App Review and only validated under `MOCK_SOCIAL=false`
- Schema alignment: HIGH — verified directly against 001_schema.sql, but requires planner decision on naming (A1)
- Pitfalls: HIGH — pitfalls 1, 5, 6, 7 are general patterns; 2, 3, 4 are Meta-specific and documented in Meta's own docs
- Security: MEDIUM — file-handling threats are well-known, token rotation is an operational gap deferred to Phase 7

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (30 days) for the Meta Graph API specifics; indefinitely for the codebase-internal patterns
