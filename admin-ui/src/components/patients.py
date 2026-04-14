"""Patient business logic: phone normalization, CSV/Excel parsing, preview builder."""
import re

import pandas as pd


def normalize_sv_phone(raw: str) -> tuple[str, str | None]:
    """Normalize a El Salvador phone number to E.164 format (+503XXXXXXXX).

    Returns (normalized, error_message). error_message is None if valid.

    El Salvador format: +503 followed by 8 digits.
    """
    if not raw or not raw.strip() or raw.strip().lower() == "nan":
        return "", "Numero invalido: (vacio)"

    # Handle pandas float conversion: "77546650.0" -> "77546650"
    # When pandas reads a numeric column with any missing value, it converts
    # all values to float64, adding a spurious ".0" suffix.
    cleaned = raw.strip()
    match = re.fullmatch(r"(\d+)\.0+", cleaned)
    if match:
        cleaned = match.group(1)

    # Strip all non-digit characters
    digits = re.sub(r"\D", "", cleaned)

    # Remove country code if present (503XXXXXXXX)
    if digits.startswith("503") and len(digits) == 11:
        digits = digits[3:]

    if len(digits) != 8:
        return "", f"Numero invalido: {raw} ({len(digits)} digitos, se esperan 8)"

    return f"+503{digits}", None


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
        phone_norm, error = normalize_sv_phone(str(row["telefono"]))
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
