# Requirements: AI Social Media Manager & CRM

**Defined:** 2026-03-27
**Core Value:** El dueño de la clínica puede lanzar una promoción dirigida — que llega a WhatsApp de los pacientes relevantes Y se publica en redes sociales — sin tocar ningún sistema manualmente.

---

## v1 Requirements

### Infrastructure & WhatsApp Session (INFRA)

- [x] **INFRA-01**: Administrador puede conectar/reconectar sesión WhatsApp de la clínica escaneando QR desde la UI
- [x] **INFRA-02**: Sistema muestra estado de sesión WhatsApp (conectada/desconectada) visible en todo momento
- [x] **INFRA-03**: Sistema detecta automáticamente desconexión de sesión y envía alerta al administrador

### CRM — Gestión de Pacientes (CRM)

- [x] **CRM-01**: Administrador puede importar pacientes desde archivo CSV/Excel con normalización automática de números telefónicos (formato MX +52) y detección de duplicados
- [x] **CRM-02**: Administrador puede ver lista paginada de pacientes con búsqueda por nombre/teléfono y filtro por segmento/etiqueta
- [x] **CRM-03**: Administrador puede crear etiquetas personalizadas y asignarlas a pacientes para segmentación (ej: acné, rosácea, facial, postoperatorio)

### WhatsApp — Mensajería y Campañas (WA)

- [x] **WA-01**: Administrador puede crear plantillas de mensaje con variables dinámicas ({{nombre}}, {{fecha}}) y previsualizar antes de guardar
- [ ] **WA-02**: Administrador puede enviar broadcast masivo a un segmento de pacientes seleccionado, con rate limiting automático (delays con jitter) para prevenir baneo de número
- [ ] **WA-03**: Sistema muestra paso de confirmación antes de envío masivo indicando número de destinatarios ("Estás a punto de enviar a N pacientes. ¿Confirmar?")
- [ ] **WA-04**: Administrador puede cancelar un broadcast en progreso

### Chatbot — IA Conversacional (BOT)

- [x] **BOT-01**: Chatbot responde automáticamente preguntas frecuentes de pacientes (horarios, ubicación, precios, servicios) usando RAG sobre el knowledge base de la clínica
- [ ] **BOT-02**: Chatbot escala conversación a humano cuando no encuentra respuesta en el knowledge base o detecta pregunta médica/queja — envía mensaje de handoff al paciente
- [x] **BOT-03**: Administrador puede ver bandeja de conversaciones con historial completo (mensajes del bot y del paciente) y responder manualmente desde la UI
- [ ] **BOT-04**: Chatbot muestra indicador de "escribiendo..." (typing indicator) mientras procesa la respuesta del LLM

### Citas — Google Calendar (CAL)

- [x] **CAL-01**: Chatbot puede consultar disponibilidad en Google Calendar de la clínica y agendar cita sin intervención humana, usando Service Account (sin expiración de token)
- [ ] **CAL-02**: Sistema envía mensaje de confirmación de cita por WhatsApp al paciente con fecha, hora y datos de la clínica
- [ ] **CAL-03**: Sistema envía recordatorio automático por WhatsApp 24 horas y 1 hora antes de la cita agendada

### Social Media — Publicación (SOCIAL)

- [ ] **SOCIAL-01**: Administrador puede programar publicación en Instagram y Facebook con imagen y caption para fecha/hora específica
- [ ] **SOCIAL-02**: Sistema dispara trigger unificado que ejecuta simultáneamente: broadcast WhatsApp al segmento seleccionado + publicación en redes sociales desde una sola acción del administrador
- [ ] **SOCIAL-03**: Administrador puede ver estado de cada publicación programada (pendiente, publicado, error)

### Dashboard y Analítica (DASH)

- [ ] **DASH-01**: Administrador puede ver métricas clave: total mensajes enviados, porcentaje de consultas resueltas por el bot, citas agendadas, posts publicados
- [ ] **DASH-02**: Administrador puede ver métricas de entrega por segmento: cuántos pacientes del segmento X recibieron/leyeron la campaña
- [ ] **DASH-03**: Administrador puede ver log de errores de workflows de n8n para diagnóstico operativo

---

## v2 Requirements

### Engagement y Retención

- **ENG-01**: Sistema envía mensaje de seguimiento automático a paciente N horas después de una cita (solicitar reseña Google o re-agendamiento)
- **ENG-02**: Sistema genera copy e imagen para promociones usando IA (GPT/DALL-E) con posibilidad de editar antes de enviar

### Cumplimiento y Privacidad

- **PRIV-01**: Administrador puede registrar consentimiento de comunicación por paciente (opt-in/opt-out) con exclusión automática de broadcasts
- **PRIV-02**: Sistema mantiene log de auditoría de quién envió qué campaña y cuándo

### Escalabilidad

- **SCALE-01**: Sistema soporta múltiples clínicas (multi-tenant) con aislamiento de datos por clínica
- **SCALE-02**: Administrador puede gestionar múltiples números de WhatsApp (una sesión por clínica)

---

## Out of Scope

| Feature | Razón |
|---------|-------|
| Expediente médico / historial clínico completo | Riesgo regulatorio (NOM-024 MX), explosión de scope — solo datos de contacto y segmentación |
| Cobros / pagos en la plataforma | Requiere PSP, PCI compliance; delegar a link externo si necesario |
| App móvil nativa | Web-first; PWA o responsivo como bridge — app nativa en v3+ |
| TikTok y X (Twitter) autoposting | API de TikTok requiere aprobación; formato video no encaja con workflow de imagen estática; X tiene límites agresivos en tier gratuito |
| BI analytics avanzado / Metabase | Métricas simples satisfacen MVP; embedding de Metabase si el dueño lo pide en v2 |
| Chatbot para quejas, reembolsos, reclamaciones | LLM en contexto médico-financiero es riesgo legal — escalar siempre a humano para estos casos |
| Websocket push en tiempo real para inbox | Polling cada 5-10s es suficiente para el volumen de una clínica; añadir WS si la UX lo requiere |

---

## Traceability

| Requirement | Phase | Phase Name | Status |
|-------------|-------|------------|--------|
| INFRA-01 | Phase 2 | WhatsApp Core | Pending |
| INFRA-02 | Phase 2 | WhatsApp Core | Pending |
| INFRA-03 | Phase 2 | WhatsApp Core | Pending |
| CRM-01 | Phase 3 | CRM Core | Pending |
| CRM-02 | Phase 3 | CRM Core | Pending |
| CRM-03 | Phase 3 | CRM Core | Pending |
| WA-01 | Phase 3 | CRM Core | Pending |
| WA-02 | Phase 5 | Campaign Blast | Pending |
| WA-03 | Phase 5 | Campaign Blast | Pending |
| WA-04 | Phase 5 | Campaign Blast | Pending |
| BOT-01 | Phase 4 | AI Chatbot + Appointment Booking | Pending |
| BOT-02 | Phase 4 | AI Chatbot + Appointment Booking | Pending |
| BOT-03 | Phase 4 | AI Chatbot + Appointment Booking | Pending |
| BOT-04 | Phase 4 | AI Chatbot + Appointment Booking | Pending |
| CAL-01 | Phase 4 | AI Chatbot + Appointment Booking | Pending |
| CAL-02 | Phase 4 | AI Chatbot + Appointment Booking | Pending |
| CAL-03 | Phase 7 | Automation Layer + Dashboard | Pending |
| SOCIAL-01 | Phase 6 | Social Media Publishing | Pending |
| SOCIAL-02 | Phase 6 | Social Media Publishing | Pending |
| SOCIAL-03 | Phase 6 | Social Media Publishing | Pending |
| DASH-01 | Phase 7 | Automation Layer + Dashboard | Pending |
| DASH-02 | Phase 7 | Automation Layer + Dashboard | Pending |
| DASH-03 | Phase 7 | Automation Layer + Dashboard | Pending |

**Coverage:**
- v1 requirements: 23 total
- Mapped to phases: 23
- Unmapped: 0 ✓

**Note:** Phase 1 (Infrastructure Foundation) has no formal requirements — it delivers the Docker Compose stack, database schema, and Meta App Review submission that are prerequisites for all subsequent phases.

---
*Requirements defined: 2026-03-27*
*Last updated: 2026-03-27 after roadmap creation*
