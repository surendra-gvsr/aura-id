# agent/tests/test_logging.py
import pytest
import structlog
from src.utils.logging import pii_scrub_processor, configure_logging


class TestPiiScrubProcessor:
    def test_allows_safe_log_line(self):
        event_dict = {
            "event": "typed scan_id=abc123 fields=8 duration_ms=2400",
            "scan_id": "abc123",
            "fields": 8,
            "duration_ms": 2400,
        }
        result = pii_scrub_processor(None, "info", event_dict)
        assert result["event"] == "typed scan_id=abc123 fields=8 duration_ms=2400"

    def test_blocks_email_pattern_in_event(self):
        event_dict = {"event": "user john.doe@hotel.com signed in"}
        with pytest.raises(structlog.DropEvent):
            pii_scrub_processor(None, "info", event_dict)

    def test_blocks_pii_key_in_dict(self):
        """Any event containing a known PII key must be dropped."""
        for key in ["first_name", "last_name", "dob", "email", "doc_number",
                    "address_line_1", "postal_code"]:
            event_dict = {"event": "test", key: "some_value"}
            with pytest.raises(structlog.DropEvent):
                pii_scrub_processor(None, "info", event_dict)

    def test_blocks_dob_pattern_in_value(self):
        event_dict = {"event": "scan done", "date": "01/15/1990"}
        with pytest.raises(structlog.DropEvent):
            pii_scrub_processor(None, "info", event_dict)

    def test_blocks_doc_number_pattern_in_event(self):
        event_dict = {"event": "processed A12345678 doc"}
        with pytest.raises(structlog.DropEvent):
            pii_scrub_processor(None, "info", event_dict)

    def test_allows_scan_id_profile_and_window(self):
        event_dict = {
            "event": "typing scan_id=abc123 profile=opera window=Opera-PMS-v5",
            "scan_id": "abc123",
            "profile": "opera",
            "window": "Opera-PMS-v5",
        }
        result = pii_scrub_processor(None, "info", event_dict)
        assert result is not None

    def test_blocks_long_suspicious_string_value(self):
        """Values over 40 chars in non-standard keys are suspect."""
        event_dict = {
            "event": "scan done",
            "detail": "A" * 45,
        }
        with pytest.raises(structlog.DropEvent):
            pii_scrub_processor(None, "info", event_dict)
