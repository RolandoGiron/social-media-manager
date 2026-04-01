"""Tests for patient business logic: phone normalization, CSV parsing, preview builder."""
import io
import pytest
import pandas as pd
from unittest import mock

from components.patients import normalize_mx_phone, parse_import_file, build_preview


class TestNormalizeMxPhone:
    """Phone normalization to +52 E.164 format."""

    def test_normalize_mx_phone_10_digits(self):
        assert normalize_mx_phone("5512345678") == ("+525512345678", None)

    def test_normalize_mx_phone_with_country_code(self):
        assert normalize_mx_phone("525512345678") == ("+525512345678", None)

    def test_normalize_mx_phone_plus52(self):
        assert normalize_mx_phone("+525512345678") == ("+525512345678", None)

    def test_normalize_mx_phone_old_521_format(self):
        assert normalize_mx_phone("+5215512345678") == ("+525512345678", None)

    def test_normalize_mx_phone_521_no_plus(self):
        assert normalize_mx_phone("5215512345678") == ("+525512345678", None)

    def test_normalize_mx_phone_with_dashes(self):
        assert normalize_mx_phone("55-1234-5678") == ("+525512345678", None)

    def test_normalize_mx_phone_with_spaces_parens(self):
        assert normalize_mx_phone("(55) 1234 5678") == ("+525512345678", None)

    def test_normalize_mx_phone_too_short(self):
        result = normalize_mx_phone("12345")
        assert result[0] == ""
        assert "5 digitos" in result[1]

    def test_normalize_mx_phone_empty(self):
        result = normalize_mx_phone("")
        assert result[0] == ""


class TestParseImportFile:
    """CSV/Excel file parsing and column validation."""

    def test_parse_import_file_csv(self, sample_csv_bytes):
        df = parse_import_file(sample_csv_bytes)
        assert len(df) == 2
        assert set(df.columns) >= {"nombre", "apellido", "telefono"}

    def test_parse_import_file_missing_column(self, sample_csv_missing_col):
        with pytest.raises(ValueError, match="telefono"):
            parse_import_file(sample_csv_missing_col)

    def test_parse_import_file_unsupported_format(self):
        uploaded = mock.MagicMock()
        uploaded.name = "data.txt"
        with pytest.raises(ValueError, match="Formato no soportado"):
            parse_import_file(uploaded)


class TestBuildPreview:
    """Preview builder: classify rows as Nuevo, Duplicado, or Error."""

    def test_build_preview_new_patient(self):
        df = pd.DataFrame([{"nombre": "Ana", "apellido": "Lopez", "telefono": "5512345678"}])
        preview = build_preview(df, existing_phones=set())
        assert preview.iloc[0]["estado"] == "Nuevo"
        assert preview.iloc[0]["tel_normalizado"] == "+525512345678"

    def test_build_preview_duplicate(self):
        df = pd.DataFrame([{"nombre": "Ana", "apellido": "Lopez", "telefono": "5512345678"}])
        preview = build_preview(df, existing_phones={"+525512345678"})
        assert preview.iloc[0]["estado"] == "Duplicado"

    def test_build_preview_error(self):
        df = pd.DataFrame([{"nombre": "Ana", "apellido": "Lopez", "telefono": "123"}])
        preview = build_preview(df, existing_phones=set())
        assert preview.iloc[0]["estado"] == "Error"

    def test_build_preview_columns(self):
        df = pd.DataFrame([{"nombre": "Ana", "apellido": "Lopez", "telefono": "5512345678"}])
        preview = build_preview(df, existing_phones=set())
        assert "tel_normalizado" in preview.columns
        assert "estado" in preview.columns
