"""Tests for template variable extraction and preview rendering."""
from components.templates import extract_variables, render_preview


class TestExtractVariables:
    """Variable extraction from template body."""

    def test_extract_variables_basic(self):
        assert extract_variables("Hola {{nombre}}, tu cita es el {{fecha}}") == ["nombre", "fecha"]

    def test_extract_variables_none(self):
        assert extract_variables("Sin variables") == []

    def test_extract_variables_dedup(self):
        assert extract_variables("{{nombre}} y {{nombre}}") == ["nombre"]

    def test_extract_variables_multiple(self):
        assert extract_variables("{{a}} {{b}} {{c}}") == ["a", "b", "c"]


class TestRenderPreview:
    """Preview rendering with sample value substitution."""

    def test_render_preview_known_var(self):
        assert render_preview("Hola {{nombre}}") == "Hola Ana"

    def test_render_preview_fecha(self):
        assert render_preview("Cita el {{fecha}}") == "Cita el 15 de enero de 2026"

    def test_render_preview_unknown_var(self):
        assert render_preview("{{desconocido}}") == "[desconocido]"

    def test_render_preview_no_vars(self):
        assert render_preview("Sin variables") == "Sin variables"
