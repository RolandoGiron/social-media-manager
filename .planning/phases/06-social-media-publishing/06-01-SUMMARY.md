---
phase: 06-social-media-publishing
plan: 01
subsystem: database
tags: [python, psycopg2, streamlit, zoneinfo, uuid, postgresql, social-posts]

# Dependency graph
requires:
  - phase: 01-infrastructure-foundation
    provides: social_posts table in postgres/init/001_schema.sql (lines 174-192)
  - phase: 05-campaign-blast
    provides: insert_campaign pattern (RealDictCursor + try/finally + conn.commit)
provides:
  - admin-ui/src/components/social_posts.py with save_uploaded_image, status_label, combine_local_datetime, MX_TZ, MAX_IMAGE_BYTES, ALLOWED_IMAGE_EXTS
  - admin-ui/src/components/database.py with insert_social_post, fetch_social_posts, fetch_social_post_by_id, delete_social_post
  - Tests: test_social_posts.py (9 test functions, 17 assertions) + test_database.py (5 new social_post tests)
affects:
  - 06-02 (n8n social-publish.json workflow reads social_posts with status='scheduled')
  - 06-03 (8_Publicaciones.py UI imports all helpers from these two modules)

# Tech tracking
tech-stack:
  added: [zoneinfo (stdlib Python 3.9+)]
  patterns:
    - UUID filename strategy for image uploads (no collision, no path traversal)
    - DB enum to Spanish UI label mapping via Python dict (status_label helper)
    - ZoneInfo("America/Mexico_City") for admin timezone-aware scheduling
    - psycopg2 parameterized queries exclusively for all social_posts CRUD (T-06-04)

key-files:
  created:
    - admin-ui/src/components/social_posts.py
    - admin-ui/src/tests/test_social_posts.py
  modified:
    - admin-ui/src/components/database.py
    - admin-ui/src/tests/test_database.py

key-decisions:
  - "UUID filenames for uploaded images to prevent collision and path traversal (T-06-01)"
  - "8 MB hard cap enforced before disk I/O to prevent DoS (T-06-03)"
  - "Extension allowlist {jpg,jpeg,png,webp} enforced in save_uploaded_image (T-06-02)"
  - "DB enum draft/scheduled/publishing all map to 'Pendiente' in UI per RESEARCH Open Question 2"
  - "delete_social_post restricted to status IN ('draft','scheduled') to protect live rows"
  - "insert_social_post always sets status='scheduled' (not 'draft') so n8n dispatcher picks it up immediately"

patterns-established:
  - "Pattern: save_uploaded_image(bytes, name, uploads_dir=UPLOADS_DIR) -> 'uploads/{uuid}.{ext}' — uploads_dir is injectable for test isolation"
  - "Pattern: status_label(db_status) dict lookup with '—' fallback for unknown enums"
  - "Pattern: combine_local_datetime(date, time) -> tz-aware datetime in MX_TZ before Postgres insert"
  - "Pattern: social CRUD functions follow identical get_connection/RealDictCursor/try-finally/conn.commit style as campaign helpers"

requirements-completed: [SOCIAL-01, SOCIAL-03]

# Metrics
duration: 15min
completed: 2026-04-14
---

# Phase 6 Plan 01: Social Posts Foundation Summary

**Pure Python helpers for social post scheduling: UUID image upload to shared volume, ZoneInfo MX timezone conversion, DB enum-to-Spanish label mapping, and 4 parameterized CRUD functions for the social_posts table**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-14T05:45:00Z
- **Completed:** 2026-04-14T06:00:00Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 4

## Accomplishments

- Created `social_posts.py` module with 3 pure helpers + 4 public constants; zero DB or Streamlit dependencies — importable by Plan 03 UI without side effects
- Extended `database.py` with 4 social_posts CRUD functions that reuse the established psycopg2 RealDictCursor pattern from Phase 5 campaigns
- 37 tests total pass (17 in test_social_posts.py, 20 in test_database.py); zero regressions on existing tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Create social_posts helper module with image upload, timezone, status mapping** - `8c70873` (feat)
2. **Task 2: Add social_posts CRUD helpers to database.py and tests** - `ce4ae7d` (feat)

_Note: Both tasks used TDD (RED → GREEN). No REFACTOR step needed — code was clean on first pass._

## Files Created/Modified

- `admin-ui/src/components/social_posts.py` - New module: save_uploaded_image, status_label, combine_local_datetime, MX_TZ, MAX_IMAGE_BYTES, ALLOWED_IMAGE_EXTS
- `admin-ui/src/tests/test_social_posts.py` - New test file: 9 test functions covering all helpers + constants
- `admin-ui/src/components/database.py` - Appended: insert_social_post, fetch_social_posts, fetch_social_post_by_id, delete_social_post
- `admin-ui/src/tests/test_database.py` - Appended: 5 new test classes for social_post CRUD functions

## Decisions Made

- `insert_social_post` always writes `status='scheduled'` (hardcoded in SQL literal) so the n8n Plan 02 dispatcher picks up the row immediately without a separate state transition
- `delete_social_post` uses `status IN ('draft', 'scheduled')` guard clause to refuse deletion of in-flight or completed posts
- `save_uploaded_image` accepts an injectable `uploads_dir` parameter so tests use `tmp_path` instead of touching `/opt/clinic-crm/uploads/`
- Extension allowlist enforced AFTER size check so we fail-fast on oversized files without extension inspection

## Deviations from Plan

None — plan executed exactly as written. All code and tests match the specified interfaces from the plan's `<action>` blocks.

## Issues Encountered

None. The test discovery path inside the container is `/app/tests/` (not `/app/src/tests/` as stated in the plan's verify commands) — this is a pre-existing container volume mount convention, not a problem with the code.

## User Setup Required

None — no external service configuration required. The `/opt/clinic-crm/uploads/` directory is created at runtime by `save_uploaded_image` via `uploads_dir.mkdir(parents=True, exist_ok=True)`.

## Threat Surface Scan

No new network endpoints or auth paths introduced. All new surface is:
- Filesystem write to `/opt/clinic-crm/uploads/` (addressed by T-06-01/02/03 mitigations in place)
- PostgreSQL writes via parameterized queries (T-06-04 mitigated)

No unplanned threat surface detected.

## Next Phase Readiness

- Plan 02 (n8n social-publish.json): can rely on `social_posts` rows with `status='scheduled'` and `image_url = 'uploads/{uuid}.{ext}'`
- Plan 03 (8_Publicaciones.py UI): can `from components.social_posts import save_uploaded_image, status_label, combine_local_datetime, MAX_IMAGE_BYTES, ALLOWED_IMAGE_EXTS` and `from components.database import insert_social_post, fetch_social_posts, fetch_social_post_by_id, delete_social_post` without ambiguity

## Self-Check: PASSED

- `admin-ui/src/components/social_posts.py` exists: FOUND
- `admin-ui/src/tests/test_social_posts.py` exists: FOUND
- `admin-ui/src/components/database.py` (modified): FOUND
- `admin-ui/src/tests/test_database.py` (modified): FOUND
- Commit `8c70873` exists: FOUND
- Commit `ce4ae7d` exists: FOUND
- All 37 tests pass: VERIFIED

---
*Phase: 06-social-media-publishing*
*Completed: 2026-04-14*
