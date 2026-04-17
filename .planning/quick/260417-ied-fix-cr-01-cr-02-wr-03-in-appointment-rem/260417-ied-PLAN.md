---
type: quick
task_id: 260417-ied
title: Fix CR-01, CR-02, WR-03 in appointment-reminders workflow and database.py
source: .planning/phases/07-automation-layer-dashboard/07-VERIFICATION.md
autonomous: true
files_modified:
  - n8n/workflows/appointment-reminders.json
  - admin-ui/src/components/database.py
must_haves:
  truths:
    - "No hardcoded Evolution API key value remains in appointment-reminders.json"
    - "All six Postgres executeQuery nodes use n8n's =\\{\\{ \\}\\} expression syntax"
    - "fetch_dashboard_kpis bot_resolution_pct query uses conversations.state enum, not human_handoff boolean"
    - "Valid JSON is preserved in appointment-reminders.json (parses cleanly)"
    - "database.py remains importable with the same public function signature"
  artifacts:
    - path: "n8n/workflows/appointment-reminders.json"
      provides: "appointment reminders workflow with env-var API key and correct n8n expression syntax"
      contains: "={{ $env.EVOLUTION_API_KEY }}"
    - path: "admin-ui/src/components/database.py"
      provides: "fetch_dashboard_kpis with schema-correct bot_resolution_pct query"
      contains: "state != 'human_handoff'"
  key_links:
    - from: "n8n/workflows/appointment-reminders.json Send 24h/1h WA Reminder nodes"
      to: "Evolution API credentials"
      via: "={{ $env.EVOLUTION_API_KEY }} n8n expression"
      pattern: "\\$env\\.EVOLUTION_API_KEY"
    - from: "n8n/workflows/appointment-reminders.json Postgres executeQuery nodes"
      to: "appointments / workflow_errors tables"
      via: "n8n =\\{\\{ \\}\\} expression interpolation"
      pattern: "\"query\":\\s*\"[^\"]*=\\{\\{"
    - from: "admin-ui/src/components/database.py fetch_dashboard_kpis"
      to: "conversations.state column"
      via: "COUNT(*) FILTER (WHERE state != 'human_handoff')"
      pattern: "state\\s*!=\\s*'human_handoff'"
---

<objective>
Fix three review findings from Phase 7 verification so the appointment-reminders
workflow can be activated safely and the dashboard KPI reports correct data:

- CR-01 (CRITICAL): Remove hardcoded Evolution API key `Jehova01` from the n8n
  workflow JSON (lines 192, 241) and replace with an n8n expression that reads
  from the environment variable `EVOLUTION_API_KEY`.
- CR-02 (CRITICAL): Fix six Postgres `executeQuery` nodes (lines 354, 372, 390,
  408, 426, 444) that use bare Mustache `{{ }}` syntax instead of n8n's
  `={{ }}` expression syntax.
- WR-03 (WARNING): Fix `fetch_dashboard_kpis` in `admin-ui/src/components/database.py`
  (line ~823) so the bot-resolution query uses the actual schema
  (`conversations.state` enum with value `'human_handoff'`) instead of a
  non-existent boolean column `human_handoff`.

Purpose: Unblock appointment-reminders activation (CR-01 + CR-02 are listed as
must-fix-before-activation in `07-VERIFICATION.md`) and eliminate the silent
0.0 fallback on the Dashboard's `bot_resolution_pct` KPI.

Output:
- Updated `n8n/workflows/appointment-reminders.json` (valid JSON, no hardcoded
  secret, correct expression syntax in all six Postgres nodes).
- Updated `admin-ui/src/components/database.py` with schema-correct KPI query.
- Clear note to the human that the `Jehova01` key must also be rotated in the
  Evolution API admin panel (out of scope for the code change).
</objective>

<execution_context>
@/home/rolando/Desarrollo/social-media-manager/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/phases/07-automation-layer-dashboard/07-VERIFICATION.md
@.planning/phases/07-automation-layer-dashboard/07-REVIEW.md
@n8n/workflows/appointment-reminders.json
@admin-ui/src/components/database.py
@postgres/init/001_schema.sql

<interfaces>
<!-- Confirmed schema from postgres/init/001_schema.sql (loaded during planning). -->
<!-- Executor should use these directly — no further exploration needed. -->

From postgres/init/001_schema.sql (conversations table, lines 52-63):

```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE SET NULL,
    wa_contact_id TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'new'
        CHECK (state IN ('new', 'awaiting_intent', 'faq_flow', 'booking_flow', 'human_handoff', 'closed')),
    context JSONB DEFAULT '{}',
    assigned_agent TEXT,
    last_message_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

There is NO `human_handoff` boolean column. The correct predicate for
"bot-resolved" conversations is `state != 'human_handoff'` (and optionally
exclude `'closed'` if desired — but to keep this fix minimal and match the
reviewer's recommendation verbatim, use `state != 'human_handoff'`).

From n8n/workflows/appointment-reminders.json (HTTP node shape at lines 180-221):

```json
"headerParameters": {
  "parameters": [
    { "name": "apikey", "value": "Jehova01" },
    { "name": "Content-Type", "value": "application/json" }
  ]
}
```

The fix pattern is to change the `value` field of the `apikey` header to the
n8n expression `={{ $env.EVOLUTION_API_KEY }}`. The `$env` accessor reads
environment variables injected into the n8n container; `EVOLUTION_API_KEY` is
already present in the project's `.env` and Docker Compose env config per the
Phase 2 Evolution API integration.

From n8n/workflows/appointment-reminders.json (Postgres executeQuery query field):

Current (BROKEN — bare Mustache):
```
"query": "UPDATE appointments\nSET reminder_24h_sent = true, updated_at = now()\nWHERE id = '{{ $('Render 24h Message').item.json.appointment_id }}'::uuid"
```

Correct (n8n expression):
```
"query": "=UPDATE appointments\nSET reminder_24h_sent = true, updated_at = now()\nWHERE id = '{{ $('Render 24h Message').item.json.appointment_id }}'::uuid"
```

In n8n, prefixing the entire string value with `=` turns it into an evaluated
expression; the `{{ ... }}` blocks inside are then resolved. This is the
smallest fix that preserves the existing query text. Apply the `=` prefix to
the query string in all six affected nodes (Mark 24h Sent, Mark 1h Sent, Log
24h Failure, Log 1h Failure, Mark 24h Sent After Failure, Mark 1h Sent After
Failure).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Replace hardcoded Evolution API key with env-var expression (CR-01)</name>
  <files>n8n/workflows/appointment-reminders.json</files>
  <action>
In `n8n/workflows/appointment-reminders.json`, locate the two occurrences of the
`apikey` header with the literal value `"Jehova01"`:

- Line ~192: inside the `Send 24h WA Reminder` node (id `a1b2c3d4-0011-...`).
- Line ~241: inside the `Send 1h WA Reminder` node (id `a1b2c3d4-0012-...`).

Replace the literal value `"Jehova01"` with the n8n expression
`"={{ $env.EVOLUTION_API_KEY }}"` in both locations. Do NOT change any other
field (node ids, positions, retry config, URL, body parameters, or content-type
header must stay identical).

Example of the exact edit (both Send nodes):

Before:
```json
{
  "name": "apikey",
  "value": "Jehova01"
}
```

After:
```json
{
  "name": "apikey",
  "value": "={{ $env.EVOLUTION_API_KEY }}"
}
```

After the edit, verify the file is still valid JSON and confirm the literal
string `Jehova01` no longer appears anywhere in the file.

IMPORTANT — human follow-up (NOT part of this task, note it in the task summary):
The `Jehova01` key is already in git history. The human must rotate the key in
the Evolution API admin panel (regenerate/replace the API key, then update the
`EVOLUTION_API_KEY` value in `.env` / Docker Compose env) to close the
exposure window. The code change alone does NOT rotate the key.
  </action>
  <verify>
    <automated>python3 -c "import json; json.load(open('n8n/workflows/appointment-reminders.json'))" &amp;&amp; ! grep -q 'Jehova01' n8n/workflows/appointment-reminders.json &amp;&amp; [ "$(grep -c '={{ \$env.EVOLUTION_API_KEY }}' n8n/workflows/appointment-reminders.json)" = "2" ]</automated>
  </verify>
  <done>
- File parses as valid JSON.
- String `Jehova01` does not appear anywhere in the file.
- Expression `={{ $env.EVOLUTION_API_KEY }}` appears exactly 2 times (one per
  Send node).
- No other fields changed (spot-check: node ids, URLs, body parameters unchanged).
  </done>
</task>

<task type="auto">
  <name>Task 2: Fix n8n expression syntax in six Postgres executeQuery nodes (CR-02)</name>
  <files>n8n/workflows/appointment-reminders.json</files>
  <action>
In `n8n/workflows/appointment-reminders.json`, six Postgres nodes have a
`parameters.query` string that starts with raw SQL and contains `{{ ... }}`
Mustache-style placeholders. In n8n, the entire string value must be prefixed
with `=` for n8n to evaluate the `{{ ... }}` blocks as expressions. Without
the `=` prefix, n8n passes the literal text (including the braces) to
Postgres, which causes UPDATEs to not match any rows and INSERTs to write
literal `{{ ... }}` placeholders into `workflow_errors`.

For each of the six nodes, prefix the `query` value with `=` (single leading
equals sign). Leave the rest of the string (including all `{{ ... }}`
expressions, newlines, and casts) exactly as-is.

Nodes to edit (by `name` and approximate line of the `query` value):

1. `Mark 24h Sent` — line ~354 (UPDATE appointments ... reminder_24h_sent).
2. `Mark 1h Sent` — line ~372 (UPDATE appointments ... reminder_1h_sent).
3. `Log 24h Failure` — line ~390 (INSERT INTO workflow_errors ... 24h).
4. `Log 1h Failure` — line ~408 (INSERT INTO workflow_errors ... 1h).
5. `Mark 24h Sent After Failure` — line ~426 (UPDATE appointments ... 24h).
6. `Mark 1h Sent After Failure` — line ~444 (UPDATE appointments ... 1h).

Example of the edit (Mark 24h Sent):

Before:
```json
"query": "UPDATE appointments\nSET reminder_24h_sent = true, updated_at = now()\nWHERE id = '{{ $('Render 24h Message').item.json.appointment_id }}'::uuid",
```

After:
```json
"query": "=UPDATE appointments\nSET reminder_24h_sent = true, updated_at = now()\nWHERE id = '{{ $('Render 24h Message').item.json.appointment_id }}'::uuid",
```

Apply the same single-character `=` prefix to the other five `query` values.
Do not alter any other field (operation, options, credentials, node ids,
positions). Do not collapse or reformat the multi-line strings.

Scope note: This plan intentionally does NOT address WR-01 (Mark Sent After
Failure marking reminders as sent on delivery failure) — that is a separate
finding and is explicitly out of scope for this quick fix. We only correct the
expression syntax so the existing SQL actually executes.
  </action>
  <verify>
    <automated>python3 -c "import json,sys; d=json.load(open('n8n/workflows/appointment-reminders.json')); nodes=[n for n in d['nodes'] if n.get('type')=='n8n-nodes-base.postgres' and n.get('parameters',{}).get('operation')=='executeQuery']; assert len(nodes)==6, f'expected 6 executeQuery nodes, got {len(nodes)}'; bad=[n['name'] for n in nodes if not n['parameters']['query'].startswith('=')]; assert not bad, f'nodes missing = prefix: {bad}'; print('OK:', [n['name'] for n in nodes])"</automated>
  </verify>
  <done>
- All six Postgres `executeQuery` node `query` values start with `=`.
- The rest of each query string (the `{{ ... }}` placeholders, SQL, casts,
  newlines) is unchanged.
- File still parses as valid JSON.
- No additional `=` prefixes were accidentally added to any other query in the
  file.
  </done>
</task>

<task type="auto">
  <name>Task 3: Fix bot_resolution_pct query to use conversations.state enum (WR-03)</name>
  <files>admin-ui/src/components/database.py</files>
  <action>
In `admin-ui/src/components/database.py`, update the `fetch_dashboard_kpis`
function (around line 819-833). The current query references a non-existent
boolean column `human_handoff`:

```python
cur.execute(
    """
    SELECT
        COUNT(*) FILTER (WHERE human_handoff = false) AS bot_resolved,
        COUNT(*) AS total
    FROM conversations
    WHERE created_at >= now() - interval '1 day' * %s
    """,
    (days,),
)
```

The actual schema (confirmed in `postgres/init/001_schema.sql` lines 52-63)
has `state TEXT NOT NULL` with CHECK values including `'human_handoff'`. Replace
the filter predicate so "bot-resolved" = any conversation whose `state` is not
`'human_handoff'`:

```python
cur.execute(
    """
    SELECT
        COUNT(*) FILTER (WHERE state != 'human_handoff') AS bot_resolved,
        COUNT(*) AS total
    FROM conversations
    WHERE created_at >= now() - interval '1 day' * %s
    """,
    (days,),
)
```

This is the minimal fix recommended verbatim by WR-03 in `07-REVIEW.md`. Do
NOT change the surrounding logic (row unpacking, zero-division guard, return
dict structure). Do NOT modify any other query or function in the file.
  </action>
  <verify>
    <automated>python3 -c "import ast; src=open('admin-ui/src/components/database.py').read(); ast.parse(src); assert 'human_handoff = false' not in src, 'old predicate still present'; assert \"state != 'human_handoff'\" in src, 'new predicate missing'; print('OK')"</automated>
  </verify>
  <done>
- `admin-ui/src/components/database.py` parses as valid Python.
- The string `human_handoff = false` no longer appears in the file.
- The string `state != 'human_handoff'` appears in `fetch_dashboard_kpis`.
- The function signature, return dict keys, and surrounding KPI queries are
  unchanged.
  </done>
</task>

</tasks>

<verification>
After all three tasks:

1. JSON validity: `python3 -c "import json; json.load(open('n8n/workflows/appointment-reminders.json'))"` exits 0.
2. Python syntax: `python3 -m py_compile admin-ui/src/components/database.py` exits 0.
3. No hardcoded key: `grep -c Jehova01 n8n/workflows/appointment-reminders.json` returns 0.
4. Env var expression present twice: `grep -c '={{ \$env.EVOLUTION_API_KEY }}' n8n/workflows/appointment-reminders.json` returns 2.
5. All six executeQuery queries prefixed with `=` (verified via the Task 2 automated check).
6. WR-03 predicate swapped (verified via the Task 3 automated check).

Human verification (documented, NOT part of automated run):
- Rotate the old `Jehova01` API key in the Evolution API admin panel and
  update `EVOLUTION_API_KEY` in `.env` / compose env.
- Re-import `n8n/workflows/appointment-reminders.json` into n8n and execute
  manually (Execute Workflow, do not activate) to confirm no red-node errors
  and that UPDATE statements now match rows on a seeded appointment.
</verification>

<success_criteria>
- CR-01 resolved: zero occurrences of `Jehova01`; both Send nodes reference
  `={{ $env.EVOLUTION_API_KEY }}`.
- CR-02 resolved: all six Postgres `executeQuery` node `query` values start
  with `=` so n8n evaluates the embedded `{{ ... }}` expressions.
- WR-03 resolved: `fetch_dashboard_kpis` queries `state != 'human_handoff'`
  against the `conversations` table, matching the actual schema.
- Both files remain syntactically valid (JSON and Python respectively).
- No unrelated changes committed.
</success_criteria>

<output>
After completion, create a task summary at
`.planning/quick/260417-ied-fix-cr-01-cr-02-wr-03-in-appointment-rem/260417-ied-SUMMARY.md`
noting:

1. Which files were changed and which lines (CR-01 at 192 + 241, CR-02 at six
   query positions, WR-03 in `fetch_dashboard_kpis`).
2. Verification commands run and their output.
3. The outstanding HUMAN action for CR-01: rotate the Evolution API key in the
   Evolution admin panel; ensure `EVOLUTION_API_KEY` is set in the n8n
   container's environment so the `$env` expression resolves at runtime.
4. The outstanding HUMAN verification for CR-02 (recommended): import the
   updated workflow JSON into n8n and execute manually to confirm the six
   Postgres queries now resolve their expressions correctly.
5. Note that WR-01 (reminders marked sent on failure), WR-02 (DATABASE_URL
   None guard), WR-04, WR-05, and all IN-xx findings are OUT OF SCOPE for
   this quick fix and remain open in `07-VERIFICATION.md` / `07-REVIEW.md`.
</output>
