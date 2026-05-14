# agent/tests/test_sentry_setup.py
import pytest
from src.sentry_setup import scrub_sentry_event


class TestSentryScrubbing:
    def _event(self, **extra) -> dict:
        return {
            "extra": extra,
            "tags": {},
            "exception": {"values": [{"stacktrace": {"frames": [
                {"vars": {"last_name": "Smith", "safe_var": "ok"}}
            ]}}]},
        }

    def test_removes_pii_keys_from_extra(self):
        event = self._event(first_name="John", last_name="Smith", scan_id="abc123")
        result = scrub_sentry_event(event, {})
        assert "first_name" not in result["extra"]
        assert "last_name" not in result["extra"]
        assert result["extra"]["scan_id"] == "abc123"

    def test_removes_email_value_from_extra(self):
        event = self._event(msg="user john@hotel.com failed")
        result = scrub_sentry_event(event, {})
        for v in result["extra"].values():
            assert "john@hotel.com" not in str(v)

    def test_removes_pii_keys_from_frame_locals(self):
        event = self._event()
        result = scrub_sentry_event(event, {})
        frame = result["exception"]["values"][0]["stacktrace"]["frames"][0]
        assert "last_name" not in frame["vars"]
        assert frame["vars"]["safe_var"] == "ok"

    def test_preserves_non_pii_extra(self):
        event = self._event(scan_id="abc123", duration_ms=2400)
        result = scrub_sentry_event(event, {})
        assert result["extra"]["scan_id"] == "abc123"
        assert result["extra"]["duration_ms"] == 2400

    def test_removes_pii_from_tags(self):
        event = self._event()
        event["tags"] = {"email": "x@y.com", "workstation_id": "ws_001"}
        result = scrub_sentry_event(event, {})
        assert "email" not in result["tags"]
        assert result["tags"]["workstation_id"] == "ws_001"
