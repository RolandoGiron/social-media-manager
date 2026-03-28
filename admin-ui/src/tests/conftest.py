import pytest
from components.evolution_api import EvolutionAPIClient


@pytest.fixture
def api_client():
    return EvolutionAPIClient(
        api_url="http://mock-evolution:8080",
        api_key="test-api-key",
        instance_name="test-instance",
    )
