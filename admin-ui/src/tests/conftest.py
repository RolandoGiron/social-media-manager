import io

import pytest
from unittest import mock

from components.evolution_api import EvolutionAPIClient


@pytest.fixture
def api_client():
    return EvolutionAPIClient(
        api_url="http://mock-evolution:8080",
        api_key="test-api-key",
        instance_name="test-instance",
    )


@pytest.fixture
def mock_session_state():
    """Provide a dict-like mock for st.session_state."""
    state = {}
    with mock.patch("streamlit.session_state", state):
        yield state


@pytest.fixture
def sample_csv_bytes():
    """BytesIO with valid CSV content for import testing."""
    content = b"nombre,apellido,telefono\nAna,Lopez,78422032\nCarlos,Garcia,76109026\n"
    buf = io.BytesIO(content)
    buf.name = "pacientes.csv"
    return buf


@pytest.fixture
def sample_csv_missing_col():
    """BytesIO with CSV missing the telefono column."""
    content = b"nombre,apellido\nAna,Lopez\n"
    buf = io.BytesIO(content)
    buf.name = "pacientes.csv"
    return buf
