"""Tests for patient business logic: phone normalization, CSV parsing, preview builder."""
import io
import pytest
import pandas as pd
from unittest import mock

from components.patients import normalize_sv_phone, parse_import_file, build_preview


class TestNormalizeSvPhone:
    """Phone normalization to +503 E.164 format (El Salvador)."""

    def test_normalize_sv_phone_8_digits(self):
        assert normalize_sv_phone("78422032") == ("+50378422032", None)

    def test_normalize_sv_phone_with_country_code(self):
        assert normalize_sv_phone("50378422032") == ("+50378422032", None)

    def test_normalize_sv_phone_plus503(self):
        assert normalize_sv_phone("+50378422032") == ("+50378422032", None)

    def test_normalize_sv_phone_with_dashes(self):
        assert normalize_sv_phone("7842-2032") == ("+50378422032", None)

    def test_normalize_sv_phone_with_spaces(self):
        assert normalize_sv_phone("7842 2032") == ("+50378422032", None)

    def test_normalize_sv_phone_with_parens_spaces(self):
        assert normalize_sv_phone("(503) 7842 2032") == ("+50378422032", None)

    def test_normalize_sv_phone_too_short(self):
        result = normalize_sv_phone("12345")
        assert result[0] == ""
        assert "5 digitos" in result[1]

    def test_normalize_sv_phone_too_long(self):
        result = normalize_sv_phone("123456789")
        assert result[0] == ""
        assert "9 digitos" in result[1]

    def test_normalize_sv_phone_empty(self):
        result = normalize_sv_phone("")
        assert result[0] == ""

    def test_normalize_sv_phone_landline(self):
        """El Salvador landlines start with 2."""
        assert normalize_sv_phone("22345678") == ("+50322345678", None)

    def test_normalize_sv_phone_pandas_float(self):
        """When pandas reads phone as float64, str() produces '77546650.0'."""
        assert normalize_sv_phone("77546650.0") == ("+50377546650", None)

    def test_normalize_sv_phone_pandas_float_double_zero(self):
        """Handle '.00' suffix from some Excel exports."""
        assert normalize_sv_phone("77546650.00") == ("+50377546650", None)

    def test_normalize_sv_phone_nan_string(self):
        """When pandas NaN is converted to str(), it produces 'nan'."""
        result = normalize_sv_phone("nan")
        assert result[0] == ""
        assert "vacio" in result[1]


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
        df = pd.DataFrame([{"nombre": "Ana", "apellido": "Lopez", "telefono": "78422032"}])
        preview = build_preview(df, existing_phones=set())
        assert preview.iloc[0]["estado"] == "Nuevo"
        assert preview.iloc[0]["tel_normalizado"] == "+50378422032"

    def test_build_preview_duplicate(self):
        df = pd.DataFrame([{"nombre": "Ana", "apellido": "Lopez", "telefono": "78422032"}])
        preview = build_preview(df, existing_phones={"+50378422032"})
        assert preview.iloc[0]["estado"] == "Duplicado"

    def test_build_preview_error(self):
        df = pd.DataFrame([{"nombre": "Ana", "apellido": "Lopez", "telefono": "123"}])
        preview = build_preview(df, existing_phones=set())
        assert preview.iloc[0]["estado"] == "Error"

    def test_build_preview_columns(self):
        df = pd.DataFrame([{"nombre": "Ana", "apellido": "Lopez", "telefono": "78422032"}])
        preview = build_preview(df, existing_phones=set())
        assert "tel_normalizado" in preview.columns
        assert "estado" in preview.columns

    def test_build_preview_with_country_code(self):
        df = pd.DataFrame([{"nombre": "Ana", "apellido": "Lopez", "telefono": "+50378422032"}])
        preview = build_preview(df, existing_phones=set())
        assert preview.iloc[0]["estado"] == "Nuevo"
        assert preview.iloc[0]["tel_normalizado"] == "+50378422032"

    def test_build_preview_numeric_phones_with_missing(self):
        """Simulate pandas float64 column from CSV with missing phone values.

        When any telefono cell is empty, pandas reads the entire column as
        float64, turning 77546650 into 77546650.0. This must not break
        normalization for valid rows.
        """
        import numpy as np

        df = pd.DataFrame([
            {"nombre": "Ana", "apellido": "Lopez", "telefono": 77546650.0},
            {"nombre": "Luis", "apellido": "Diaz", "telefono": np.nan},
            {"nombre": "Rosa", "apellido": "Rivas", "telefono": 71705667.0},
        ])
        preview = build_preview(df, existing_phones=set())
        assert preview.iloc[0]["estado"] == "Nuevo"
        assert preview.iloc[0]["tel_normalizado"] == "+50377546650"
        assert preview.iloc[1]["estado"] == "Error"
        assert preview.iloc[2]["estado"] == "Nuevo"
        assert preview.iloc[2]["tel_normalizado"] == "+50371705667"
