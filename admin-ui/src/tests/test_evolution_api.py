"""Tests for Evolution API client module."""
import pytest
import requests_mock as rm

from components.evolution_api import EvolutionAPIClient, EvolutionAPIError


class TestCreateInstance:
    def test_create_instance(self, api_client):
        """POST /instance/create returns 200 with instance data and base64 QR."""
        with rm.Mocker() as m:
            m.post(
                "http://mock-evolution:8080/instance/create",
                json={
                    "instance": {"instanceName": "test-instance", "status": "created"},
                    "hash": {"apikey": "generated-key"},
                    "qrcode": {"base64": "data:image/png;base64,AAAA"},
                },
                status_code=200,
            )
            result = api_client.create_instance()
            assert result["instance"]["instanceName"] == "test-instance"
            assert "qrcode" in result

    def test_create_instance_already_exists(self, api_client):
        """POST /instance/create returns 409; function raises EvolutionAPIError."""
        with rm.Mocker() as m:
            m.post(
                "http://mock-evolution:8080/instance/create",
                json={"message": "Instance already exists"},
                status_code=409,
            )
            with pytest.raises(EvolutionAPIError) as exc_info:
                api_client.create_instance()
            assert exc_info.value.status_code == 409


class TestGetQrCode:
    def test_get_qr_code(self, api_client):
        """GET /instance/connect/{instance} returns 200 with base64 string."""
        with rm.Mocker() as m:
            m.get(
                "http://mock-evolution:8080/instance/connect/test-instance",
                json={"base64": "data:image/png;base64,QRDATA"},
                status_code=200,
            )
            result = api_client.get_qr_code()
            assert result == "data:image/png;base64,QRDATA"

    def test_get_qr_code_not_found(self, api_client):
        """GET /instance/connect/{instance} returns 404; raises EvolutionAPIError."""
        with rm.Mocker() as m:
            m.get(
                "http://mock-evolution:8080/instance/connect/test-instance",
                json={"message": "Instance not found"},
                status_code=404,
            )
            with pytest.raises(EvolutionAPIError) as exc_info:
                api_client.get_qr_code()
            assert exc_info.value.status_code == 404


class TestGetConnectionState:
    def test_get_connection_state(self, api_client):
        """GET /instance/connectionState/{instance} returns open state."""
        with rm.Mocker() as m:
            m.get(
                "http://mock-evolution:8080/instance/connectionState/test-instance",
                json={"instance": {"instanceName": "test-instance", "state": "open"}},
                status_code=200,
            )
            result = api_client.get_connection_state()
            assert result == "open"

    def test_get_connection_state_closed(self, api_client):
        """GET /instance/connectionState/{instance} returns close state."""
        with rm.Mocker() as m:
            m.get(
                "http://mock-evolution:8080/instance/connectionState/test-instance",
                json={"instance": {"instanceName": "test-instance", "state": "close"}},
                status_code=200,
            )
            result = api_client.get_connection_state()
            assert result == "close"


class TestSendTextMessage:
    def test_send_text_message(self, api_client):
        """POST /message/sendText/{instance} returns 200; function returns response dict."""
        with rm.Mocker() as m:
            m.post(
                "http://mock-evolution:8080/message/sendText/test-instance",
                json={"key": {"id": "msg123"}, "status": "PENDING"},
                status_code=200,
            )
            result = api_client.send_text_message("+521234567890", "Hola!")
            assert result["key"]["id"] == "msg123"

    def test_send_text_message_failure(self, api_client):
        """POST /message/sendText/{instance} returns 500; raises EvolutionAPIError."""
        with rm.Mocker() as m:
            m.post(
                "http://mock-evolution:8080/message/sendText/test-instance",
                json={"message": "Internal server error"},
                status_code=500,
            )
            with pytest.raises(EvolutionAPIError) as exc_info:
                api_client.send_text_message("+521234567890", "Hola!")
            assert exc_info.value.status_code == 500


class TestFetchInstances:
    def test_fetch_instances(self, api_client):
        """GET /instance/fetchInstances returns list of instance dicts."""
        with rm.Mocker() as m:
            m.get(
                "http://mock-evolution:8080/instance/fetchInstances",
                json=[
                    {"instance": {"instanceName": "inst1", "status": "open"}},
                    {"instance": {"instanceName": "inst2", "status": "close"}},
                ],
                status_code=200,
            )
            result = api_client.fetch_instances()
            assert len(result) == 2
            assert result[0]["instance"]["instanceName"] == "inst1"
