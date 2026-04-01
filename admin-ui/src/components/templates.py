"""Template business logic: variable extraction and preview rendering."""
import re


VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")

SAMPLE_VALUES = {
    "nombre": "Ana",
    "fecha": "15 de enero de 2026",
    "clinica": "Clinica Dermatologica",
    "telefono": "+52 55 1234 5678",
    "hora": "10:00 AM",
}


def extract_variables(body: str) -> list[str]:
    """Extract unique variable names from template body, preserving order."""
    return list(dict.fromkeys(VARIABLE_PATTERN.findall(body)))


def render_preview(body: str) -> str:
    """Substitute {{variables}} with sample values for preview display.

    Unknown variables are rendered as [variable_name].
    """
    def replacer(match):
        var_name = match.group(1)
        return SAMPLE_VALUES.get(var_name, f"[{var_name}]")

    return VARIABLE_PATTERN.sub(replacer, body)
