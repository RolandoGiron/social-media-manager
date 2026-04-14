"""Social publishing helpers (Phase 6, SOCIAL-01).

Pure helpers consumed by 8_Publicaciones.py and 7_Campañas.py Step 3.
DB CRUD lives in components/database.py — this module is filesystem + time + label mapping only.
"""
from __future__ import annotations

import uuid
from datetime import date as _date, datetime, time as _time
from pathlib import Path
from zoneinfo import ZoneInfo

# Public constants -----------------------------------------------------------
UPLOADS_DIR = Path("/opt/clinic-crm/uploads")
ALLOWED_IMAGE_EXTS: frozenset[str] = frozenset({"jpg", "jpeg", "png", "webp"})
MAX_IMAGE_BYTES: int = 8 * 1024 * 1024  # 8 MB hard cap (UI-SPEC + RESEARCH security)
MX_TZ = ZoneInfo("America/Mexico_City")

# DB enum -> Spanish UI label (per RESEARCH Open Question 2 recommendation)
_STATUS_LABELS: dict[str, str] = {
    "draft": "Pendiente",
    "scheduled": "Pendiente",
    "publishing": "Pendiente",
    "published": "Publicado",
    "failed": "Error",
}


def status_label(db_status: str) -> str:
    """Map social_posts.status DB enum to the Spanish UI label."""
    return _STATUS_LABELS.get(db_status, "—")


def combine_local_datetime(d: _date, t: _time) -> datetime:
    """Combine a date + time entered by the admin into a tz-aware datetime in MX_TZ.

    Postgres TIMESTAMPTZ will then convert to UTC on insert automatically.
    """
    return datetime.combine(d, t).replace(tzinfo=MX_TZ)


def save_uploaded_image(
    image_bytes: bytes,
    original_name: str,
    uploads_dir: Path = UPLOADS_DIR,
) -> str:
    """Persist uploaded bytes under a UUID filename and return the relative DB path.

    Returns a path of the form `uploads/{uuid}.{ext}` to be stored in social_posts.image_url.
    n8n reads the absolute path `/opt/clinic-crm/{relative}` via the shared volume.
    """
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ValueError(
            f"Imagen excede {MAX_IMAGE_BYTES // (1024 * 1024)} MB"
        )
    ext = Path(original_name).suffix.lower().lstrip(".")
    if ext == "jpeg":
        ext = "jpg"
    if ext not in ALLOWED_IMAGE_EXTS:
        raise ValueError(f"Extension no permitida: {ext}")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4()}.{ext}"
    (uploads_dir / filename).write_bytes(image_bytes)
    return f"uploads/{filename}"
