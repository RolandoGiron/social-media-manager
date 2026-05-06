# Estado de Auditoría MCP n8n

**Fecha:** 2026-04-25  
**MCP Server:** n8n v1.1.0 en https://n8n-dlyc.srv1533829.hstgr.cloud

## Configuración MCP

- `.mcp.json` configurado con `n8n-mcp` (tipo: http)
- Token activo: audience = `mcp-server-api`

## Workflows encontrados (10)

| ID | Nombre | Activo | Trigger Count | MCP Access |
|---|---|---|---|---|
| BHvg7aS40fuVcnDB | sub-faq-answer | Sí | 0 | NO |
| 82if5RiWKE1MS9mD | WhatsApp Connection Update Alert | Sí | 1 | NO |
| uiFvmqH5XVbIKJTe | sub-classify-intent | Sí | 0 | NO |
| XZJm5vNMPjW4dxrj | social-publish | Sí | 3 | NO |
| OIGLydhMfzLbjqGC | whatsapp-chatbot | Sí | 1 | NO |
| Kbza4AqP7yGpjPb6 | sub-send-wa-message | Sí | 0 | NO |
| j0Fxh8Gkcf7Nviya | campaign-blast | Sí | 1 | NO |
| EcYOvXc59CUXsCOJ | OpenClaw Telegram Notification | Sí | 1 | NO |
| P55vLec8JejChdTi | appointment-reminders | Sí | 1 | NO |
| pNtr6xprRTZ2snNf | sub-booking-flow | Sí | 0 | NO |

## Bloqueo actual

Todas las herramientas que requieren acceso al workflow (`get_workflow_details`, 
`execute_workflow`) retornan: "Workflow is not available in MCP. Enable MCP access in workflow settings."

El token MCP (`aud: mcp-server-api`) no puede usarse con la REST API de n8n
(que requiere `X-N8N-API-KEY`).

## Acción requerida

### Opción A: Habilitar MCP access por workflow (recomendado)
Para cada workflow en n8n UI:
1. Abrir el workflow
2. Ir a Settings (engranaje)
3. Activar "Make workflow available in MCP"
4. Guardar

### Opción B: Generar n8n API key
1. Ir a Settings > n8n API > Create API key
2. Compartir la key para usar REST API

## Herramientas MCP disponibles (16)

- search_workflows, execute_workflow, get_execution
- get_workflow_details, publish_workflow, unpublish_workflow
- search_nodes, get_node_types, get_suggested_nodes
- validate_workflow, create_workflow_from_code
- search_projects, search_folders, archive_workflow
- update_workflow, get_sdk_reference
