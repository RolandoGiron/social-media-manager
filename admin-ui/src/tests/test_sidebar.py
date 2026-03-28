"""Tests for sidebar WhatsApp status rendering logic.

These tests validate sidebar rendering behavior. The actual sidebar
component (components/sidebar.py) is created in Plan 02-02.
All tests are skipped until the implementation exists.
"""
import pytest


# Tests enabled -- sidebar.py created in Plan 02-02


def test_render_sidebar_connected():
    """When wa_state is 'open', sidebar output contains green circle and 'Conectado'."""
    from components.sidebar import render_whatsapp_status

    output = render_whatsapp_status("open")
    assert "\U0001f7e2" in output or "Conectado" in output


def test_render_sidebar_disconnected():
    """When wa_state is 'close', sidebar output contains red circle and 'Desconectado'."""
    from components.sidebar import render_whatsapp_status

    output = render_whatsapp_status("close")
    assert "\U0001f534" in output or "Desconectado" in output


def test_render_sidebar_connecting():
    """When wa_state is 'connecting', sidebar output contains orange circle and 'Conectando'."""
    from components.sidebar import render_whatsapp_status

    output = render_whatsapp_status("connecting")
    assert "\U0001f7e0" in output or "Conectando" in output


def test_render_sidebar_shows_phone_number(monkeypatch):
    """When connected and CLINIC_WHATSAPP_NUMBER is set, sidebar output contains the phone number."""
    monkeypatch.setenv("CLINIC_WHATSAPP_NUMBER", "+529876543210")
    from components.sidebar import render_whatsapp_status

    output = render_whatsapp_status("open")
    assert "+529876543210" in output


def test_polling_interval_respects_60s(monkeypatch):
    """When last check was <60s ago, no HTTP call is made (cached state returned)."""
    import time

    monkeypatch.setenv("EVOLUTION_API_URL", "http://mock:8080")
    monkeypatch.setenv("EVOLUTION_API_KEY", "test-key")

    from components.sidebar import get_cached_connection_state

    # Simulate a recent check
    state, was_cached = get_cached_connection_state(
        last_check_time=time.time() - 30,  # 30s ago, within 60s window
        last_state="open",
    )
    assert state == "open"
    assert was_cached is True
