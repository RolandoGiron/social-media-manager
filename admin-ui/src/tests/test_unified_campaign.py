"""Tests for 7_Campañas.py Step 3 unified WA + social publishing (Phase 6, SOCIAL-02).

Tests exercise _handle_launch_campaign() directly (extracted for testability).
Mocking strategy matches test_campaigns.py:
  - @mock.patch("components.database.get_connection")
  - components.social_posts helpers mocked at import time
  - st.session_state driven as a dict on the mock
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from unittest import mock
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

# ---------------------------------------------------------------------------
# Load 7_Campañas.py as a module with deps mocked
# ---------------------------------------------------------------------------
PAGE_PATH = Path(__file__).parent.parent / "pages" / "7_Campañas.py"


class _SessionState(dict):
    """Dict subclass that also supports attribute-style access (mirrors Streamlit's SessionState)."""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value


def _make_st_mock(session_state: "_SessionState | None" = None):
    """Return a MagicMock shaped like streamlit with a real-dict session_state."""
    st = mock.MagicMock()
    st.session_state = session_state if session_state is not None else _SessionState()
    col = mock.MagicMock()
    col.__enter__ = mock.MagicMock(return_value=col)
    col.__exit__ = mock.MagicMock(return_value=False)
    st.columns.return_value = (col, col)
    st.button.return_value = False
    st.file_uploader.return_value = None
    st.checkbox.return_value = False
    st.multiselect.return_value = []
    st.selectbox.return_value = None
    return st


def _load_campanhas_module(session_state: dict, module_name: str = "pages.campanhas_test"):
    """Load 7_Campañas.py with mocked deps and the given session_state dict."""
    MX_TZ = ZoneInfo("America/Mexico_City")

    st_mock = _make_st_mock(session_state)

    # --- components.database ---
    db_mock = types.ModuleType("components.database")
    campaign_id = "aaaaaaaa-0000-0000-0000-000000000001"
    social_id = "bbbbbbbb-0000-0000-0000-000000000002"
    db_mock.insert_campaign = mock.MagicMock(return_value={"id": campaign_id})
    db_mock.insert_campaign_recipients = mock.MagicMock(return_value=3)
    db_mock.insert_social_post = mock.MagicMock(return_value={"id": social_id})
    db_mock.fetch_tags_with_counts = mock.MagicMock(return_value=[])
    db_mock.fetch_templates = mock.MagicMock(return_value=[])
    db_mock.fetch_patients_by_tags = mock.MagicMock(return_value=[])
    db_mock.fetch_campaign_history = mock.MagicMock(return_value=[])
    db_mock.fetch_campaign_status = mock.MagicMock(return_value=None)
    db_mock.cancel_campaign = mock.MagicMock()
    db_mock.execute_values = mock.MagicMock()
    db_mock.fetch_campaign_delivery_analytics = mock.MagicMock(return_value=[])

    # --- components.social_posts ---
    sp_mock = types.ModuleType("components.social_posts")
    sp_mock.MX_TZ = MX_TZ
    sp_mock.ALLOWED_IMAGE_EXTS = frozenset({"jpg", "jpeg", "png", "webp"})
    sp_mock.MAX_IMAGE_BYTES = 8 * 1024 * 1024
    sp_mock.combine_local_datetime = mock.MagicMock(
        return_value=datetime.now(MX_TZ) + timedelta(hours=1)
    )
    sp_mock.save_uploaded_image = mock.MagicMock(return_value="uploads/test.jpg")
    sp_mock.status_label = mock.MagicMock(return_value="Pendiente")

    # --- components.sidebar ---
    sidebar_mock = types.ModuleType("components.sidebar")
    sidebar_mock.render_sidebar = mock.MagicMock()

    # --- components.templates ---
    templates_mock = types.ModuleType("components.templates")
    templates_mock.render_preview = mock.MagicMock(return_value="Preview text")

    # --- requests ---
    requests_mock = types.ModuleType("requests")
    resp = mock.MagicMock()
    resp.status_code = 200
    requests_mock.post = mock.MagicMock(return_value=resp)
    requests_mock.RequestException = Exception

    original = {}
    inject = {
        "streamlit": st_mock,
        "components.database": db_mock,
        "components.social_posts": sp_mock,
        "components.sidebar": sidebar_mock,
        "components.templates": templates_mock,
        "requests": requests_mock,
    }
    for key, mod in inject.items():
        original[key] = sys.modules.get(key)
        sys.modules[key] = mod

    # Save values that the page-level render will overwrite (fetch_* mocks return empty).
    _preserve_keys = ("_campanas_tags_cache", "_campanas_selected_template_cache",
                      "campanas_selected_tag_ids")
    _saved = {k: session_state[k] for k in _preserve_keys if k in session_state}

    try:
        spec = importlib.util.spec_from_file_location(module_name, str(PAGE_PATH))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        for key, orig in original.items():
            if orig is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = orig

    # Restore session state clobbered by page-level render so _handle_launch_campaign sees them.
    session_state.update(_saved)

    return module, db_mock, sp_mock, requests_mock, st_mock


# ---------------------------------------------------------------------------
# Helper: build a session state for the confirm path
# ---------------------------------------------------------------------------
MX_TZ = ZoneInfo("America/Mexico_City")
_FUTURE_DATE = (datetime.now(MX_TZ) + timedelta(days=1)).date()
_FUTURE_TIME = time(12, 0)


def _base_session(publish_social: bool = False) -> "_SessionState":
    return _SessionState({
        "campanas_mode": "setup",
        "campanas_selected_tag_ids": ["tag-uuid-1"],
        "campanas_selected_template_id": "tpl-uuid-1",
        "campanas_active_campaign_id": None,
        "campanas_recipient_count": 3,
        "campanas_publish_social": publish_social,
        "campanas_social_caption": "Promo redes" if publish_social else "",
        "campanas_social_image_bytes": b"FAKEIMG" if publish_social else None,
        "campanas_social_image_name": "img.jpg" if publish_social else None,
        "campanas_social_platforms": ["Instagram", "Facebook"],
        "campanas_social_date": _FUTURE_DATE,
        "campanas_social_time": _FUTURE_TIME,
        "_campanas_tags_cache": [{"id": "tag-uuid-1", "name": "acn\u00e9"}],
        "_campanas_selected_template_cache": {"id": "tpl-uuid-1", "name": "Promo", "body": "Hola {nombre}"},
    })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestStep3DefaultOffNoSocialInsert:
    """When campanas_publish_social is False, insert_social_post must NOT be called."""

    def test_step3_default_off_does_not_call_insert_social_post(self):
        session = _base_session(publish_social=False)
        module, db_mock, sp_mock, req_mock, st_mock = _load_campanhas_module(
            session, "pages.campanhas_step3_off"
        )
        module._handle_launch_campaign(
            recipient_ids=["p1", "p2", "p3"],
            recipient_count=3,
        )
        db_mock.insert_social_post.assert_not_called()


class TestStep3OnInsertsBothRows:
    """When campanas_publish_social is True, both insert_campaign and insert_social_post are called."""

    def test_step3_on_inserts_both_campaign_and_social_post(self):
        session = _base_session(publish_social=True)
        module, db_mock, sp_mock, req_mock, st_mock = _load_campanhas_module(
            session, "pages.campanhas_step3_on_1"
        )
        module._handle_launch_campaign(
            recipient_ids=["p1", "p2", "p3"],
            recipient_count=3,
        )
        db_mock.insert_campaign.assert_called_once()
        db_mock.insert_social_post.assert_called_once()

    def test_step3_on_links_campaign_id_via_kwarg(self):
        session = _base_session(publish_social=True)
        module, db_mock, sp_mock, req_mock, st_mock = _load_campanhas_module(
            session, "pages.campanhas_step3_on_2"
        )
        campaign_id = "aaaaaaaa-0000-0000-0000-000000000001"
        db_mock.insert_campaign.return_value = {"id": campaign_id}

        module._handle_launch_campaign(
            recipient_ids=["p1"],
            recipient_count=1,
        )
        call_kwargs = db_mock.insert_social_post.call_args
        # campaign_id must be passed as keyword arg or positional; check either
        kwargs = call_kwargs.kwargs if hasattr(call_kwargs, "kwargs") else call_kwargs[1]
        assert kwargs.get("campaign_id") == str(campaign_id)

    def test_step3_caption_is_independent_from_wa_template(self):
        """Caption sent to insert_social_post must come from campanas_social_caption."""
        social_caption = "Caption exclusivo de redes sociales"
        session = _base_session(publish_social=True)
        session["campanas_social_caption"] = social_caption

        module, db_mock, sp_mock, req_mock, st_mock = _load_campanhas_module(
            session, "pages.campanhas_caption_check"
        )
        module._handle_launch_campaign(
            recipient_ids=["p1"],
            recipient_count=1,
        )
        call_kwargs = db_mock.insert_social_post.call_args
        kwargs = call_kwargs.kwargs if hasattr(call_kwargs, "kwargs") else call_kwargs[1]
        # Caption passed to social post must be the social-specific caption
        assert kwargs.get("caption") == social_caption


class TestUnifiedWebhookFailure:
    """When social webhook fails, emit st.warning — NOT st.error — and reach progress mode."""

    def test_unified_webhook_failure_emits_warning_not_error(self):
        session = _base_session(publish_social=True)
        module, db_mock, sp_mock, req_mock, st_mock = _load_campanhas_module(
            session, "pages.campanhas_webhook_fail"
        )

        # WA webhook succeeds, social webhook fails
        req_mock.post = mock.MagicMock(side_effect=[
            # first call: WA blast — success
            mock.MagicMock(status_code=200),
            # second call: social-publish — failure
            mock.MagicMock(status_code=500),
        ])

        # st.rerun raises SystemExit in Streamlit — mock it so we can detect progress mode
        st_mock.rerun = mock.MagicMock(side_effect=SystemExit(0))

        try:
            module._handle_launch_campaign(
                recipient_ids=["p1"],
                recipient_count=1,
            )
        except SystemExit:
            pass  # expected — st.rerun() terminates script execution

        # Must have shown a warning (not error) about the social webhook
        st_mock.warning.assert_called()
        st_mock.error.assert_not_called()

        # Progress mode must have been set before rerun
        assert session.get("campanas_mode") == "progress"
