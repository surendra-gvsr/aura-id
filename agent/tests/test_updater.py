# agent/tests/test_updater.py
import pytest
import requests
import responses as resp_mock
from src.updater import UpdateChecker


class TestUpdateChecker:
    @resp_mock.activate
    def test_no_update_when_versions_equal(self):
        resp_mock.add(
            resp_mock.GET, "https://updates.auraid.com/latest.json",
            json={"version": "0.1.0", "url": "https://dl.auraid.com/setup.exe", "notes": ""},
            status=200,
        )
        info = UpdateChecker("https://updates.auraid.com/latest.json", "0.1.0").check()
        assert info.update_available is False

    @resp_mock.activate
    def test_update_available_when_remote_is_newer(self):
        resp_mock.add(
            resp_mock.GET, "https://updates.auraid.com/latest.json",
            json={"version": "0.2.0", "url": "https://dl.auraid.com/setup-0.2.0.exe", "notes": "Fixes"},
            status=200,
        )
        info = UpdateChecker("https://updates.auraid.com/latest.json", "0.1.0").check()
        assert info.update_available is True
        assert info.latest_version == "0.2.0"
        assert "0.2.0" in info.download_url

    @resp_mock.activate
    def test_no_update_on_network_error(self):
        resp_mock.add(
            resp_mock.GET, "https://updates.auraid.com/latest.json",
            body=requests.ConnectionError(),
        )
        info = UpdateChecker("https://updates.auraid.com/latest.json", "0.1.0").check()
        assert info.update_available is False

    @resp_mock.activate
    def test_no_update_when_current_is_newer(self):
        resp_mock.add(
            resp_mock.GET, "https://updates.auraid.com/latest.json",
            json={"version": "0.1.0", "url": "", "notes": ""},
            status=200,
        )
        info = UpdateChecker("https://updates.auraid.com/latest.json", "0.2.0").check()
        assert info.update_available is False
