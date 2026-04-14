"""Smoke tests for 8_Publicaciones.py (Phase 6, SOCIAL-01, SOCIAL-03).

Tests verify that the page module:
1. Imports cleanly (no ImportError)
2. Uses the correct helper symbols from components.social_posts
3. Uses the correct DB helpers from components.database
4. Has the MOCK_SOCIAL banner logic

Strategy: load the page file via importlib with streamlit and heavy dependencies
mocked so Streamlit widget calls become no-ops.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from unittest import mock

# ---------------------------------------------------------------------------
# Path to the page under test
# ---------------------------------------------------------------------------
PAGE_PATH = Path(__file__).parent.parent / "pages" / "8_Publicaciones.py"
PAGE_SOURCE = PAGE_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Helper: build a minimal mock for streamlit so module-level calls are no-ops
# ---------------------------------------------------------------------------
def _make_st_mock():
    st = mock.MagicMock()
    # session_state must behave like a dict for .setdefault()
    session_state = {}
    st.session_state = session_state
    # st.columns must return a context-manager-capable tuple
    col = mock.MagicMock()
    col.__enter__ = mock.MagicMock(return_value=col)
    col.__exit__ = mock.MagicMock(return_value=False)
    st.columns.return_value = (col, col)
    # st.button returns False so the confirm block is never entered
    st.button.return_value = False
    # st.file_uploader returns None (no file selected)
    st.file_uploader.return_value = None
    return st


def _load_page_module(module_name: str = "pages.publicaciones_test"):
    """Load 8_Publicaciones.py with dependencies mocked.

    Returns the loaded module object.
    """
    st_mock = _make_st_mock()

    # --- mock components.database ---
    db_mock = types.ModuleType("components.database")
    db_mock.insert_social_post = mock.MagicMock(return_value={"id": "00000000-0000-0000-0000-000000000001"})
    db_mock.fetch_social_posts = mock.MagicMock(return_value=[])
    db_mock.fetch_social_post_by_id = mock.MagicMock(return_value=None)
    db_mock.delete_social_post = mock.MagicMock(return_value=1)

    # --- mock components.sidebar ---
    sidebar_mock = types.ModuleType("components.sidebar")
    sidebar_mock.render_sidebar = mock.MagicMock()

    # --- mock components.social_posts ---
    from zoneinfo import ZoneInfo
    from datetime import datetime, date, time, timedelta, timezone

    social_posts_mock = types.ModuleType("components.social_posts")
    social_posts_mock.ALLOWED_IMAGE_EXTS = frozenset({"jpg", "jpeg", "png", "webp"})
    social_posts_mock.MAX_IMAGE_BYTES = 8 * 1024 * 1024
    social_posts_mock.MX_TZ = ZoneInfo("America/Mexico_City")
    social_posts_mock.combine_local_datetime = mock.MagicMock(
        return_value=datetime.now(ZoneInfo("America/Mexico_City")) + timedelta(hours=1)
    )
    social_posts_mock.save_uploaded_image = mock.MagicMock(return_value="uploads/test.jpg")
    social_posts_mock.status_label = mock.MagicMock(return_value="Pendiente")

    # --- mock requests ---
    requests_mock = types.ModuleType("requests")
    resp_mock = mock.MagicMock()
    resp_mock.status_code = 200
    requests_mock.post = mock.MagicMock(return_value=resp_mock)
    requests_mock.RequestException = Exception

    original_modules = {}
    inject = {
        "streamlit": st_mock,
        "components.database": db_mock,
        "components.sidebar": sidebar_mock,
        "components.social_posts": social_posts_mock,
        "requests": requests_mock,
    }

    for key, mod in inject.items():
        original_modules[key] = sys.modules.get(key)
        sys.modules[key] = mod

    try:
        spec = importlib.util.spec_from_file_location(module_name, str(PAGE_PATH))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        # restore original sys.modules entries
        for key, original in original_modules.items():
            if original is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = original

    return module


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_publicaciones_module_imports():
    """Loading the page module with mocked deps must not raise any exception."""
    try:
        _load_page_module("pages.pub_smoke_1")
    except Exception as exc:
        raise AssertionError(f"Page module raised during import: {exc}") from exc


def test_publicaciones_uses_status_label_helper():
    """The page must import status_label from components.social_posts."""
    assert "from components.social_posts import" in PAGE_SOURCE
    # status_label must appear in the import block
    assert "status_label" in PAGE_SOURCE


def test_publicaciones_uses_save_uploaded_image():
    """The page must import and reference save_uploaded_image."""
    assert "save_uploaded_image" in PAGE_SOURCE
    assert "from components.social_posts import" in PAGE_SOURCE


def test_publicaciones_uses_insert_social_post():
    """The page must import and call insert_social_post from components.database."""
    assert "insert_social_post" in PAGE_SOURCE
    assert "from components.database import" in PAGE_SOURCE


def test_publicaciones_has_mock_banner():
    """Page must check MOCK_SOCIAL env var and show Spanish mock-mode info banner."""
    assert "MOCK_SOCIAL" in PAGE_SOURCE
    assert "Modo prueba activo" in PAGE_SOURCE


def test_publicaciones_has_programar_button():
    """Page must have the 'Programar publicacion' primary action button."""
    assert "Programar publicaci" in PAGE_SOURCE


def test_publicaciones_has_eliminar_button():
    """Page must have the 'Eliminar publicacion' delete action."""
    assert "Eliminar publicaci" in PAGE_SOURCE


def test_publicaciones_has_empty_state_message():
    """Page must show the correct empty state info message."""
    assert "Sin publicaciones programadas" in PAGE_SOURCE


def test_publicaciones_webhook_url():
    """Page must POST to the /webhook/social-publish endpoint."""
    assert "/webhook/social-publish" in PAGE_SOURCE
