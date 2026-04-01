"""Patient business logic: phone normalization, CSV/Excel parsing, preview builder."""
import re

import pandas as pd


def normalize_mx_phone(raw: str) -> tuple[str, str | None]:
    """Normalize a Mexican phone number to E.164 format (+52XXXXXXXXXX).

    Returns (normalized, error_message). error_message is None if valid.

    Mexico format: +52 followed by 10 digits (no "1" prefix since Aug 2020).
    """
    if not raw or not raw.strip():
        return "", "Numero invalido: (vacio)"

    # Strip all non-digit characters
    digits = re.sub(r"\D", "", raw)

    # Remove country code if present
    if digits.startswith("521") and len(digits) == 13:
        # Old format with "1" -- strip it
        digits = digits[3:]
    elif digits.startswith("52") and len(digits) == 12:
        digits = digits[2:]

    if len(digits) != 10:
        return "", f"Numero invalido: {raw} ({len(digits)} digitos, se esperan 10)"

    return f"+52{digits}", None


def parse_import_file(uploaded_file) -> pd.DataFrame:
    """Parse CSV or Excel file into a DataFrame.

    Validates that required columns (nombre, apellido, telefono) are present.
    Raises ValueError if format is unsupported or columns are missing.
    """
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(uploaded_file)
    else:
        raise ValueError("Formato no soportado")

    # Normalize column names to lowercase stripped
    df.columns = [c.strip().lower() for c in df.columns]

    # Validate required columns
    required = {"nombre", "apellido", "telefono"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Columnas faltantes: {', '.join(sorted(missing))}")

    return df


def build_preview(df: pd.DataFrame, existing_phones: set[str]) -> pd.DataFrame:
    """Add normalization and status columns for import preview.

    Status values:
    - "Nuevo": valid phone, not in existing_phones
    - "Duplicado": valid phone, already in existing_phones
    - "Error": phone normalization failed
    """
    preview = df.copy()
    normalized = []
    statuses = []

    for _, row in preview.iterrows():
        phone_norm, error = normalize_mx_phone(str(row["telefono"]))
        normalized.append(phone_norm)
        if error:
            statuses.append("Error")
        elif phone_norm in existing_phones:
            statuses.append("Duplicado")
        else:
            statuses.append("Nuevo")

    preview["tel_normalizado"] = normalized
    preview["estado"] = statuses
    return preview
