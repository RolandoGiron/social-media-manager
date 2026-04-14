---
status: diagnosed
trigger: "n8n recibe webhook de Evolution API y ejecuta el flujo del chatbot, pero los mensajes/conversaciones NO se persisten en PostgreSQL. El Inbox de la app muestra 'No hay conversaciones abiertas' porque la DB esta vacia."
created: 2026-04-10T00:00:00Z
updated: 2026-04-10T00:00:00Z
---

## Current Focus

hypothesis: "Read Conversation State" Postgres node returns 0 items when SELECT finds no rows (new contact). The downstream IF node "Conversation Exists?" receives 0 items and produces 0 items on BOTH branches. Neither the true (existing conversation) nor false (Create New Conversation) path fires.
test: Static analysis of workflow JSON confirmed the executeQuery mode + IF node zero-item behavior
expecting: n/a - root cause confirmed
next_action: Return diagnosis

## Symptoms

expected: Cuando llega un mensaje de WhatsApp, n8n lo procesa Y guarda la conversacion/mensaje en PostgreSQL, para que el Inbox lo muestre.
actual: n8n ejecuta el flujo correctamente (hay ejecuciones visibles), pero la base de datos PostgreSQL no tiene registros de conversaciones/mensajes nuevos. The flow stops at the "Conversation Exists?" IF node — neither true nor false branch fires after "Read Conversation State" returns 0 rows for new contacts.
errors: Ningun error visible reportado por el usuario — el flujo ejecuta sin errores aparentes.
reproduction: Enviar un mensaje de WhatsApp desde un numero NUEVO (sin conversacion previa en DB) al numero conectado en Evolution API.
started: Los flujos acaban de ser importados/cargados (sesion reciente). No esta claro si alguna vez funciono.

## Eliminated

- hypothesis: n8n chatbot workflow is missing Postgres insert nodes for conversations/messages
  evidence: whatsapp-chatbot.json contains 5 Postgres nodes — Read Conversation State, Create New Conversation, Insert Inbound Message, Update Conversation State, Insert Bot Response Message. All correctly reference conversations and messages tables.
  timestamp: 2026-04-10

- hypothesis: Inbox Streamlit page queries wrong table or has filtering bug
  evidence: admin-ui/src/pages/5_Inbox.py calls fetch_conversations() which queries "conversations c LEFT JOIN patients p" with "WHERE c.state != 'closed'" — correct query against the right tables. The issue is upstream (no data reaches the DB).
  timestamp: 2026-04-10

- hypothesis: Stub workflow (whatsapp-message-stub) intercepts the webhook instead of the real chatbot
  evidence: User confirmed the stub workflow was never imported into n8n. The real chatbot workflow IS executing — user can see in n8n that "Read Conversation State" runs successfully.
  timestamp: 2026-04-10

## Evidence

- timestamp: 2026-04-10
  checked: All 7 n8n workflow JSON files in n8n/workflows/
  found: whatsapp-chatbot.json has full Postgres persistence chain (create conversation, insert inbound message, update state, insert bot response). The workflow design is correct.
  implication: The persistence logic exists in the workflow — the problem is downstream flow control.

- timestamp: 2026-04-10
  checked: "Read Conversation State" node configuration (lines 106-125 of whatsapp-chatbot.json)
  found: Uses operation "executeQuery" with a SELECT query that filters by wa_contact_id and state != 'closed'. For a new contact with no conversation in the DB, this returns 0 rows.
  implication: n8n Postgres executeQuery with 0 result rows outputs 0 items to the next node.

- timestamp: 2026-04-10
  checked: "Conversation Exists?" IF node configuration (lines 128-156)
  found: Checks if $json.id is "notEmpty" (string type, notEmpty operation). True branch goes to "Merge Conversation Data" (existing conversation). False branch goes to "Create New Conversation". But the IF node receives 0 items from the Postgres node when no rows are returned.
  implication: n8n IF nodes are item-level processors. 0 items in = 0 items out on ALL branches. The false branch (Create New Conversation) never fires because there are no items to evaluate, not because the condition evaluates to true.

- timestamp: 2026-04-10
  checked: Workflow connections (lines 884-895)
  found: Read Conversation State -> Conversation Exists? -> (true) Merge Conversation Data / (false) Create New Conversation. The branching logic is correct in intent but broken by the zero-item problem.
  implication: The workflow design assumed the Postgres node would always return at least 1 item (even if empty). It does not — executeQuery with 0 rows returns 0 items.

## Resolution

root_cause: The "Read Conversation State" Postgres node uses executeQuery mode. When the SELECT query finds no matching rows (new contact, no existing conversation), n8n's Postgres node outputs 0 items (empty array). The downstream "Conversation Exists?" IF node receives 0 items and — per n8n's item-level processing model — produces 0 items on both the true AND false branches. The "Create New Conversation" path (false branch) never fires because there are literally no items for the IF node to evaluate. The entire flow silently stops.
fix:
verification:
files_changed: []
