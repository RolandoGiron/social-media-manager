# Phase 6: Social Media Publishing - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

El admin puede programar posts en Instagram y Facebook con imagen y caption para una fecha/hora específica, Y puede lanzar una sola acción que simultáneamente envía el WhatsApp broadcast al segmento seleccionado Y publica en redes sociales.

Los flujos de WhatsApp campaña blast (Fase 5) y chatbot/citas (Fase 4) son independientes y NO se modifican. Esta fase solo añade la capa de publicación social y el trigger unificado.

**Requisitos en scope:** SOCIAL-01, SOCIAL-02, SOCIAL-03

</domain>

<decisions>
## Implementation Decisions

> **Schema correction (2026-04-13, post-research):** D-03 and D-13 were updated to reference the existing Phase 1 schema (`social_posts` table, `image_url` column) rather than introducing a new `scheduled_posts` table. Corrected per RESEARCH.md A1 — existing Phase 1 schema adopted. The original intent (track post state, map to DB path) is preserved; only the identifiers changed to match what already ships in `postgres/init/001_schema.sql` lines 174-192.

### Meta API — Estrategia mientras App Review está pendiente
- **D-01:** Construir con **Meta Graph API real** (endpoints de Instagram Graph API y Facebook Pages API vía n8n HTTP nodes). No depender de Buffer ni de otra plataforma intermediaria.
- **D-02:** Variable de entorno `MOCK_SOCIAL=true/false` en el workflow de n8n de publicación. Cuando `MOCK_SOCIAL=true`, el nodo de publicación logea la acción en lugar de llamar a Meta Graph API. Cuando llegue la aprobación de Meta App Review, se cambia la env var y el workflow funciona sin ningún cambio de código.
- **D-03:** La tabla existente `social_posts` (definida en `postgres/init/001_schema.sql` líneas 174-192, Fase 1) almacena el estado de cada publicación. El admin puede verificar el estado desde la UI aunque la publicación real esté mockeada. *Corregido per RESEARCH.md A1 — existing Phase 1 schema adopted.*

### Flujo Campaña Unificada — Extensión de 7_Campañas.py
- **D-04:** El flujo unificado vive en **7_Campañas.py** (extender, no crear nueva página). Después del flujo existente de Fase 5 (Paso 1: segmento + plantilla; Paso 2: confirmación), se agrega un **Paso 3 opcional**: checkbox "Publicar en redes sociales también".
- **D-05:** Si el checkbox de Paso 3 está activado, aparece el composer de post: campo de caption (textarea), selector de imagen (file uploader), y campo de fecha/hora de publicación. El caption puede diferir del mensaje WA.
- **D-06:** El botón "Lanzar campaña" (existente) dispara ambos canales si el checkbox está activo: (a) inserta en `campaign_log` y `campaign_recipients` + webhook n8n para WA blast (flujo Fase 5), y (b) inserta en `social_posts` + webhook n8n para social publishing. **Atómico:** si el webhook social falla antes de disparar el WA blast, el blast NO se envía (usar `st.error` + `st.stop()`, no `st.warning` + continue). Ambos canales tienen éxito o ninguno procede.
- **D-07:** Si el checkbox de Paso 3 está **desactivado**, el flujo se comporta exactamente igual que en Fase 5 — sin cambios en el blast WA existente.

### Página de Publicaciones Standalone — 8_Publicaciones.py
- **D-08:** Nueva página **8_Publicaciones.py** para SOCIAL-01 y SOCIAL-03: lista de publicaciones programadas con estado (pendiente/publicado/error) + composer para crear un post standalone (sin WA blast).
- **D-09:** La lista muestra: Caption (truncado), Plataforma (Instagram/Facebook), Fecha programada, Estado, Acciones. Ordenada por `scheduled_at ASC` para ver lo próximo primero.
- **D-10:** El composer standalone en 8_Publicaciones.py usa el mismo pattern que el Paso 3 de 7_Campañas.py: caption, imagen, fecha/hora. Al guardar, inserta en `social_posts` + dispara webhook n8n.
- **D-11:** El flujo unificado de 7_Campañas.py también escribe en `social_posts` cuando está activo — el admin puede ver el estado de esas publicaciones en 8_Publicaciones.py.

### Imágenes — Upload y Storage
- **D-12:** Admin sube imagen via **Streamlit `st.file_uploader`** (formatos aceptados: JPG, PNG, WEBP). La imagen se guarda en `/opt/clinic-crm/uploads/` (volumen Docker compartido, montado en los contenedores de Streamlit y n8n).
- **D-13:** Nombre de archivo: `{uuid4}.{ext}` para evitar colisiones. La ruta relativa (ej: `uploads/abc-123.jpg`) se guarda en la columna existente `social_posts.image_url` (Fase 1 schema). n8n lee el archivo desde esa ruta montada para adjuntarlo a la llamada de Meta Graph API. *Corregido per RESEARCH.md A1 — existing Phase 1 schema adopted.*
- **D-14:** El volumen `uploads` debe estar declarado en docker-compose.yml y montado en ambos servicios (streamlit y n8n). Caddy sirve `/uploads/` como static files si se necesita URL pública para Meta API (algunos endpoints de Meta requieren URL pública, no upload directo).

### n8n — Workflow de Publicación Social
- **D-15:** Nuevo workflow `social-publish.json`. Disparado por webhook POST con `post_id`. Lee `social_posts WHERE id = ?`, construye el payload, llama a Meta Graph API (Instagram y/o Facebook según la publicación). Actualiza `social_posts.status` a `published` o `failed`.
- **D-16:** Cron trigger separado `social-scheduler.json` (o integrado en `social-publish.json` como Schedule Trigger en n8n) que corre cada minuto, busca `social_posts WHERE status = 'scheduled' AND scheduled_at <= now()`, y dispara la publicación para cada post pendiente.
- **D-17:** Cuando `MOCK_SOCIAL=true`, el nodo de publicación hace un HTTP call a un endpoint interno de n8n (p.ej. `http://n8n:5678/webhook/mock-social-log`) que simplemente logea el payload y retorna `{success: true, mock: true}`. El endpoint interno es un webhook trigger separado (puede vivir en el mismo `social-publish.json` o en un micro-workflow companion). El resto del workflow (actualizar estado, etc.) corre igual. **No usar un Set node con JSON estático** — debe ser una llamada HTTP real para que el path de ejecución sea byte-equivalente al modo real.

### Claude's Discretion
- Diseño visual del Paso 3 en 7_Campañas.py (posición del checkbox, expansión/colapso de la sección)
- Selector de plataforma en el composer (Instagram y/o Facebook — checkbox múltiple o multiselect)
- Manejo de errores en n8n cuando Meta Graph API falla (retry automático 1 vez, luego marcar como error)
- Preview de imagen en el composer (st.image para previsualizar antes de guardar)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Database Schema
- `postgres/init/001_schema.sql` líneas 174-192 — Tabla `social_posts` ya existente (Fase 1). **No crear una tabla nueva.** Columnas: id, caption, image_url, platforms[], scheduled_at, published_at, status (draft/scheduled/publishing/published/failed), platform_post_ids jsonb, campaign_id fk, error_message, created_at, updated_at.

### Requirements
- `.planning/REQUIREMENTS.md` §SOCIAL — SOCIAL-01 (programar post con imagen/caption), SOCIAL-02 (trigger unificado WA + social), SOCIAL-03 (ver estado publicaciones)
- `.planning/ROADMAP.md` §Phase 6 — 3 success criteria definen el done

### Existing Admin UI (extend)
- `admin-ui/src/app.py` — Añadir 8_Publicaciones.py a st.navigation(); Paso 3 en 7_Campañas.py
- `admin-ui/src/components/sidebar.py` — render_sidebar() al top de nueva página (patrón estándar)
- `admin-ui/src/components/database.py` — Patrón de conexión DB para queries de social_posts
- `admin-ui/src/pages/7_Campañas.py` — Extender con Paso 3 opcional (checkbox + composer social)

### Existing n8n Workflows (reference)
- `n8n/workflows/campaign-blast.json` — Patrón de webhook trigger + loop + status update en PostgreSQL; reutilizar para social-publish.json
- `n8n/workflows/sub-send-wa-message.json` — Patrón de HTTP call a API externa desde n8n; misma estructura para Meta Graph API calls

### Prior Phase Context
- `.planning/phases/05-campaign-blast/05-CONTEXT.md` — D-05 a D-15: flujo de campaign_log, confirmación, monitoreo. El Paso 3 de Phase 6 debe integrarse sin romper este flujo.
- `.planning/phases/03-crm-core/03-CONTEXT.md` — Modelo de tags/segmentos (reutilizado para selección en flujo unificado)

### Docker Compose
- `docker-compose.yml` — Añadir volumen `uploads` montado en servicios `streamlit` y `n8n`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `admin-ui/src/pages/7_Campañas.py` — Flujo de 3 pasos con session_state ya implementado; Paso 3 se agrega como extensión natural después del paso de confirmación existente
- `admin-ui/src/components/database.py` — Patrón get_db_connection() para queries de social_posts
- `n8n/workflows/campaign-blast.json` — Webhook + PostgreSQL loop + status update: plantilla directa para social-publish.json
- `admin-ui/src/pages/3_Pacientes.py` — Patrón de tabla paginada con columnas de estado; replicar en lista de 8_Publicaciones.py

### Established Patterns
- **Multi-step flow con session_state:** Usado en 7_Campañas.py (Pasos 1→2→3 con flags de session_state); extender el mismo patrón para Paso 3
- **Polling cada 5s:** `streamlit_autorefresh` para monitoreo de estado; aplicar al estado de publicaciones si se desea actualización en vivo
- **n8n webhook trigger:** POST a webhook n8n con `{id}` → workflow procesa desde PostgreSQL; mismo pattern para `social-publish.json`
- **Status enum en DB:** el enum existente de `social_posts` es `draft/scheduled/publishing/published/failed` — usar los labels Pendiente/Publicado/Error via helper `status_label()`

### Integration Points
- **7_Campañas.py → nuevo Paso 3:** Después de que el admin confirma en Paso 2, renderizar checkbox "¿Publicar en redes también?". Si activo, mostrar composer. El botón "Lanzar" hace las dos inserciones + dos webhooks
- **8_Publicaciones.py → n8n social-publish webhook:** Nueva página llama al mismo webhook que 7_Campañas.py usa para publicaciones standalone
- **n8n social-scheduler → social_posts:** Cron job busca posts pendientes cuyo `scheduled_at <= now()` y dispara la publicación

</code_context>

<specifics>
## Specific Ideas

- El Paso 3 en 7_Campañas.py es **opcional** — si no se activa el checkbox, el comportamiento de Fase 5 es idéntico, sin ninguna regresión
- **MOCK_SOCIAL=true** permite que el admin pruebe el flujo completo (incluyendo estado en BD, UI, etc.) antes de que llegue la aprobación de Meta — esto es la validación real del core value
- Caption del post social puede ser diferente al mensaje WA — no copiar automáticamente entre los dos

</specifics>

<deferred>
## Deferred Ideas

- TikTok y X (Twitter) autoposting — ya en Out of Scope (REQUIREMENTS.md): API de TikTok requiere aprobación; X tiene límites agresivos en tier gratuito
- Preview del post como se vería en Instagram (simulación) — v2
- Métricas de engagement de posts (likes, comentarios) — Fase 7 Dashboard

</deferred>

---

*Phase: 06-social-media-publishing*
*Context gathered: 2026-04-13*
*Schema correction applied: 2026-04-13 (RESEARCH.md A1)*
