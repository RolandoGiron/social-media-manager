"""HTTP client wrapper for Evolution API v2.2.3."""
import os

import requests


class EvolutionAPIError(Exception):
    """Raised when Evolution API returns an error response."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Evolution API error {status_code}: {message}")


class EvolutionAPIClient:
    """Client for Evolution API REST endpoints.

    Reads configuration from environment variables by default:
    - EVOLUTION_API_URL: Base URL of the Evolution API (default: http://evolution-api:8080)
    - EVOLUTION_API_KEY: API key for authentication
    - EVOLUTION_INSTANCE_NAME: Default instance name (default: clinic-main)
    """

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        instance_name: str | None = None,
    ):
        self.api_url = (
            api_url or os.environ.get("EVOLUTION_API_URL", "http://evolution-api:8080")
        ).rstrip("/")
        self.api_key = api_key or os.environ.get("EVOLUTION_API_KEY", "")
        self.instance_name = instance_name or os.environ.get(
            "EVOLUTION_INSTANCE_NAME", "clinic-main"
        )

    def _headers(self) -> dict:
        return {"apikey": self.api_key, "Content-Type": "application/json"}

    def _handle_error(self, resp: requests.Response) -> None:
        if resp.status_code >= 400:
            try:
                msg = resp.json().get("message", resp.text)
            except Exception:
                msg = resp.text
            raise EvolutionAPIError(resp.status_code, str(msg))

    def fetch_instances(self) -> list[dict]:
        """Fetch all registered instances."""
        resp = requests.get(
            f"{self.api_url}/instance/fetchInstances",
            headers=self._headers(),
            timeout=10,
        )
        self._handle_error(resp)
        return resp.json()

    def create_instance(self, instance_name: str | None = None) -> dict:
        """Create a new WhatsApp instance with QR code generation enabled."""
        name = instance_name or self.instance_name
        resp = requests.post(
            f"{self.api_url}/instance/create",
            headers=self._headers(),
            json={
                "instanceName": name,
                "integration": "WHATSAPP-BAILEYS",
                "qrcode": True,
            },
            timeout=10,
        )
        self._handle_error(resp)
        return resp.json()

    def get_qr_code(self, instance_name: str | None = None) -> str:
        """Get the QR code base64 string for connecting an instance."""
        name = instance_name or self.instance_name
        resp = requests.get(
            f"{self.api_url}/instance/connect/{name}",
            headers=self._headers(),
            timeout=10,
        )
        self._handle_error(resp)
        data = resp.json()
        return data.get("base64", "")

    def get_connection_state(self, instance_name: str | None = None) -> str:
        """Get the connection state of an instance ('open', 'close', 'connecting')."""
        name = instance_name or self.instance_name
        resp = requests.get(
            f"{self.api_url}/instance/connectionState/{name}",
            headers=self._headers(),
            timeout=5,
        )
        self._handle_error(resp)
        data = resp.json()
        return data.get("instance", {}).get("state", "close")

    def send_text_message(
        self, number: str, text: str, instance_name: str | None = None
    ) -> dict:
        """Send a text message to a WhatsApp number."""
        name = instance_name or self.instance_name
        resp = requests.post(
            f"{self.api_url}/message/sendText/{name}",
            headers=self._headers(),
            json={"number": number, "text": text},
            timeout=10,
        )
        self._handle_error(resp)
        return resp.json()
