---
name: send-buttons-type-field-missing
status: resolved
trigger: me da error al quererme presentar los botones de whatsapp en el modulo send buttons message, del sub flujo sub-send-wa-message
created: 2026-05-14
updated: 2026-05-14
---

## Symptoms

- **Expected:** Módulo `send buttons message` en `sub-send-wa-message` envía mensaje con 3 botones de respuesta rápida a WhatsApp vía Evolution API
- **Actual:** Error HTTP 400 de Evolution API: `buttons[0] requires property "type"` (y lo mismo para buttons[1] y buttons[2])
- **Error:** `400 - {"status":400,"error":"Bad Request","response":{"message":[["buttons[0] requires property \"type\"","buttons[1] requires property \"type\"","buttons[2] requires property \"type\""]]}}`
- **Timeline:** Nunca ha funcionado — es nuevo
- **Reproduction:** Ejecutando el chatbot con un mensaje que dispara los botones

## Request Body Being Sent (old format — v1 style)

```json
{
  "number": "50378422032@s.whatsapp.net",
  "title": "¿En qué puedo ayudarte?",
  "description": "Selecciona una opción para continuar:",
  "footer": "Clínica Dermatológica",
  "buttons": [
    { "buttonId": "promo_precios", "buttonText": { "displayText": "Precios / Promo" } },
    { "buttonId": "horarios_ubicacion", "buttonText": { "displayText": "Horarios / Ubicación" } },
    { "buttonId": "agendar_cita", "buttonText": { "displayText": "Agendar cita" } }
  ]
}
```

## Pre-Investigation Findings

- **File on disk** (`n8n/workflows/sub-send-wa-message.json`) has the FIXED format from commit `7d717de`:
  `{ type: 'reply', reply: { id: 'promo_precios', title: 'Precios / Promo' } }`
- **Running n8n instance** still uses the OLD format (not reimported after the commit)
- **Hypothesis:** Root cause is that the updated workflow JSON was never imported into the running n8n instance

## Current Focus

- hypothesis: RESOLVED — see Resolution section
- next_action: None

## Evidence

- timestamp: 2026-05-14T00:00:00Z
  type: error
  content: Evolution API returns 400 with "buttons[0] requires property type" — payload lacks `type` field
- timestamp: 2026-05-14T00:00:01Z
  type: observation
  content: git show 7d717de confirms n8n/workflows/sub-send-wa-message.json was updated to `{ type: reply, reply: { id, title } }` format
- timestamp: 2026-05-14T00:00:02Z
  type: observation
  content: Error request body shows old { buttonId, buttonText } format still being sent by n8n
- timestamp: 2026-05-14T07:15:00Z
  type: observation
  content: Running n8n DB (SQLite) inspection shows workflow already has commit 7d717de format `{ type reply, reply { id, title } }` — pre-investigation hypothesis was wrong, the workflow WAS imported
- timestamp: 2026-05-14T07:16:00Z
  type: observation
  content: Direct API test with `{ type reply, reply { id, title } }` format succeeds (HTTP 200) but buttonParamsJson is always `{}` — button id and title are silently dropped
- timestamp: 2026-05-14T07:17:00Z
  type: root_cause
  content: "Evolution API v2.3.7 message.schema.js validates buttons as flat objects: `{ type, displayText, id, url, phoneNumber, ... }`. The nested `reply: { id, title }` format is NOT the correct Evolution API v2 format — it is a WhatsApp Business API format that Baileys/Evolution does not map to."
- timestamp: 2026-05-14T07:18:00Z
  type: fix
  content: "Updated both disk JSON and running n8n SQLite DB to use flat format: `{ type: 'reply', displayText: 'Precios / Promo', id: 'promo_precios' }`. Restarted n8n container. Verified: all 3 buttons send with correct display_text and id in buttonParamsJson."

## Eliminated

- Hypothesis: workflow not imported after fix commit — ELIMINATED. DB inspection showed 7d717de format was already live.
- Hypothesis: `{ type, reply: { id, title } }` is correct v2 format — ELIMINATED. Schema shows flat structure required.

## Resolution

- **root_cause:** Commit 7d717de fixed the v1 `{ buttonId, buttonText }` format but introduced a second incorrect format `{ type: 'reply', reply: { id, title } }`. Evolution API v2.3.7 requires a flat button object: `{ type: 'reply', displayText: '...', id: '...' }`. The nested `reply` sub-object is silently ignored, resulting in empty `buttonParamsJson: "{}"` in the WhatsApp message.
- **fix:** Updated `Send Buttons Message` node jsonBody in both `n8n/workflows/sub-send-wa-message.json` (disk) and the running n8n SQLite database to use the correct flat format. Restarted n8n container to apply changes.
- **verified:** Direct Evolution API test confirms 3 buttons sent with correct `display_text` and `id` values in `buttonParamsJson`.

### Correct Button Format (Evolution API v2.3.7)

```json
{
  "type": "reply",
  "displayText": "Button Label",
  "id": "button_id"
}
```

### Wrong Formats

```json
// v1 format (old — fails with 400)
{ "buttonId": "id", "buttonText": { "displayText": "Label" } }

// commit 7d717de format (wrong — accepted but silently drops id/title)
{ "type": "reply", "reply": { "id": "id", "title": "Label" } }
```
