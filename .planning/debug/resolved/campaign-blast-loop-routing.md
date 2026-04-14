---
status: resolved
trigger: "campaign-blast-loop-routing — Loop Recipients skips Check Cancelled and jumps to Finalize Status"
created: 2026-04-13T00:00:00Z
updated: 2026-04-13T13:30:00Z
---

## Current Focus

status: RESOLVED — user confirmed fix works end-to-end. Workflow sends WhatsApp messages correctly.
next_action: none — session archived.

## Symptoms

expected: After "Loop Recipients" (Loop Branch with 1 item), flow goes through "Check Cancelled" → send WhatsApp → back to loop. Finalize Status only runs when all items processed.
actual: Loop Branch with 1 item jumps directly to "Finalize Status", skipping Check Cancelled and the send flow. No errors; UPDATE status='completed' fires immediately.
errors: None visible — flow "succeeds" without sending messages
reproduction: Execute campaign-blast workflow with any active campaign
started: Current issue, identified during this execution

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-04-13T13:00:00Z
  checked: n8n/workflows/campaign-blast.json — Wait Jitter node configuration
  found: |
    "wait-jitter" node parameters:
      "amount": "={{ $json.delay_ms }}"
      "unit": "ms"
    n8n Wait node (typeVersion 1.1) valid units per Wait.node.ts:524 error message:
      'seconds', 'minutes', 'hours', 'days'
    "ms" is NOT a valid unit. Compute Jitter produces delay_ms = 3000-8000 (milliseconds),
    intending a 3-8 second wait between sends.
  implication: |
    The unit "ms" was a design mistake — n8n Wait does not support sub-second waits.
    Fix: convert delay_ms to delay_seconds in Compute Jitter and use unit="seconds" in Wait Jitter.
    This preserves the 3-8 second jitter semantics (Math.ceil ensures minimum 3s).



- timestamp: 2026-04-13T12:00:00Z
  checked: n8n/workflows/campaign-blast.json — all $() expressions in node parameters
  found: |
    Line 146 (Merge Recipient and Status code node):
      const recipient = $('loop-recipients').item.json;
    All other $() references use proper node display names:
      $('Merge Recipient and Status') — exists ✓
      $('Load Recipients') — exists ✓
    The string 'loop-recipients' is the node `id` field, not its `name`. The node's name is "Loop Recipients" (capitalized, with space).
  implication: n8n's $() proxy looks up nodes by display name. Passing the id string yields a "Referenced node doesn't exist" error. n8n then tries to set `.name` on the Error object to enrich the stack trace, but the Error's `name` property is read-only in this context, producing the observed TypeError "Cannot assign to read only property 'name' of object 'Error: Referenced node doesn't exist'".

- timestamp: 2026-04-13T00:00:00Z
  checked: n8n/workflows/campaign-blast.json — Loop Recipients connections
  found: |
    "Loop Recipients": {
      "main": [
        [ { "node": "Check Cancelled", "index": 0 } ],   // output index 0
        [ { "node": "Finalize Status", "index": 0 } ]    // output index 1
      ]
    }
  implication: Output index 0 is wired to Check Cancelled, output index 1 is wired to Finalize Status.

- timestamp: 2026-04-13T00:00:00Z
  checked: n8n SplitInBatches v3 output semantics
  found: In n8n SplitInBatches (typeVersion 3), main output index 0 = "done" (emitted once when all batches complete), and main output index 1 = "loop" (emitted for each batch).
  implication: Current wiring means "done" → Check Cancelled and "loop" → Finalize Status. This is inverted. The symptom description ("Loop Branch (1 item) lands on Finalize Status") confirms output[1] is the per-item loop branch, and it is wired to Finalize Status.

## Resolution

root_cause: |
  Three sequential bugs in campaign-blast.json:
  (1) Loop Recipients SplitInBatches v3 outputs were swapped — output 0 (done) was wired to Check Cancelled and output 1 (loop) to Finalize Status. Fixed previously.
  (2) The "Merge Recipient and Status" Code node referenced the loop node as $('loop-recipients'), which is the node's internal `id` field. n8n's $() proxy resolves nodes by display `name`, not by id. Fixed previously.
  (3) Wait Jitter node was configured with unit="ms" — not a valid n8n Wait unit. The Wait node only accepts 'seconds', 'minutes', 'hours', 'days'. Compute Jitter was emitting delay_ms (3000-8000 ms), intending 3-8 second waits, but passing it with unit "ms" crashed at Wait.node.ts:524 with "Invalid wait unit".
fix: |
  (1) Swapped Loop Recipients outputs so output[0] → Finalize Status, output[1] → Check Cancelled.
  (2) Changed $('loop-recipients') to $('Loop Recipients') in Merge Recipient and Status.
  (3) Compute Jitter now also emits delay_seconds = Math.ceil(delay_ms / 1000). Wait Jitter now uses amount={{ $json.delay_seconds }} and unit="seconds", preserving the 3-8 second jitter semantics.
verification: |
  Static inspection of the updated JSON confirms:
  - Wait Jitter parameters: amount = "={{ $json.delay_seconds }}", unit = "seconds" ✓
  - Compute Jitter emits both delay_ms (legacy) and delay_seconds (new) on the item.
  - delay_seconds is Math.ceil(delay_ms / 1000) so minimum wait is 3s, maximum is 8s — matches original intent.
  Runtime verification requires re-importing the workflow in n8n and running it against an active campaign.
files_changed:
  - n8n/workflows/campaign-blast.json
