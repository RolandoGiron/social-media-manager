"""Tests for components.social_posts (Phase 6, SOCIAL-01)."""
from __future__ import annotations

from datetime import date, time
from pathlib import Path

import pytest

from components.social_posts import (
    ALLOWED_IMAGE_EXTS,
    MAX_IMAGE_BYTES,
    MX_TZ,
    combine_local_datetime,
    save_uploaded_image,
    status_label,
)


# --- save_uploaded_image -----------------------------------------------------

def test_save_uploaded_image_writes_file_and_returns_relative_path(tmp_path: Path) -> None:
    rel = save_uploaded_image(b"\x89PNG fake", "promo.png", uploads_dir=tmp_path)
    assert rel.startswith("uploads/")
    assert rel.endswith(".png")
    written = tmp_path / Path(rel).name
    assert written.exists()
    assert written.read_bytes() == b"\x89PNG fake"


def test_save_uploaded_image_normalizes_jpeg_to_jpg(tmp_path: Path) -> None:
    rel = save_uploaded_image(b"jpegdata", "photo.JPEG", uploads_dir=tmp_path)
    assert rel.endswith(".jpg")


def test_save_uploaded_image_rejects_oversize(tmp_path: Path) -> None:
    too_big = b"\x00" * (MAX_IMAGE_BYTES + 1)
    with pytest.raises(ValueError, match="excede"):
        save_uploaded_image(too_big, "huge.jpg", uploads_dir=tmp_path)


@pytest.mark.parametrize("name", ["evil.svg", "shell.exe", "doc.pdf", "noext"])
def test_save_uploaded_image_rejects_disallowed_extensions(tmp_path: Path, name: str) -> None:
    with pytest.raises(ValueError, match="permitida"):
        save_uploaded_image(b"x", name, uploads_dir=tmp_path)


def test_save_uploaded_image_creates_uploads_dir(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "dir"
    save_uploaded_image(b"x", "p.webp", uploads_dir=target)
    assert target.is_dir()


def test_save_uploaded_image_uses_uuid_filenames(tmp_path: Path) -> None:
    rel1 = save_uploaded_image(b"a", "p.jpg", uploads_dir=tmp_path)
    rel2 = save_uploaded_image(b"b", "p.jpg", uploads_dir=tmp_path)
    assert rel1 != rel2


# --- combine_local_datetime --------------------------------------------------

def test_combine_local_datetime_is_tz_aware_in_mexico_city() -> None:
    dt = combine_local_datetime(date(2026, 5, 1), time(10, 30))
    assert dt.tzinfo is MX_TZ
    assert dt.year == 2026 and dt.month == 5 and dt.day == 1
    assert dt.hour == 10 and dt.minute == 30


# --- status_label ------------------------------------------------------------

@pytest.mark.parametrize(
    "db,label",
    [
        ("draft", "Pendiente"),
        ("scheduled", "Pendiente"),
        ("publishing", "Pendiente"),
        ("published", "Publicado"),
        ("failed", "Error"),
        ("nonsense", "—"),
    ],
)
def test_status_label_maps_db_enum_to_spanish(db: str, label: str) -> None:
    assert status_label(db) == label


def test_allowed_extensions_contract() -> None:
    assert ALLOWED_IMAGE_EXTS == frozenset({"jpg", "jpeg", "png", "webp"})
