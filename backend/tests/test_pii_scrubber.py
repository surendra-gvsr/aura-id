# Tests for PII scrubbing and masking helpers.
# These are compliance-critical: PII must never appear in logs.
from app.utils.pii import mask_name, mask_doc_number, scrub_pii_from_string
from app.utils.logging import _pii_scrub_processor


def test_mask_name_returns_initial_plus_last():
    assert mask_name("John", "Smith") == "J. Smith"


def test_mask_name_no_first():
    assert mask_name(None, "Smith") == "Smith"


def test_mask_name_only_first():
    """Should return initial-only, not empty string."""
    result = mask_name("John", None)
    assert result == "J."


def test_mask_name_both_none():
    assert mask_name(None, None) == ""


def test_mask_doc_number_shows_last_four():
    assert mask_doc_number("AB123456789") == "****6789"


def test_mask_doc_number_short():
    assert mask_doc_number("AB1") == "****"


def test_mask_doc_number_none():
    assert mask_doc_number(None) is None


def test_scrub_pii_redacts_dob():
    result = scrub_pii_from_string("guest dob=1990-05-12 checked in")
    assert "1990-05-12" not in result
    assert "[DOB_REDACTED]" in result


def test_scrub_pii_redacts_explicit_doc_number():
    result = scrub_pii_from_string("doc_number=AB123456")
    assert "AB123456" not in result


def test_scrub_pii_preserves_version_strings():
    """Regression: version strings like v1234 must NOT be redacted."""
    result = scrub_pii_from_string("running version v1234 of the app")
    assert "v1234" in result


def test_pii_scrub_processor_removes_pii_keys():
    event_dict = {
        "event": "guest created",
        "first_name": "John",
        "last_name": "Smith",
        "dob": "1990-01-01",
        "doc_number": "AB123456",
        "email": "john@example.com",
        "phone": "555-1234",
        "hotel_id": "hotel-uuid",
    }
    result = _pii_scrub_processor(None, None, event_dict)
    assert "first_name" not in result
    assert "last_name" not in result
    assert "dob" not in result
    assert "doc_number" not in result
    assert "email" not in result
    assert "phone" not in result
    assert result["hotel_id"] == "hotel-uuid"  # non-PII preserved


def test_pii_scrub_processor_preserves_non_pii_event():
    event_dict = {"event": "scan.parsed scan_id=abc-123"}
    result = _pii_scrub_processor(None, None, event_dict)
    assert result["event"] == "scan.parsed scan_id=abc-123"


def test_pii_scrub_processor_handles_missing_keys_gracefully():
    """Should not raise if PII keys are absent."""
    event_dict = {"event": "system startup", "level": "info"}
    result = _pii_scrub_processor(None, None, event_dict)
    assert result["event"] == "system startup"


def test_pii_scrub_processor_handles_non_string_event():
    """Should not crash if event is not a string."""
    event_dict = {"event": 42, "level": "info"}
    result = _pii_scrub_processor(None, None, event_dict)
    assert result["event"] == 42
