---
phase: "06"
plan: "02"
subsystem: social-publishing
tags: [n8n, workflow, docker-compose, caddy, social-media, mock-mode, postgres]
dependency_graph:
  requires:
    - "06-01: social_posts table schema (postgres/init/001_schema.sql L174-192)"
    - "Phase 1: Docker Compose infrastructure stack"
  provides:
    - "n8n/workflows/social-publish.json — dual-trigger dispatcher with mock/real branch"
    - "Shared uploads volume mounted in streamlit, n8n, caddy"
    - "MOCK_SOCIAL=true safe default for pre-approval dev"
    - "Caddy /uploads/* static HTTPS route for Meta API image fetch"
    - "Nyquist test stubs locking SKIP LOCKED and MOCK_SOCIAL isolation"
  affects:
    - "06-03: 8_Publicaciones.py and 7_Campañas.py call the social-publish webhook"
tech_stack:
  added:
    - "n8n Schedule Trigger (1-minute cron dispatcher)"
    - "n8n Merge node (dual-entry-point fan-in)"
    - "Meta Graph API v21.0 endpoints (Instagram two-step, Facebook /photos)"
  patterns:
    - "FOR UPDATE SKIP LOCKED idempotent dispatcher (prevents double-publish on race)"
    - "MOCK_SOCIAL env var toggle: true=internal HTTP call, false=real Meta API"
    - "D-17: mock path is real HTTP Request node (not Set node) for byte-equivalent execution"
    - "Named Docker volume shared across streamlit + n8n + caddy with :ro on caddy"
key_files:
  created:
    - "n8n/workflows/social-publish.json"
    - "admin-ui/src/tests/test_dispatcher.py"
  modified:
    - "docker-compose.yml"
    - ".env.example"
    - "caddy/Caddyfile"
decisions:
  - "Named volume 'uploads' (not 'social_uploads') per CONTEXT.md D-12/D-14"
  - "Caddy mount uses :ro because Caddy only reads images, never writes"
  - "Mock path is HTTP Request to /webhook/mock-social-log (D-17) — same workflow, same instance"
  - "test_dispatcher.py uses REPO_ROOT env var fallback so tests skip gracefully inside Docker container (workflow JSON not mounted)"
  - "MOCK_SOCIAL=true is the safe default — prevents accidental Meta API calls before App Review"
metrics:
  duration: "~30min"
  completed: "2026-04-14T05:52:54Z"
  tasks_completed: 3
  files_created: 2
  files_modified: 3
---

# Phase 06 Plan 02: Infrastructure Plumbing + n8n Social Publish Workflow Summary

**One-liner:** Docker uploads volume + Caddy static HTTPS route + n8n social-publish workflow with FOR UPDATE SKIP LOCKED dispatcher and HTTP-based MOCK_SOCIAL toggle.

## What Was Built

### Task 1: Shared uploads volume, Caddy static route, MOCK_SOCIAL env

- `docker-compose.yml` — Added named volume `uploads` with `driver: local`. Mounted in:
  - `streamlit` service: `/opt/clinic-crm/uploads` (read-write, for Plan 03 file uploader)
  - `n8n` service: `/opt/clinic-crm/uploads` (read-write, for workflow file access)
  - `caddy` service: `/srv/uploads:ro` (read-only, serves images to Meta API)
- Both `n8n` and `streamlit` services received `MOCK_SOCIAL: ${MOCK_SOCIAL:-true}` env var.
- `caddy/Caddyfile` — Added `handle_path /uploads/*` inside the admin site block (before `reverse_proxy`) with `X-Content-Type-Options: nosniff` (T-06-07 mitigation).
- `.env.example` — Added Phase 6 section with `MOCK_SOCIAL=true` default and Meta Graph API credential placeholders.

### Task 2: social-publish.json n8n workflow

Single workflow file with 22 nodes covering:
- **Dual entry points:** `Webhook social-publish` (POST from Streamlit) + `Schedule social-scheduler` (1-minute cron)
- **Claim Pending Rows** — `FOR UPDATE SKIP LOCKED` to prevent double-publish on race (T-06-12)
- **Load Single Post** — Webhook path loads a single post and transitions it to `publishing`
- **Merge Entry Paths** — Fan-in from both entry points into a single publish pipeline
- **Build Public URL** — Constructs `https://{ADMIN_DOMAIN}/{image_url}` for Meta API
- **Mock Mode? IF gate** — Branches on `$env.MOCK_SOCIAL == "true"`
  - TRUE: `Mock Publish Call` HTTP Request → `/webhook/mock-social-log` (real HTTP, not Set node per D-17)
  - FALSE: Instagram two-step (`IG Create Container` → `Wait 3s` → `IG Publish Container`) + Facebook `FB Publish Photo`
- **Mark Published** / **Mark Failed** — Write-back to `social_posts` table
- **Internal mock-log webhook** — `Webhook mock-social-log` + `Mock Log Response` returns `{success:true,mock:true}`
- All Meta API calls pinned to `graph.facebook.com/v21.0`
- No deprecated `scheduled_posts` table or `image_path` column

### Task 3: test_dispatcher.py Nyquist test stubs

8 tests that introspect `social-publish.json` as a JSON document (no DB, no Docker, no live n8n):
- `test_skip_locked_claim_pattern_present` — Guards SOCIAL-02 idempotency contract
- `test_claim_limit_bounded` — Guards T-06-10 (mass-publish cap)
- `test_mock_mode_gate_exists` — Mock Mode? IF node required
- `test_mock_publish_is_http_not_set_node` — D-17: HTTP Request not Set node
- `test_mock_log_webhook_entry_exists` — Internal webhook path must exist
- `test_meta_api_nodes_not_reachable_from_mock_branch` — Graph walk isolation (T-06-22)
- `test_workflow_name_is_social_publish` — Sanity check
- `test_no_deprecated_schema_names` — Guards against `scheduled_posts`/`image_path` regressions

Tests skip gracefully inside Docker container (workflow JSON not bind-mounted). All 8 pass on host.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree git reset --soft caused index mismatch**
- **Found during:** Task 1 commit
- **Issue:** `git reset --soft 99f47b9` left the working tree from the old HEAD (dd69c371) while resetting the index. Staging only the 3 target files caused git to commit all other file deletions too.
- **Fix:** Added a `fix(06-02): restore files accidentally deleted` commit (e09414f) that restores all 47 files to their state at base commit 99f47b9 using `git checkout 99f47b9 -- <files>`.
- **Commit:** e09414f

**2. [Rule 1 - Bug] WORKFLOW_PATH parents[3] IndexError inside Docker container**
- **Found during:** Task 3 verification
- **Issue:** Inside the Docker container, the test file is mounted at `/app/tests/test_dispatcher.py` (only 2 parent levels). `Path(__file__).parents[3]` raised IndexError at import time.
- **Fix:** Changed `_DEFAULT_REPO_ROOT` calculation to use `_parents[3] if len(_parents) > 3 else _self.parent`, and added `REPO_ROOT` env var override + `pytest.skip()` when workflow file is not accessible.
- **Files modified:** `admin-ui/src/tests/test_dispatcher.py`

## Known Stubs

None. All nodes wire to real SQL and real HTTP endpoints. The MOCK_SOCIAL=true path calls a real HTTP endpoint (not a Set node stub).

## Threat Flags

No new threat surface beyond what is already tracked in the plan's threat model (T-06-07 through T-06-22). The `X-Content-Type-Options: nosniff` mitigation for T-06-07 was implemented in Caddy.

## Self-Check: PASSED

- `n8n/workflows/social-publish.json` exists: FOUND
- `admin-ui/src/tests/test_dispatcher.py` exists: FOUND
- `docker-compose.yml` has 2x uploads:/opt/clinic-crm/uploads: VERIFIED
- `caddy/Caddyfile` has handle_path /uploads/*: VERIFIED
- `.env.example` has MOCK_SOCIAL=true: VERIFIED
- Commits: 982b136, e09414f, ee88d29, 170d65e all in git log: VERIFIED
- 8/8 dispatcher tests pass on host: VERIFIED
- Docker container tests exit 0 (8 skips): VERIFIED
