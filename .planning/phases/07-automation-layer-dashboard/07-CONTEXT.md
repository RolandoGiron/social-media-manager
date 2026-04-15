# Phase 7: Automation Layer + Dashboard - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Dos capacidades independientes entregadas en la misma fase:

1. **Recordatorios automáticos de citas (CAL-03):** Un n8n workflow cron que detecta citas próximas y envía WhatsApp automáticamente 24h y 1h antes, sin intervención del admin. Usa la columna `reminder_24h_sent` / `reminder_1h_sent` ya existente en la tabla `appointments`.

2. **Dashboard de métricas operativas (DASH-01, DASH-02, DASH-03):** Transformar el stub `1_Dashboard.py` en un dashboard real con KPI cards, gráfica de actividad y tabla de errores. Las métricas de entrega de campañas viven en `7_Campañas.py`.

Los workflows existentes (chatbot, campaign-blast, social-publish) NO se modifican. Esta fase solo añade el cron de recordatorios y construye la capa de visualización.

**Requisitos en scope:** CAL-03, DASH-01, DASH-02, DASH-03

</domain>

<decisions>
## Implementation Decisions

### Recordatorios de Citas — Contenido del Mensaje

- **D-01:** El texto del recordatorio se toma de `message_templates` usando `category = 'recordatorio'`. El workflow busca la primera plantilla activa con esa categoría. El admin la crea y categoriza desde la página de Plantillas existente — sin nueva UI, sin env vars adicionales.
- **D-02:** Variables que el workflow inyecta en el template: `{{nombre}}` (patient name), `{{tipo}}` (appointment_type), `{{fecha}}` (scheduled_at fecha formateada), `{{hora}}` (scheduled_at hora formateada). Los datos de la clínica (dirección, teléfono) van directamente en el cuerpo de la plantilla — el admin los escribe al crear la plantilla. Sin tabla `clinic_settings`, sin env vars de clínica.
- **D-03:** Formato de fecha/hora: usar zona horaria de México (America/Mexico_City, configurable via env var `TZ` ya presente). Formato legible: "lunes 20 de abril" + "10:00 AM".

### Recordatorios de Citas — Comportamiento de Fallo

- **D-04:** Ante fallo de envío WhatsApp: **1 reintento automático a los 30 segundos**. Si el segundo intento también falla: (a) registrar en `workflow_errors` con workflow_name='appointment-reminders', (b) marcar `reminder_Xh_sent = true` en la cita para evitar reintentos indefinidos. El admin ve el fallo en la tabla de errores del Dashboard.
- **D-05:** Frecuencia del cron: **cada 15 minutos**. La query busca citas donde `scheduled_at` esté entre `now() + interval '23h45m'` y `now() + interval '24h15m'` (para el recordatorio de 24h) y entre `now() + interval '45m'` y `now() + interval '1h15m'` (para el de 1h). Ventana de tolerancia: ±15 minutos. Aceptable para uso clínico.

### Dashboard — Layout y Métricas (DASH-01)

- **D-06:** `1_Dashboard.py` implementa: (1) fila de 4 tarjetas KPI, (2) gráfica de actividad de los últimos 7 días con dos series, (3) tabla de errores recientes de workflows. Sin paginación compleja en v1.
- **D-07:** Las 4 KPI cards son:
  - **Mensajes enviados** — total de mensajes en conversations (sent en los últimos 30 días)
  - **Bot resolution %** — conversaciones donde `human_handoff = false` / total conversaciones (período: últimos 30 días)
  - **Citas agendadas** — COUNT de appointments con status='confirmed' (últimos 30 días)
  - **Posts publicados** — COUNT de social_posts con status='published' (últimos 30 días)
- **D-08:** Período por defecto: **últimos 30 días**. Sin selector de rango en v1 (Claude's Discretion si el planner quiere añadirlo sin complejidad extra).
- **D-09:** La gráfica de actividad muestra **dos series en los últimos 7 días**: mensajes enviados por día + citas agendadas por día. Una línea por serie. La librería de charting es Claude's Discretion (st.line_chart, altair, o plotly; preferir la más simple).

### Dashboard — Error Log (DASH-03)

- **D-10:** La tabla de errores de n8n vive **al pie de `1_Dashboard.py`** (no es página separada). Columnas: Workflow, Nodo, Error (truncado), Hace cuánto tiempo. Muestra los últimos 20 errores ordenados por `created_at DESC`. Sin filtros en v1.
- **D-11:** El error log es de solo lectura. No hay acción de "marcar como resuelto" en v1.

### Analytics de Entrega por Campaña (DASH-02)

- **D-12:** Las métricas de entrega de campañas viven en **`7_Campañas.py`** como una nueva sección al final de la página, debajo del historial existente. No es una página separada.
- **D-13:** Vista: **tarjetas de campaña con barra de progreso visual**. Cada campaña reciente muestra:
  - Nombre de la campaña, fecha, segmento
  - Tres barras de progreso con porcentajes: % Enviado → % Entregado → % Leído
  - Totales numéricos junto a cada barra (ej: "48/50 entregados")
- **D-14:** Campañas a mostrar: las de los **últimos 30 días**, ordenadas por `created_at DESC`. El planner decide si paginar o mostrar las N más recientes (Claude's Discretion).
- **D-15:** Los datos vienen de `campaign_recipients` JOIN `campaign_log`. La query agrupa por `campaign_id` y cuenta por status (sent, delivered, read, failed).

### Claude's Discretion

- Librería de charting para la gráfica de actividad (st.line_chart vs altair vs plotly)
- Colores e iconos de las KPI cards
- Si añadir un simple selector de período (hoy / 7d / 30d) si resulta trivial implementarlo
- Diseño exacto de la barra de progreso en tarjetas de campaña (st.progress, CSS custom)
- Cantidad máxima de campañas a mostrar si no se pagina (sugerencia: últimas 10)
- Si mostrar detalle de destinatarios individuales al expandir una tarjeta de campaña

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Database Schema
- `postgres/init/001_schema.sql` líneas 88-106 — Tabla `appointments` con columnas `reminder_24h_sent`, `reminder_1h_sent` (boolean, base del cron de recordatorios)
- `postgres/init/001_schema.sql` líneas 120-157 — Tablas `campaign_log` + `campaign_recipients` con status enum (sent/delivered/read/failed) y timestamps
- `postgres/init/001_schema.sql` líneas 158-172 — Tabla `workflow_errors` (workflow_name, node_name, error_message, error_details jsonb, created_at)
- `postgres/init/001_schema.sql` — Tabla `conversations` con columna `human_handoff` boolean (para bot resolution %)
- `postgres/init/001_schema.sql` líneas 174-192 — Tabla `social_posts` con status (para KPI de posts publicados)

### Requirements
- `.planning/REQUIREMENTS.md` §CAL-03 — Recordatorio 24h + 1h antes de la cita
- `.planning/REQUIREMENTS.md` §DASH-01 — Métricas clave del sistema
- `.planning/REQUIREMENTS.md` §DASH-02 — Métricas de entrega por segmento
- `.planning/REQUIREMENTS.md` §DASH-03 — Log de errores de workflows n8n
- `.planning/ROADMAP.md` §Phase 7 — 4 success criteria definen el done

### Existing Admin UI (extend)
- `admin-ui/src/pages/1_Dashboard.py` — Stub actual (4 líneas); reemplazar por completo
- `admin-ui/src/pages/7_Campañas.py` — Extender con sección de delivery analytics al final
- `admin-ui/src/components/database.py` — Patrón `get_db_connection()` para queries
- `admin-ui/src/components/sidebar.py` — `render_sidebar()` al top de cada página

### Existing n8n Workflows (referencia de patrones)
- `n8n/workflows/campaign-blast.json` — Patrón de Schedule Trigger + query PostgreSQL + loop + status update; base para appointment-reminders.json
- `n8n/workflows/sub-send-wa-message.json` — Patrón de HTTP call a Evolution API para envío de mensaje WA; reutilizar en el workflow de recordatorios
- `n8n/workflows/whatsapp-chatbot.json` — Manejo de errores y reintentos como referencia

### Prior Phase Context
- `.planning/phases/05-campaign-blast/05-CONTEXT.md` — D-05 a D-15: flujo de campaign_log, estructura de campaign_recipients; las analytics de DASH-02 leen esos mismos datos
- `.planning/phases/06-social-media-publishing/06-CONTEXT.md` — D-02 a D-03: patrón de `social_posts` status update; KPI de posts publicados lee esa tabla

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `admin-ui/src/components/database.py` — `get_db_connection()` para todas las queries del dashboard
- `admin-ui/src/pages/7_Campañas.py` — Página multi-sección existente; agregar sección de analytics al final sin tocar el flujo de campaña existente
- `n8n/workflows/campaign-blast.json` — Schedule Trigger + PostgreSQL Query node + loop: plantilla directa para appointment-reminders.json
- `n8n/workflows/sub-send-wa-message.json` — Nodo HTTP Request a Evolution API; copiar para enviar recordatorio WA

### Established Patterns
- **Streamlit multipage:** Cada página usa `render_sidebar()` al inicio; 1_Dashboard.py debe seguir el mismo patrón
- **DB queries:** `get_db_connection()` + `cursor.execute()` + `cursor.fetchall()` — patrón uniforme en todas las páginas
- **n8n error logging:** El campo `workflow_errors` ya es usado por otros workflows; el cron de recordatorios debe escribir ahí también
- **Estado de cita como guard:** `reminder_24h_sent = true` actúa como idempotency guard — el mismo patrón que `social_posts.status = 'publishing'` en Phase 6

### Integration Points
- **n8n appointment-reminders → PostgreSQL appointments:** SELECT citas en ventana de tiempo, UPDATE reminder_Xh_sent después de enviar
- **n8n appointment-reminders → sub-send-wa-message:** Reuso del sub-workflow existente para el envío WA
- **1_Dashboard.py → PostgreSQL (conversations, appointments, campaign_log, social_posts, workflow_errors):** 5 queries separadas, cada una con filtro últimos 30 días
- **7_Campañas.py → campaign_recipients JOIN campaign_log:** Query de agregación por status para las tarjetas de progreso

</code_context>

<specifics>
## Specific Ideas

- El cron de recordatorios no necesita un nuevo endpoint webhook — es puro Schedule Trigger que corre en n8n, sin interacción desde Streamlit
- La tabla `message_templates` ya existe y tiene `category TEXT DEFAULT 'general'`. Solo se necesita que el admin cree una plantilla con `category = 'recordatorio'` desde la UI de Plantillas. No hay migraciones de schema requeridas.
- El `reminder_24h_sent` y `reminder_1h_sent` ya existen en la tabla `appointments` desde Phase 1 — la funcionalidad de recordatorios fue anticipada en el schema original
- Para las barras de progreso en tarjetas de campaña, `st.progress(value)` de Streamlit acepta float 0.0–1.0 y es suficiente para v1 sin CSS custom
- El Dashboard en v1 no necesita auto-refresh (a diferencia del Inbox que usa streamlit_autorefresh) — las métricas de negocio no requieren actualización en tiempo real

</specifics>

<deferred>
## Deferred Ideas

- Selector de rango de fechas interactivo (hoy / 7d / 30d / personalizado) — si las 4 KPI cards son suficientes con 30 días fijo, no añadir
- Vista de detalle por destinatario individual dentro de cada tarjeta de campaña — tabla de pacientes con status individual queda para v2
- Notificación push al admin cuando hay un error de workflow — el log en Dashboard es suficiente para v1
- Métricas de engagement de posts (likes, comentarios via Meta API) — depende de App Review aprobado; v2
- Export CSV de métricas del dashboard — v2
- Auto-refresh del dashboard (polling cada 5s) — no necesario; el admin puede refrescar manualmente

</deferred>

---

*Phase: 07-automation-layer-dashboard*
*Context gathered: 2026-04-15*
