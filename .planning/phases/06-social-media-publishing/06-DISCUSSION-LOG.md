# Phase 6: Social Media Publishing - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-13
**Phase:** 06-social-media-publishing
**Mode:** discuss
**Areas discussed:** Meta API / Fallback, Flujo campaña unificada, Página de publicaciones, Imágenes — upload y storage

---

## Gray Areas Presented

| Area | Relevance |
|------|-----------|
| Meta API / Fallback | Bloqueador crítico: Meta App Review pendiente desde Fase 1 |
| Flujo campaña unificada | Core value del producto: una acción, dos canales |
| Página de publicaciones | SOCIAL-01 requiere programación standalone |
| Imágenes — upload y storage | Los posts requieren imagen; decisión de storage afecta n8n |

---

## Decisions Made

### Meta API / Fallback
- **Question:** La Meta App Review está pendiente. ¿Cómo publicamos en Instagram/Facebook sin aprobación?
- **Decision:** Meta Graph API real + env `MOCK_SOCIAL=true` como stub mientras llega aprobación
- **Rationale:** Construir el workflow real desde el principio; flipping una env var activa el sistema en producción sin cambios de código

### Flujo Campaña Unificada
- **Question:** ¿Cómo fluye la "una sola acción = WA + social" en la UI?
- **Decision:** Extender 7_Campañas.py con Paso 3 opcional (checkbox "Publicar en redes también")
- **Rationale:** Reutiliza la UI de Fase 5 sin duplicación. Si el checkbox está desactivado, el comportamiento de Fase 5 es idéntico — sin regressions.

### Página de Publicaciones
- **Question:** ¿Posts standalone viven en página separada?
- **Decision:** Nueva página 8_Publicaciones.py con lista de publicaciones + composer
- **Rationale:** SOCIAL-01 y SOCIAL-03 requieren visibilidad del estado de publicaciones. El flujo unificado también escribe en scheduled_posts, por lo que esta página muestra ambos orígenes.

### Imágenes — Upload y Storage
- **Question:** ¿Cómo se sube y almacena la imagen para que n8n la use?
- **Decision:** Streamlit file_uploader → volumen Docker /opt/clinic-crm/uploads/ (nombre: {uuid4}.{ext})
- **Rationale:** Accesible por Streamlit y n8n desde el mismo volumen Docker compartido. Caddy puede servir los archivos como static si Meta API requiere URL pública.

---

## No Corrections Made

Todas las decisiones recomendadas fueron aceptadas.

---

## Scope Creep Deflected

- Ninguno en esta sesión.
