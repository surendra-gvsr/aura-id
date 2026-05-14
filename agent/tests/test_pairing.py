# agent/tests/test_pairing.py
import json
import pytest
import responses as resp_mock
import requests
from src.pairing import PairingClient, PairingError


class TestPairingClient:
    @resp_mock.activate
    def test_claim_returns_token_on_success(self):
        resp_mock.add(
            resp_mock.POST,
            "https://api.auraid.com/v1/workstations/claim",
            json={"token": "wt_abc123xyz"},
            status=200,
        )
        client = PairingClient(api_base="https://api.auraid.com/v1")
        assert client.claim("PAIR-CODE") == "wt_abc123xyz"

    @resp_mock.activate
    def test_claim_raises_on_422(self):
        resp_mock.add(
            resp_mock.POST,
            "https://api.auraid.com/v1/workstations/claim",
            json={"error": "invalid_code"},
            status=422,
        )
        client = PairingClient(api_base="https://api.auraid.com/v1")
        with pytest.raises(PairingError, match="invalid_code"):
            client.claim("BAD-CODE")

    @resp_mock.activate
    def test_claim_sends_pairing_code_in_body(self):
        resp_mock.add(
            resp_mock.POST,
            "https://api.auraid.com/v1/workstations/claim",
            json={"token": "wt_test"},
            status=200,
        )
        client = PairingClient(api_base="https://api.auraid.com/v1")
        client.claim("CODE-456")
        body = json.loads(resp_mock.calls[0].request.body)
        assert body["pairing_code"] == "CODE-456"

    @resp_mock.activate
    def test_claim_raises_on_network_error(self):
        resp_mock.add(
            resp_mock.POST,
            "https://api.auraid.com/v1/workstations/claim",
            body=requests.ConnectionError("network error"),
        )
        client = PairingClient(api_base="https://api.auraid.com/v1")
        with pytest.raises(PairingError, match="network error"):
            client.claim("CODE-789")

    @resp_mock.activate
    def test_claim_raises_on_missing_token_in_200(self):
        resp_mock.add(
            resp_mock.POST,
            "https://api.auraid.com/v1/workstations/claim",
            json={"result": "ok"},
            status=200,
        )
        client = PairingClient(api_base="https://api.auraid.com/v1")
        with pytest.raises(PairingError, match="no token"):
            client.claim("CODE-200")
