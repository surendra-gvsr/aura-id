# agent/tests/test_poller.py
import json
import pytest
import requests
import responses as resp_mock
from src.poller import Poller
from src.models import ScanData


class TestPoller:
    @resp_mock.activate
    def test_fetch_returns_scan_when_pending(self):
        resp_mock.add(
            resp_mock.GET,
            "https://api.auraid.com/v1/scans/pending-type",
            json={
                "scan_id": "scan_001",
                "pms_profile_name": "opera",
                "fields": {
                    "last_name": "Smith", "first_name": "John",
                    "dob": "1990-01-15", "doc_number": "A12345678",
                    "address_line_1": "123 Main St", "city": "Springfield",
                    "postal_code": "12345", "email": "j@h.com",
                },
            },
            status=200,
        )
        poller = Poller(api_base="https://api.auraid.com/v1", token="tok")
        scan = poller.fetch_pending()
        assert scan is not None
        assert scan.scan_id == "scan_001"
        assert scan.last_name == "Smith"

    @resp_mock.activate
    def test_fetch_returns_none_on_204(self):
        resp_mock.add(
            resp_mock.GET,
            "https://api.auraid.com/v1/scans/pending-type",
            status=204,
        )
        poller = Poller(api_base="https://api.auraid.com/v1", token="tok")
        assert poller.fetch_pending() is None

    @resp_mock.activate
    def test_fetch_sends_bearer_token(self):
        resp_mock.add(
            resp_mock.GET,
            "https://api.auraid.com/v1/scans/pending-type",
            status=204,
        )
        poller = Poller(api_base="https://api.auraid.com/v1", token="my_token")
        poller.fetch_pending()
        assert resp_mock.calls[0].request.headers["Authorization"] == "Bearer my_token"

    @resp_mock.activate
    def test_mark_typed_posts_status_and_duration(self):
        resp_mock.add(
            resp_mock.POST,
            "https://api.auraid.com/v1/scans/scan_001/mark-typed",
            json={"ok": True},
            status=200,
        )
        poller = Poller(api_base="https://api.auraid.com/v1", token="tok")
        poller.mark_typed("scan_001", status="success", duration_ms=2400)
        body = json.loads(resp_mock.calls[0].request.body)
        assert body == {"status": "success", "duration_ms": 2400}

    @resp_mock.activate
    def test_fetch_returns_none_on_network_error(self):
        resp_mock.add(
            resp_mock.GET,
            "https://api.auraid.com/v1/scans/pending-type",
            body=requests.ConnectionError(),
        )
        poller = Poller(api_base="https://api.auraid.com/v1", token="tok")
        assert poller.fetch_pending() is None
