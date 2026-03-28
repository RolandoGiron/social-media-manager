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
