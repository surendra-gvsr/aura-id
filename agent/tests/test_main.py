# agent/tests/test_main.py
import pytest
import requests
import responses as resp_mock
from src.main import SubscriptionChecker


class TestSubscriptionChecker:
    @resp_mock.activate
    def test_active_subscription_returns_true(self):
        resp_mock.add(
            resp_mock.GET,
            "https://api.auraid.com/v1/hotels/me",
            json={"subscription_status": "active"},
            status=200,
        )
        assert SubscriptionChecker("https://api.auraid.com/v1", "tok").is_active() is True

    @resp_mock.activate
    def test_past_due_returns_false(self):
        resp_mock.add(
            resp_mock.GET,
            "https://api.auraid.com/v1/hotels/me",
            json={"subscription_status": "past_due"},
            status=200,
        )
        assert SubscriptionChecker("https://api.auraid.com/v1", "tok").is_active() is False

    @resp_mock.activate
    def test_network_error_returns_false(self):
        resp_mock.add(
            resp_mock.GET,
            "https://api.auraid.com/v1/hotels/me",
            body=requests.ConnectionError(),
        )
        assert SubscriptionChecker("https://api.auraid.com/v1", "tok").is_active() is False

    @resp_mock.activate
    def test_401_returns_false(self):
        resp_mock.add(
            resp_mock.GET,
            "https://api.auraid.com/v1/hotels/me",
            json={"error": "unauthorized"},
            status=401,
        )
        assert SubscriptionChecker("https://api.auraid.com/v1", "tok").is_active() is False
